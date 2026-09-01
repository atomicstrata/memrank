# Copyright 2026 AtomicStrata
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or
# implied. See the License for the specific language governing
# permissions and limitations under the License.
"""`run_cell` and the measurement loop it drives: prepare, ingest, retrieve, judge.
"""
from __future__ import annotations

import random
import time
from collections.abc import Callable
from concurrent.futures import ThreadPoolExecutor
from dataclasses import replace
from pathlib import Path
from typing import Any

from memrank import rate_limit
from memrank.core import AdapterResponse, Benchmark, Document, MemoryAdapter
from memrank.errors import MemrankError
from memrank.evaluation.aggregate import _drill_unit, build_result
from memrank.evaluation.judge_stage import _apply_judge, assert_judge_coverage
from memrank.evaluation.observer import NULL_OBSERVER, EvalObserver, _eval_plan
from memrank.evaluation.receipt import _build_receipt
from memrank.evaluation.result import EvalResult
from memrank.instrumentation import LatencyCollector, TokenCollector
from memrank.judging.client import build_completer
from memrank.judging.judge import JudgeConfig
from memrank.provenance.receipt import finalize_receipt
from memrank.rate_limit import RateLimitGate, retry_after_seconds
from memrank.runs import checkpoint


def cell_applicable(adapter: MemoryAdapter, benchmark: Benchmark) -> bool:
    """True unless the benchmark needs a graph snapshot the adapter can't provide.

    The single capability-gate predicate: both execution paths (``run_cell`` and
    ``compare``) consult it BEFORE any prepare/ingest/retrieve (or preflight), so an
    inapplicable cell skips cleanly instead of crashing in the scorer or touching a
    live backend.
    """
    return not (getattr(benchmark, "requires_graph", False) and not getattr(adapter, "graph_capable", False))


def _not_applicable_result(adapter: MemoryAdapter, benchmark: Benchmark) -> EvalResult:
    """The ``not_applicable`` result for an inapplicable (graph benchmark x non-graph
    adapter) cell. Callers MUST gate on ``cell_applicable`` first."""
    return EvalResult.not_applicable(
        adapter.name, benchmark.name,
        reason=f"{benchmark.name} requires a graph-capable adapter; {adapter.name} is not")


def _not_applicable_cell(adapter: MemoryAdapter, benchmark: Benchmark) -> dict[str, Any]:
    """The dict form of :func:`_not_applicable_result` -- what the artifact records."""
    return _not_applicable_result(adapter, benchmark).to_dict()


def run_cell(
    adapter: MemoryAdapter,
    benchmark: Benchmark,
    *,
    k: int,
    repeats: int,
    run_id_prefix: str,
    model: str,
    token_budget: int,
    seed: int = 42,
    judge: JudgeConfig | None = None,
    judge_runtime: tuple[Any, Any] | None = None,
    units: list[Any] | None = None,
    workers: int = 1,
    judge_workers: int = 1,
    #: Where to write the pre-judgment checkpoint. ``None`` writes none: ``run_cell`` is a library
    #: primitive that tests drive without a run directory, and a checkpoint nothing can resume from
    #: is just a file.
    checkpoint_path: Path | None = None,
    make_adapter: Callable[[], MemoryAdapter] | None = None,
    #: How the loop narrates. The default is silence -- a library call reports to nobody.
    #: The CLI passes `orchestration.observers.RunStatusObserver`; anything wanting bare
    #: terminal narration passes `orchestration.observers.ConsoleObserver`.
    observer: EvalObserver = NULL_OBSERVER,
    #: The rate-limit gate every worker shares. ``None`` builds a fresh per-cell gate,
    #: which is what every caller got before the parameter existed.
    gate: RateLimitGate | None = None,
) -> EvalResult:
    """Run one (adapter, benchmark) cell; return its :class:`EvalResult`.

    ``result.to_dict()`` is the aggregated artifact dict this function used to return.

    ``judge_runtime`` is an optional pre-built ``(completer, counter)`` shared
    across cells so the call cap + counter span a whole comparison rather than
    resetting per engine. When omitted, a standalone runtime is built.
    ``units`` may be pre-loaded by the caller (compare loads once and shares them)
    to avoid re-parsing the dataset per engine.

    ``workers`` > 1 ingests+retrieves UNITS concurrently -- safe because each unit
    has a distinct isolation_id/user_id, so their memory banks never interact.
    Each unit then runs on its own adapter instance (built by ``make_adapter``, which
    is required when workers>1) to avoid shared mutable adapter state. Docs WITHIN a
    unit stay sequential (mem0's per-user reconcile is order-dependent), and judging
    stays sequential after. Recall is unaffected; latency becomes contended (flagged).
    """
    if not cell_applicable(adapter, benchmark):
        return _not_applicable_result(adapter, benchmark)
    if workers > 1 and make_adapter is None:
        raise ValueError("run_cell(workers>1) requires make_adapter (an adapter factory)")
    random.seed(seed)
    receipt = _build_receipt(adapter, benchmark,
                             k=k, repeats=repeats, model=model,
                             token_budget=token_budget, seed=seed, judge=judge, workers=workers)
    if units is None:
        units = benchmark.load()
    # One shape for the whole cell: the gate, the progress denominator and the judging loop must
    # ask the same object, or they disagree about what the run is going to grade.
    shape = benchmark.judge_shape()
    # Coverage gate BEFORE any prepare/ingest/retrieve (backstop for the `run`
    # path; compare gates earlier, before preflight + client setup).
    assert_judge_coverage(units, judge, benchmark.name, shape)
    label = f"[{adapter.name} × {benchmark.name}]"
    # The work is fully known before the first document: totals now, so the first progress record
    # already has a denominator. Without it the bar would have to guess its own size. Installed
    # before any worker pool starts -- observers rely on that ordering.
    observer.planned(_eval_plan(units, repeats, judge, shape,
                                adapter=adapter.name, benchmark=benchmark.name))
    # One gate per run, shared by every worker: the provider's limit is per-ACCOUNT, so a pause
    # that only quiets the thread which hit it leaves aggregate demand unchanged.
    if gate is None:
        gate = RateLimitGate()
    if workers > 1:
        assert make_adapter is not None  # guarded above; narrows for type-checkers
        (per_unit_scores, per_query, latency_metrics, token_metrics, retrieve_summary,
         ingest_summary) = \
            _run_units_concurrent(make_adapter, benchmark, units, k=k, repeats=repeats,
                                  run_id_prefix=run_id_prefix, token_budget=token_budget,
                                  workers=workers, label=label, gate=gate,
                                  observer=observer)
    else:
        (per_unit_scores, per_query, latency_metrics, token_metrics, retrieve_summary,
         ingest_summary) = \
            _run_units_sequential(adapter, benchmark, units, k=k, repeats=repeats,
                                  run_id_prefix=run_id_prefix, token_budget=token_budget,
                                  gate=gate, observer=observer)
    budget_mode = _effective_budget_mode(adapter, benchmark)

    def aggregate(judged):
        return build_result(adapter, benchmark, units, per_unit_scores, per_query,
                            model=model, token_budget=token_budget, receipt=receipt,
                            k=k, repeats=repeats, judged_metrics=judged,
                            retrieve_summary=retrieve_summary, latency_metrics=latency_metrics,
                            token_metrics=token_metrics, workers=workers,
                            judge_workers=judge_workers, ingest_summary=ingest_summary)

    # Everything expensive is now done and nothing is on disk. Judging is the last stage, the one
    # with the least test exposure, and the one a 4h50m run died in on 2026-08-12 having completed
    # every ingest and retrieve. Written BEFORE the first judge call so that failing there costs
    # the judging, not the run (`memrank ops rejudge` finishes it).
    if checkpoint_path is not None and judge is not None:
        checkpoint.write(checkpoint_path, cell=aggregate(None).to_dict(),
                         budget_mode=budget_mode)

    judged_metrics = None
    if judge is not None:
        # Resolved here too, not only at the pre-run gate. The gate exists to refuse EARLY, before
        # a run is minted or a task launched; it is not the only way in. A library caller -- the
        # comparison path, a test, anything driving `run_cell` directly -- hands over a config whose
        # cap was never derived, and this is the one place that knows both the units and the shape
        # the derivation needs. Idempotent: an explicit cap is only re-checked, never widened.
        complete, counter = judge_runtime or build_completer(judge)
        before = counter()
        judged_metrics = _apply_judge(units, per_query, judge, complete, budget_mode,
                                      shape=shape, judge_workers=judge_workers,
                                      observer=observer)
        receipt.extra["judge_calls_made"] = counter() - before
    # What the run had to wait through. A run that survived by pausing six minutes is not
    # comparable on latency to one that never paused, and without this nothing would say so.
    receipt.extra["rate_limit"] = gate.snapshot()
    finalize_receipt(receipt)
    return aggregate(judged_metrics)


def _effective_budget_mode(adapter, benchmark) -> str:
    """The reader-context mode a cell actually runs under: target arm x benchmark protocol.

    The adapter's ``context_budget`` names the ARM (matched engine / uncapped full-context /
    no-memory "none"); the benchmark's ``context_policy`` names the PROTOCOL. A benchmark whose
    protocol is uncapped (BEAM -- every published harness hands the reader everything retrieval
    returned) promotes matched arms to uncapped, because a capped run of it is not that benchmark.
    "none" is never promoted: the no-memory arm retrieves nothing by design, protocol or not.
    """
    arm = getattr(adapter, "context_budget", "matched")
    if arm == "matched" and getattr(benchmark, "context_policy", "matched") == "uncapped":
        return "uncapped"
    return arm


def _run_units_sequential(adapter, benchmark, units, *, k, repeats, run_id_prefix,
                          token_budget, gate, observer):
    """Original sequential path: one shared adapter over every unit, in order.

    Returns ``(per_unit_scores, per_query, latency_metrics, token_metrics, retrieve_summary)``.
    Latency/token metrics come straight from the single reused adapter (unchanged behavior)."""
    measured = LatencyCollector()
    per_unit_scores: list[dict[str, Any]] = []
    per_query: list[dict[str, Any]] = []
    label = f"[{adapter.name} × {benchmark.name}]"
    total_queries = sum(len(u.queries) for u in units)
    done_queries = 0
    for unit_idx, unit in enumerate(units, start=1):
        observer.unit_started(index=unit_idx, total=len(units),
                              documents=len(unit.documents))
        responses = _run_unit_repeats(adapter, unit, k=k, repeats=repeats,
                                      run_id_prefix=run_id_prefix, measured=measured,
                                      label=label, gate=gate, observer=observer)
        scored = benchmark.score(unit, responses)
        scored["unit_id"] = unit.unit_id
        per_unit_scores.append(scored)
        per_query.extend(_drill_unit(unit, responses, token_budget,
                                     _effective_budget_mode(adapter, benchmark)))
        done_queries += len(unit.queries)
        observer.unit_finished(label=label, index=unit_idx, total=len(units),
                               queries_done=done_queries, queries_total=total_queries)
    return (per_unit_scores, per_query, adapter.latency_metrics(),
            adapter.token_metrics(), measured.summary("retrieve"),
            measured.summary("ingest"))


def _run_one_unit(make_adapter, benchmark, unit, *, k, repeats, run_id_prefix,
                  token_budget, label, gate, observer):
    """Run ONE unit on its own fresh adapter (concurrent path). Returns the unit's
    scored dict, drill rows, and its adapter's latency/token/retrieve collectors."""
    adapter = make_adapter()
    measured = LatencyCollector()
    try:
        responses = _run_unit_repeats(adapter, unit, k=k, repeats=repeats,
                                      run_id_prefix=run_id_prefix, measured=measured,
                                      label=f"{label} u={unit.unit_id}", gate=gate,
                                      observer=observer)
        scored = benchmark.score(unit, responses)
        scored["unit_id"] = unit.unit_id
        drill = _drill_unit(unit, responses, token_budget,
                            _effective_budget_mode(adapter, benchmark))
        return scored, drill, adapter.latency, adapter.tokens, measured
    finally:
        _close_adapter(adapter)


def _run_units_concurrent(make_adapter, benchmark, units, *, k, repeats, run_id_prefix,
                          token_budget, workers, label, gate, observer):
    """Ingest+retrieve units concurrently (one adapter each), then merge in unit order.

    ``ThreadPoolExecutor.map`` preserves input order, so per_unit_scores/per_query and the
    composite stay deterministic regardless of which unit finishes first."""
    def work(unit):
        return _run_one_unit(make_adapter, benchmark, unit, k=k, repeats=repeats,
                             run_id_prefix=run_id_prefix, token_budget=token_budget,
                             label=label, gate=gate, observer=observer)

    with ThreadPoolExecutor(max_workers=min(workers, len(units))) as ex:
        results = list(ex.map(work, units))

    per_unit_scores: list[dict[str, Any]] = []
    per_query: list[dict[str, Any]] = []
    # ``lat``/``tok`` merge the ADAPTERS' collectors (the published metrics shape); ``runner_lat``
    # merges what the runner timed at its own call boundary, which is where both summaries come
    # from -- see _ingest_with_progress on why the adapter's internals are not that boundary.
    lat, tok, runner_lat = LatencyCollector(), TokenCollector(), LatencyCollector()
    for scored, drill, adapter_lat, adapter_tok, measured in results:
        per_unit_scores.append(scored)
        per_query.extend(drill)
        lat.merge(adapter_lat)
        tok.merge(adapter_tok)
        runner_lat.merge(measured)
    return (per_unit_scores, per_query, lat.as_metrics(), tok.as_metrics(),
            runner_lat.summary("retrieve"), runner_lat.summary("ingest"))

def _ingest_with_progress(adapter: MemoryAdapter, documents: list[Document], *,
                          measured: LatencyCollector, label: str, gate: RateLimitGate,
                          observer: EvalObserver) -> None:
    """Ingest one document at a time, reporting each to the observer.

    Per-doc ingest is metric-neutral: every adapter already loops per document with its own
    latency/token instrumentation, so N single-doc calls match one bulk call -- this only adds
    visibility into an otherwise-silent long ingest.

    Timed HERE, at the runner's own call boundary, exactly as retrieve is. The adapter's internal
    collector holds the same samples, but it is an implementation detail -- ``MemoryAdapter``
    publishes ``latency_metrics()`` and nothing else, so an adapter that satisfies the interface
    without using ``LatencyCollector`` is a legal adapter and must still be measurable.

    The timing comes back FROM ``_ingest_one`` rather than wrapping it, because a rate-limit pause
    is time the runner chose to wait, not time the engine took to answer. Wrapping the call put
    that pause inside the sample: a 30-second gate wait would have landed in ``ingest p95`` and
    made a throttled run look like a slow engine.
    """
    n = len(documents)
    scope = getattr(adapter, "_isolation", None) or ""
    for i, doc in enumerate(documents, start=1):
        elapsed = _ingest_one(adapter, doc, scope=scope, label=label, position=f"{i}/{n}",
                              gate=gate, observer=observer)
        measured.record("ingest", elapsed * 1000.0)
        observer.item_done("ingest", seconds=elapsed, done=i, total=n, label=label)


#: Bounded by WALL CLOCK, not by a count. The count was the defect: five attempts at 1s base is
#: about 20 seconds of waiting, and TPM is a rolling SIXTY-second window, so the budget expired
#: before the window it was waiting on could possibly drain. A run at `--workers 5` died at
#: document 554/1232 with every 429 reading `Used 199659 / Limit 200000`.
#:
#: Generous, because with `RateLimitGate` in front of it sustained saturation self-resolves --
#: throughput settles wherever the account allows -- so this is a backstop for a condition no amount
#: of waiting fixes (revoked key, zero quota), not a budget for ordinary contention. Bounded all
#: the same: CLAUDE.md's "no degraded modes" means a run that cannot proceed stops and says so,
#: rather than spinning while appearing healthy.
_INGEST_RETRY_DEADLINE_S = 600.0
_INGEST_BACKOFF_BASE_S = 1.0


class RateLimitExhausted(MemrankError):
    """The provider stayed over quota for longer than a run can wait.

    A ``MemrankError`` because it is a condition of the environment, not a defect in memrank: the
    run that prompted this printed "internal error ... this is a bug in memrank", which sends the
    reader hunting the wrong thing entirely.
    """


#: Moved to `rate_limit` when the judge became a third caller: ingest, retrieve and judging all
#: spend the same account, so they must agree on what a rate limit IS. Re-exported under the
#: original name because this module's two call sites read fine as they are.
_is_rate_limited = rate_limit.is_rate_limited


def _pause_for_rate_limit(gate: RateLimitGate, exc: BaseException, *, attempt: int, label: str,
                          what: str, observer: EvalObserver = NULL_OBSERVER) -> None:
    """Close the shared gate for as long as the provider asked, and say so.

    The provider states the wait in a response header, so backoff is only the fallback for a
    provider that omits it -- guessing an interval when we were handed one is how the previous
    version waited 1.5s for a limit that wanted 241ms, and 1.5s for one that wanted a minute.
    """
    stated = retry_after_seconds(exc)
    delay = stated if stated is not None else min(
        _INGEST_BACKOFF_BASE_S * (2 ** (attempt - 1)), rate_limit.MAX_PAUSE_S)
    source = "the provider asked for" if stated is not None else "backing off"
    added = gate.pause(delay)
    observer.warning(f"{label} rate limited on {what} (attempt {attempt}); {source} {delay:.1f}s -- "
                     f"every worker pauses, since the limit is account-wide "
                     f"({added:.1f}s added to the shared pause).")


def _ingest_one(adapter: MemoryAdapter, doc: Document, *, scope: str, label: str,
                position: str, gate: RateLimitGate,
                observer: EvalObserver = NULL_OBSERVER) -> float:
    """Ingest one document, retrying a rate limit ONLY when the engine can prove nothing was written.

    Returns the seconds the SUCCESSFUL call took -- not the wall time spent here. Waiting out a
    rate limit is the runner's choice, not the engine's latency, and folding it into the sample
    would report a throttled account as a slow engine.

    The tempting version wraps this in backoff and moves on. It would be wrong, because a failed
    ingest is not necessarily a no-op: mem0's `add()` extracts, reconciles, then writes in a loop,
    so a failure in the third phase leaves the scope half-written and a retry re-extracts against a
    partially populated store. Whether that duplicates depends on a reconcile LLM noticing, which
    is not a foundation for a benchmark number.

    So the question is asked rather than assumed. `state_fingerprint` digests the scope before the
    attempt and again after the failure:

      - UNCHANGED -- the call wrote nothing, so retrying is exactly equivalent to never having
        failed. Retry.
      - CHANGED -- a partial write. Refuse, and say so: the store is no longer in a state anything
        can reason about.
      - UNAVAILABLE (`None`) -- the engine cannot be asked, so equivalence cannot be shown. Refuse.
        A benchmark that retries on hope is worse than one that stops.

    The pause is taken on ``gate`` rather than by sleeping here, because a rate limit is
    account-wide and this thread's silence does nothing about the other workers still saturating
    it. See ``memrank.rate_limit`` -- that distinction is why the first version of this retry
    recovered 35 limits and still lost the run.
    """
    deadline = time.monotonic() + _INGEST_RETRY_DEADLINE_S
    attempt = 0
    while True:
        attempt += 1
        gate.wait()
        before = adapter.state_fingerprint(scope) if scope else None
        try:
            started = time.perf_counter()
            adapter.ingest([doc])
            return time.perf_counter() - started
        except Exception as exc:  # noqa: BLE001 - re-raised unless provably safe to retry
            if not _is_rate_limited(exc):
                raise
            if before is None:
                raise RuntimeError(
                    f"{label} rate limited on document {position} and {adapter.name} cannot report "
                    f"whether the failed write landed, so retrying could double-ingest it. "
                    f"Reduce --workers so the run fits the provider's limit."
                ) from exc
            after = adapter.state_fingerprint(scope)
            if after != before:
                raise RuntimeError(
                    f"{label} rate limited PART-WAY THROUGH writing document {position}: the "
                    f"engine's state changed before the failure, so a retry would ingest it twice "
                    f"and the unit's memories can no longer be trusted. Reduce --workers."
                ) from exc
            if time.monotonic() >= deadline:
                raise RateLimitExhausted(
                    f"{label} could not ingest document {position}: the provider stayed over quota "
                    f"for {_INGEST_RETRY_DEADLINE_S / 60:.0f} minutes across {attempt} attempts. "
                    f"Waiting longer will not help -- check the key's quota, or lower --workers."
                ) from exc
            _pause_for_rate_limit(gate, exc, attempt=attempt, label=label,
                                  what=f"document {position}", observer=observer)


def _retrieve_one(adapter: MemoryAdapter, query, *, k: int, run_id: str, label: str,
                  gate: RateLimitGate, observer: EvalObserver = NULL_OBSERVER):
    """Retrieve once, waiting out a rate limit on the shared gate.

    No ``state_fingerprint`` check here, and that is not an oversight: retrieval is read-only, so
    a repeat is idempotent by construction and there is no partial write to detect. Ingest needs
    the proof because ``add()`` writes; this does not.

    It is gated all the same, because embeddings draw on the SAME account quota. A retrieve loop
    that ignored the gate would keep the window saturated while ingest sat waiting on it -- the
    workers would be throttled and the account would not.

    Returns ``(documents, raw, elapsed_ms)``. The timing is taken around the provider call alone
    so that a gate pause never enters ``retrieve p50/p95/p99`` -- latency percentiles are what
    engines are compared on, and time spent waiting on a quota says nothing about the engine.
    """
    deadline = time.monotonic() + _INGEST_RETRY_DEADLINE_S
    attempt = 0
    while True:
        attempt += 1
        gate.wait()
        try:
            started = time.perf_counter()
            docs, raw = adapter.retrieve(query["text"], k, run_id, query.get("query_timestamp"))
            return docs, raw, (time.perf_counter() - started) * 1000.0
        except Exception as exc:  # noqa: BLE001 - re-raised unless it is a rate limit
            if not _is_rate_limited(exc):
                raise
            if time.monotonic() >= deadline:
                raise RateLimitExhausted(
                    f"{label} could not retrieve query {query['id']}: the provider stayed over "
                    f"quota for {_INGEST_RETRY_DEADLINE_S / 60:.0f} minutes across {attempt} "
                    f"attempts. Check the key's quota, or lower --workers."
                ) from exc
            _pause_for_rate_limit(gate, exc, attempt=attempt, label=label,
                                  what=f"query {query['id']}", observer=observer)


def _retrieve_with_progress(adapter: MemoryAdapter, unit, *, k: int, repeats: int,
                            run_id: str, measured: LatencyCollector, label: str,
                            gate: RateLimitGate,
                            observer: EvalObserver) -> list[AdapterResponse]:
    """Retrieve every query ``repeats`` times (scoring the first pass), reporting each to
    the observer. Only measured retrieves land in ``measured``."""
    responses: list[AdapterResponse] = []
    n = len(unit.queries)
    for pass_idx in range(repeats):
        for i, query in enumerate(unit.queries, start=1):
            docs, raw, elapsed_ms = _retrieve_one(adapter, query, k=k, run_id=run_id,
                                                  label=label, gate=gate,
                                                  observer=observer)
            measured.record("retrieve", elapsed_ms)
            if pass_idx == 0:  # score the first measured pass
                responses.append(AdapterResponse(
                    query_id=query["id"], documents=docs,
                    raw=raw if isinstance(raw, dict) else None,
                    latency_ms=elapsed_ms,
                    metadata={"category": query.get("category")}))
            observer.item_done("retrieve", seconds=elapsed_ms / 1000.0, done=i, total=n,
                               label=label, pass_index=pass_idx, passes=repeats)
    return responses


def _run_unit_repeats(adapter, unit, *, k, repeats, run_id_prefix, measured, label,
                      gate, observer):
    """Prepare+ingest once, warm up once, then retrieve ``repeats`` times.

    Documents are re-scoped to ``run_id`` before ingest so engines that key on
    ``doc.user_id`` (AM, Mem0) ingest under the same id retrieval queries with.
    Only measured retrieves are recorded into ``measured`` -- the warm-up is not.
    """
    run_id = f"{run_id_prefix}-{unit.isolation_id}"
    adapter.prepare(run_id)
    try:
        _ingest_with_progress(
            adapter, [replace(doc, user_id=run_id) for doc in unit.documents], label=label,
            measured=measured, gate=gate, observer=observer)
        if unit.queries:  # warm-up -- intentionally NOT recorded in `measured`
            _retrieve_one(adapter, unit.queries[0], k=k, run_id=run_id, label=label,
                          gate=gate, observer=observer)
        return _retrieve_with_progress(adapter, unit, k=k, repeats=repeats,
                                       run_id=run_id, measured=measured, label=label,
                                       gate=gate, observer=observer)
    finally:
        adapter.cleanup()

def _close_adapter(adapter: MemoryAdapter) -> None:
    """Close any resources the adapter holds (HTTP client, etc.)."""
    closer = getattr(adapter, "close", None)
    if callable(closer):
        try:
            closer()
        except Exception:
            pass

# A zero-argument adapter constructor. `run` uses ONE of these per target for both the receipt
# instance and the per-unit instances at workers>1, so the two can never diverge.
AdapterFactory = Callable[[], MemoryAdapter]

class EmptyRetrieval(MemrankError):
    """A target that is supposed to retrieve returned nothing, for every query in the run."""


def _assert_retrieved_something(adapter, per_query: list[dict[str, Any]]) -> None:
    """Fail a run where a retrieving engine returned nothing at all.

    A per-query miss is ordinary. Zero documents across an ENTIRE run, from an engine whose whole
    purpose is retrieval, is a broken engine wearing a valid-looking number -- and that is worse
    than an error, because it is indistinguishable from a real result.

    It happened: the mem0 adapter sent a search parameter this engine does not honour, so it
    ingested perfectly and retrieved nothing on every run memrank ever made. It scored 0.2 on
    `demo` -- identical to the no-memory control, for the same reason, the single negative query --
    and that number was reported as a result repeatedly.

    ``context_budget == "none"`` is the no-memory arm, which retrieves nothing BY DESIGN and is
    exempt. The manifest already carries this, so the guard needs no new concept.

    Raises:
        EmptyRetrieval: When a retrieving target returned zero documents for every query.
    """
    if getattr(adapter, "context_budget", "matched") == "none":
        return                       # the no-memory arm: retrieving nothing is the point
    if not per_query:
        return
    if any(len(row.get("retrieved") or ()) for row in per_query):
        return
    raise EmptyRetrieval(
        f"{getattr(adapter, 'name', 'adapter')!r} retrieved 0 documents across all "
        f"{len(per_query)} queries. An engine that ingests and cannot recall scores like the "
        f"no-memory control instead of failing, so this is refused rather than recorded. Check the "
        f"engine's search contract -- a parameter it silently ignores is the usual cause.")

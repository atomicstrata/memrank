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
"""Core abstractions for Memrank.

Defines the two contracts every adapter and benchmark must implement, plus the
shared ``Document`` / ``AdapterResponse`` / ``BenchmarkUnit`` value types.

The ABCs are intentionally minimal. Adapters wrap a memory engine; benchmarks
wrap a dataset + scorer. Everything else (latency capture, token capture,
receipt generation) is composed around them by the runner.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime
from typing import TYPE_CHECKING, Any, ClassVar

if TYPE_CHECKING:  # `judge_shape` reaches `judge`; keep that out of `core`'s import graph.
    from memrank.judging.shape import JudgeShape

#: The keys ``latency_metrics`` and ``token_metrics`` must emit. Named here, beside the abstract
#: methods that promise them, because three places assert on this shape -- the conformance suite,
#: `memrank targets verify`, and the adapters themselves -- and a list restated per site is one
#: edit away from three different contracts.
REQUIRED_LATENCY_KEYS: frozenset[str] = frozenset({
    "ingest_p50_ms", "ingest_p95_ms", "ingest_p99_ms",
    "retrieve_p50_ms", "retrieve_p95_ms", "retrieve_p99_ms",
})
REQUIRED_TOKEN_KEYS: frozenset[str] = frozenset({
    "tokens_per_query_mean", "tokens_per_query_p95",
    "tokens_per_ingest_mean", "tokens_per_ingest_p95",
})


@dataclass
class Document:
    """A single piece of content the adapter ingests or returns.

    The shape mirrors what every benchmark loader produces: a stable ``id``,
    free-form ``content``, an optional ``user_id`` for isolation scoping, an
    optional ``timestamp`` (ISO-8601), and an optional structured ``messages``
    list when the source has multi-turn structure.

    Adapters should treat ``content`` as the canonical text payload.
    """

    id: str
    content: str
    user_id: str | None = None
    timestamp: str | None = None
    context: str | None = None
    messages: list[dict[str, Any]] | None = None
    metadata: dict[str, Any] = field(default_factory=dict)

    def __repr__(self) -> str:
        # Truncated by hand rather than dataclass-generated: a corpus document is
        # kilobytes of text, and a notebook cell showing a list of these must read as an
        # inventory, not a transcript. The size says what the ellipsis hides.
        size = len(self.content.encode("utf-8"))
        head = self.content[:40].replace("\n", " ")
        ellipsis = "…" if len(self.content) > 40 else ""
        scope = f", user_id={self.user_id!r}" if self.user_id is not None else ""
        return f"Document({self.id!r}{scope}, {size:,}B: {head!r}{ellipsis})"


@dataclass
class AdapterResponse:
    """Output from a single adapter ``retrieve`` call against one query.

    ``documents`` is the ranked list returned by the adapter; ``raw`` is the
    untouched provider payload (kept for forensic debugging in the receipt);
    ``latency_ms`` is wall-clock time as measured by the runner.
    """

    query_id: str
    documents: list[Document]
    raw: dict[str, Any] | None = None
    latency_ms: float | None = None
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class BenchmarkUnit:
    """A scoring unit for a benchmark.

    A unit is the smallest piece of work a benchmark scores independently.
    For LoCoMo it's a conversation; for BEAM it's a conversation x ability;
    for LongMemEval it's a single QA item. Each unit carries its own
    ``isolation_id`` so the adapter can scope memory state correctly.
    """

    unit_id: str
    isolation_id: str
    documents: list[Document]
    queries: list[dict[str, Any]]
    metadata: dict[str, Any] = field(default_factory=dict)

    def __repr__(self) -> str:
        # Counts, not contents: the generated repr inlined every document's full text,
        # which made `bench.load()` in a notebook print the whole corpus.
        return (f"BenchmarkUnit({self.unit_id!r}, documents={len(self.documents)}, "
                f"queries={len(self.queries)})")


class MemoryAdapter(ABC):
    """The contract every memory engine implements to be benchmarkable.

    Subclasses declare ``name``, ``version`` (the adapter's own version) and
    ``engine_version`` (the wrapped engine's version) as class attributes.
    The runner exercises adapters in this lifecycle:

        for unit in benchmark.load():
            adapter.prepare(unit.isolation_id)
            adapter.ingest(unit.documents)
            for query in unit.queries:
                docs, meta = adapter.retrieve(query["text"], k, query["user_id"])
            adapter.cleanup()
        adapter.latency_metrics()
        adapter.token_metrics()

    Adapters MUST be deterministic given the same seed (or document
    non-determinism explicitly). They MUST emit latency and token data via
    Memrank's instrumentation hooks rather than measuring those axes
    internally.
    """

    name: str = "abstract"
    version: str = "0.0.0"
    engine_version: str = "unknown"
    # Whether this adapter emits a graph snapshot (``raw["graph_snapshot"]``) and
    # can therefore satisfy a ``requires_graph`` benchmark. False by default; the
    # runner SKIPS (adapter, benchmark) cells where the benchmark needs a graph
    # but the adapter is not graph-capable, rather than crashing in the scorer.
    graph_capable: bool = False
    # How much retrieved context this adapter may hand the reader. "matched" -- the default for every
    # real engine -- caps it at the shared ``--token-budget``, which is the project's central fairness
    # control: a row must not win by dumping more text. Only the full-context control arm sets
    # "uncapped"; only the no-memory arm sets "none".
    context_budget: str = "matched"
    # Whether this adapter returns a RANKED list. False for the in-context controls, which hand
    # back the whole store in ingest order -- rank-cut metrics (recall_all@k, ndcg_any@k) are
    # undefined for them, and reporting 0.0 reads as total retrieval failure when the arm in fact
    # returned everything. LongMemEval's own harness draws the same line: retrieval metrics come
    # from `run_retrieval.py`'s ranked output, and its `full-history-session` / `no-retrieval`
    # generation modes are never scored on them at all.
    ranks_results: bool = True

    @abstractmethod
    def prepare(self, isolation_unit: str) -> None:
        """Set up state for a fresh benchmark unit.

        The ``isolation_unit`` is the per-conversation, per-question, or
        per-user identifier from the benchmark. Adapters MUST guarantee that
        nothing ingested in a previous unit leaks into this one.
        """

    @abstractmethod
    def ingest(self, documents: list[Document]) -> None:
        """Load documents into the engine for the current isolation unit."""

    @abstractmethod
    def retrieve(
        self,
        query: str,
        k: int,
        user_id: str,
        query_timestamp: datetime | str | None = None,
    ) -> tuple[list[Document], dict[str, Any]]:
        """Return the top-k ranked documents plus a metadata dict.

        The metadata dict is the raw provider response; the runner stores it
        in the reproducibility receipt for forensic debugging.
        """

    @abstractmethod
    def cleanup(self) -> None:
        """Tear down state for the current isolation unit."""

    @abstractmethod
    def latency_metrics(self) -> dict[str, float]:
        """Return ingest/retrieve p50/p95/p99 in milliseconds.

        Required keys: ``ingest_p50_ms``, ``ingest_p95_ms``, ``ingest_p99_ms``,
        ``retrieve_p50_ms``, ``retrieve_p95_ms``, ``retrieve_p99_ms``.
        """

    @abstractmethod
    def token_metrics(self) -> dict[str, float | None]:
        """Return per-call token statistics.

        Required keys: ``tokens_per_query_mean``, ``tokens_per_query_p95``,
        ``tokens_per_ingest_mean``, ``tokens_per_ingest_p95``.

        A key whose value is ``None`` means the engine reported no usage for that bucket, which is
        the common case -- an engine that genuinely spent no tokens reports 0.0. The two are
        different claims and must not share a value.
        """

    def declare_components(
        self,
        *,
        llm: dict[str, Any] | None = None,
        embedder: dict[str, Any] | None = None,
        transport: str | None = None,
        verified: str | None = None,
    ) -> None:
        """Record the components a resolved target manifest declares for this adapter.

        Set by the target factory after construction, so a manifest -- not ambient environment --
        describes what the run record reports. Anything left ``None`` keeps the adapter's own
        env-derived answer, so an adapter that is never declared behaves exactly as before.

        This is a precedence rule, not a fallback: the factory cross-checks the manifest against the
        environment and raises on any disagreement *before* calling this, so the two sources can
        never silently differ by the time precedence applies.
        """
        self._declared: dict[str, Any] = {
            key: value for key, value in
            (("llm", llm), ("embedder", embedder), ("transport", transport),
             ("verified", verified))
            if value is not None
        }

    def effective_config(self) -> dict[str, Any]:
        """Return the components this adapter actually used, for the run record.

        Captures the memory-engine identity plus the (operator-declared) LLM and
        embedder the backend is configured with. Recording the LLM/embedder here --
        even before they are tunable knobs -- keeps runs comparable when they are
        later promoted to explicit parameters. Values default to ``None`` and this
        never raises. Subclasses override ``_effective_llm`` / ``_effective_embedder``;
        :meth:`declare_components` overrides both.
        """
        declared: dict[str, Any] = getattr(self, "_declared", {})
        return {
            "engine": {
                "name": self.name,
                "version": self.version,
                "engine_version": self.engine_version,
                "transport": declared.get("transport", getattr(self, "transport", "unknown")),
            },
            "llm": declared.get("llm", self._effective_llm()),
            "embedder": declared.get("embedder", self._effective_embedder()),
            # How much this record can be trusted: "engine" when the engine confirmed it,
            # "declared" when the engine cannot be asked. Deliberately not a boolean -- "not asked"
            # and "asked and failed" are different, and a mismatch never reaches here (it raises).
            "verified": declared.get("verified", "declared"),
        }

    def describe_engine(self) -> dict[str, Any] | None:
        """The engine's OWN report of the components it is running, or ``None``.

        This is the only path by which memrank learns what an engine is actually configured with
        rather than what an operator claims. Returning ``None`` means "this engine cannot be asked"
        -- which is the honest answer for most engines, and is recorded as such in the run record
        instead of being presented as a passed check.

        Shape mirrors :meth:`effective_config`: ``{"llm": {provider, model},
        "embedder": {provider, model, dims}}``. Any key may be absent when the engine does not
        report it; only the keys present are compared.

        Raises:
            Exception: Transport failures propagate. An unreachable engine is a real failure, not a
                reason to skip the check -- the run would fail moments later at ingest anyway.
        """
        return None

    def state_fingerprint(self, scope: str) -> str | None:
        """A digest of everything stored under ``scope``, or ``None`` if the engine cannot say.

        Exists to answer one question that cannot be answered any other way: after a failed
        ingest, **did anything get written?** Only the engine knows, and the answer decides whether
        retrying is safe.

        mem0's ``add()`` is three steps -- extract, reconcile, then a loop that writes. A failure in
        the first two wrote nothing and a retry is exactly equivalent to never having failed. A
        failure inside the loop leaves the scope half-written, and re-running extraction against a
        partially populated store makes correctness depend on the reconcile LLM noticing, which is
        not something a benchmark number should rest on. Comparing this digest before and after
        distinguishes the two cases instead of assuming one.

        ``None`` -- the default -- means "this engine cannot be asked", the honest answer for most,
        and the runner treats it as CANNOT PROVE SAFE rather than as permission. An engine without
        it simply does not get retried.

        Must digest CONTENT, not just a count: reconciliation can UPDATE a memory in place, which
        rewrites text while leaving the number of memories unchanged.

        Must be stable across repeated reads of an unchanged store -- sort before hashing, since
        result order is a vector store's business and not a change in state.

        Args:
            scope: The isolation unit whose state to digest -- the same value ``prepare`` was given.

        Returns:
            A digest, or ``None`` when the engine exposes no way to enumerate its own state.
        """
        return None

    def _effective_llm(self) -> dict[str, Any]:
        """Provider/model of the engine's extraction LLM (override to populate)."""
        return {"provider": None, "model": None}

    def _effective_embedder(self) -> dict[str, Any]:
        """Model/dims of the engine's embedder (override to populate)."""
        return {"model": None, "dims": None}


# Human-facing labels/descriptions for a benchmark's composite quality metric,
# keyed by Benchmark.quality_metric. Unknown kinds fall back to the raw name.
QUALITY_METRIC_LABELS = {"substring_recall": "recall", "graph_score": "graph score",
                         "judged_answer_correctness": "judged correctness",
                         "judged_nugget_rubric": "judged rubric"}
QUALITY_METRIC_DESCRIPTIONS = {
    "substring_recall": "retrieval recall (a substring proxy), not end-to-end answer correctness",
    "graph_score": "a relation-graph structural score (graph correctness), not retrieval coverage or answer correctness",
    # The external benchmarks' own protocols. They ship no self-contained number, which is why
    # these evals judge by default rather than asking -- and why `--no-judge` yields a run with no
    # quality score at all rather than a lesser one.
    "judged_answer_correctness": "LLM-judged answer correctness against the dataset's reference answer (judged by default; `--no-judge` reports no quality score)",
    "judged_nugget_rubric": "LLM-judged rubric coverage, one call per atomic nugget (judged by default; `--no-judge` reports no quality score)",
}


@dataclass(frozen=True)
class EvalInfo:
    """Static, declared description of an eval for ``memrank evals show``.

    DECLARED, never loaded: rendering this must not construct units or touch the
    dataset cache -- ``evals show`` is a catalog view, not a download trigger. Which
    is also why sizes are prose claims (``units_declared``) rather than counts: a
    real count would require ``load()``.
    """

    unit: str
    """What one scoring unit is, e.g. ``"conversation"``."""
    units_declared: str
    """Prose size claim from the dataset's own description (declared, not counted)."""
    slices: tuple[str, ...]
    """Named slices besides full, e.g. ``("smoke", "mini")``."""
    tiers: tuple[str, ...] = ()
    """Named tiers, leading with the default; empty means no tier dimension."""


class Benchmark(ABC):
    """The contract every benchmark dataset+scorer implements."""

    name: str = "abstract"
    dataset_version: str = "unknown"
    # Catalog metadata for `evals show`. Declared per benchmark with no default:
    # a benchmark without one fails loudly the first time the catalog asks.
    info: ClassVar[EvalInfo]
    # Whether the deterministic substring-recall proxy is a meaningful quality
    # signal for this benchmark. False for benchmarks whose gold answers are
    # prose / not verbatim spans (e.g. BEAM ideal_responses), where substring
    # recall is structurally ~0 and must be withheld in favor of an LLM judge.
    substring_recall_supported: bool = True
    # Whether ``composite`` is a self-contained quality score to DISPLAY and RANK
    # as-is, without an LLM judge. DECOUPLED from substring_recall_supported: a
    # graph benchmark sets substring_recall_supported=False (substring recall is
    # N/A) yet composite_rankable=True (its composite IS a real graph score).
    # False for benchmarks whose raw composite is not rankable without a judge
    # (e.g. BEAM prose golds) -- withheld from rankings, shown as "judge required".
    composite_rankable: bool = True
    # Name/kind of the composite metric, driving the displayed column label and
    # the leaderboard quality kind (e.g. "substring_recall", "graph_score").
    quality_metric: str = "substring_recall"
    # Whether this benchmark's data is synthetic (safe to send to an LLM judge
    # without explicit egress consent). Real datasets must be False so judged
    # runs require --ack-egress. Keyed on the benchmark, never on its name.
    is_synthetic: bool = False
    # Whether this run's question text comes from a canonical PUBLIC dataset and
    # may appear in a public default drill-in. False for any local-path override
    # (which may point at private data). Persisted into artifacts at run time.
    question_text_public: bool = False
    # Whether this benchmark needs an adapter graph snapshot to score. When True,
    # the runner SKIPS cells whose adapter is not ``graph_capable`` with a
    # ``not_applicable`` result instead of running (and crashing in) the scorer.
    requires_graph: bool = False
    # The benchmark protocol's reader-context policy, in the adapter-side ``context_budget``
    # vocabulary. "matched" -- the default -- leaves the shared --token-budget cap in force (the
    # leaderboard's fairness control). "uncapped" declares that this benchmark's own protocol
    # hands the reader everything retrieval returned (BEAM: every published harness runs
    # uncapped, so a capped run is not that benchmark). The runner promotes matched arms
    # accordingly; the no-memory arm ("none") is never promoted.
    context_policy: str = "matched"
    # Task/scoring definition version (lm-eval-harness pattern). Bump on any
    # BREAKING change to how this benchmark loads or scores, so version-vs-version
    # comparison can flag "not directly comparable" instead of silently comparing
    # scores computed under different definitions. Distinct from ``dataset_version``
    # (the data) -- this versions the code/definition.
    VERSION: int = 0

    def __repr__(self) -> str:
        """Class, registry name, and the declared knobs -- never the data.

        Built from :meth:`config_for_receipt` (the same knobs artifacts record), so
        what a notebook shows and what a receipt hashes cannot disagree. I/O-free by
        the same contract as construction: rendering this must not call ``load()``.
        """
        knobs = " ".join(f"{key}={value}" for key, value in self.config_for_receipt().items()
                         if value is not None)
        detail = f" {knobs}" if knobs else ""
        return f"<{type(self).__name__} {self.name!r}{detail}>"

    def raw(self) -> list[dict[str, Any]]:
        """This benchmark's records exactly as upstream ships them, before normalisation.

        ``load()`` returns ``BenchmarkUnit``s -- the harness's shape, which every
        benchmark's upstream records have already been flattened, chunked and relabelled
        into. This returns what came off HuggingFace or GitHub, so a reader can see what
        the benchmark's authors actually published, including the fields loading
        deliberately drops (BEAM's ``user_profile`` and ``time_anchor``, LoCoMo's
        adversarial category 5). Uses THIS instance's configuration -- a
        ``BEAMBenchmark(tier="500k")`` answers for its own tier.

        Downloads, caches and digest-verifies exactly as a real run does, because it
        goes through the benchmark's own loader rather than a second copy of the fetch
        logic. First call on a cold cache may take minutes.
        """
        # Dispatch on what the benchmark HAS, not on its name: a renamed entry in the
        # registry would otherwise fall through to the error below while still being
        # perfectly readable.
        if (fetch := getattr(self, "_load_raw", None)) is not None:
            return fetch()                                            # beam, locomo, longmemeval
        if (fixtures := getattr(self, "_fixtures", None)) is not None:
            return list(fixtures())                                   # relation_graph
        if (path := getattr(self, "_path", None)) is not None:
            import json
            from pathlib import Path

            return [json.loads(Path(path).read_text(encoding="utf-8"))]  # demo, one scenario
        raise NotImplementedError(
            f"{self.name!r} exposes no raw records: it defines none of "
            f"_load_raw, _fixtures, _path")

    def config_for_receipt(self) -> dict[str, Any]:
        """Benchmark-specific reproducibility knobs to record in artifacts AND
        the receipt hash, so runs at different settings don't collide. The base
        captures the common ``tier``/``slice`` dimensions plus the task ``VERSION``;
        override to add more (it's part of the contract -- new dimensions must be
        exposed here)."""
        return {"tier": getattr(self, "tier", None),
                "slice": getattr(self, "slice", None),
                "task_version": self.VERSION}

    def rollup(self, per_unit_scores: list[dict[str, Any]], *,
               ranked: bool = True) -> dict[str, Any]:
        """Run-level metrics reduced from every unit's ``score()`` dict. Empty by default.

        The counterpart of :meth:`JudgeShape.aggregates` on the unjudged side. It exists because
        a per-unit metric nobody reduces is a metric nobody can read: LongMemEval's
        ``recall_all@k`` and LoCoMo's ``evidence_recall`` were both computed per unit, stored
        under ``per_unit``, and never turned into a number -- while ``composite`` (the only thing
        that WAS reduced) is None for both by design.

        Implementations must weight by each unit's own denominator rather than averaging unit
        means, so a unit covering three scoreable queries outweighs one covering a single query,
        and so units excluded from a metric contribute nothing instead of contributing a zero.

        ``ranked`` is the adapter's :attr:`MemoryAdapter.ranks_results`. A rank-cut metric is
        undefined for an arm that returns the whole store unordered, and a benchmark declaring
        one must report None rather than a 0.0 that reads as retrieval failure.
        """
        return {}

    def judge_shape(self) -> JudgeShape:
        """How this benchmark's answers are graded under ``--judge``.

        The default is one answer, one verdict, one boolean -- right for any benchmark whose
        questions have a single gold answer, which is every one of them except BEAM. BEAM scores
        against a rubric of atomic nuggets, one judge call each, averaged within the question;
        that is a different SHAPE of judging, and overriding this is how a benchmark says so
        without the runner having to know which benchmark it is holding.

        The binary default carries ``GENERIC_BINARY_CATEGORIES`` -- the vocabulary of the demo
        benchmark and ad-hoc units only. A benchmark with a real category taxonomy overrides
        this and declares its own set (LoCoMo, LongMemEval), so its loader's labels and its
        judge gate cannot drift apart.

        Imported lazily: ``memrank.judging.shape`` imports ``memrank.judging.judge``, and a
        module-level import here would drag the judge into every consumer of ``core``.
        """
        from memrank.judging.shape import GENERIC_BINARY_CATEGORIES, BinaryJudgeShape
        return BinaryJudgeShape(GENERIC_BINARY_CATEGORIES)

    @abstractmethod
    def load(self) -> list[BenchmarkUnit]:
        """Return all benchmark units to score."""

    @abstractmethod
    def score(
        self,
        unit: BenchmarkUnit,
        responses: list[AdapterResponse],
    ) -> dict[str, Any]:
        """Score adapter responses for a single unit.

        Returns a dict with at minimum a ``composite`` float in [0, 1] and a
        ``per_category`` mapping when the benchmark has sub-categories.
        """

    @abstractmethod
    def report_template(self) -> str:
        """Markdown template used to render the per-benchmark report."""

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

Defines the two contracts every adapter and benchmark must implement. The value types
they exchange -- ``Document``, ``Recall``, ``AdapterResponse``, ``BenchmarkUnit``,
``EvalInfo`` and the required metric keys -- live in :mod:`memrank.contract` and are
re-exported here, which is where every caller has always imported them from.

The ABCs are intentionally minimal. Adapters wrap a memory engine; benchmarks
wrap a dataset + scorer. Everything else (latency capture, token capture,
receipt generation) is composed around them by the runner.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from datetime import datetime
from typing import TYPE_CHECKING, Any, ClassVar

from memrank.contract import (
    REQUIRED_LATENCY_KEYS as REQUIRED_LATENCY_KEYS,  # noqa: PLC0414 - re-export only
)

# Re-exported, not merely used: `memrank.core` is the import path every adapter, benchmark and
# caller in the tree already names for these, and moving the definitions must not move that.
from memrank.contract import (
    REQUIRED_TOKEN_KEYS,
    AdapterResponse,
    BenchmarkUnit,
    Document,
    EvalInfo,
    Recall,
)
from memrank.instrument.system import System
from memrank.quality import DATASET_VERSION_UNSET, QUALITY_METRICS

if TYPE_CHECKING:  # `judge_shape` reaches `judge`; keep that out of `core`'s import graph.
    from memrank.judging.shape import JudgeShape


class MemoryAdapter(System):
    """The contract every memory engine implements to be benchmarkable.

    Subclasses declare ``name``, ``version`` (the adapter's own version) and
    ``engine_version`` (the wrapped engine's version) as class attributes.
    The runner exercises adapters in this lifecycle:

        for unit in benchmark.load():
            adapter.prepare(unit.isolation_id)
            adapter.ingest(unit.documents)
            for query in unit.queries:
                recall = adapter.retrieve(query["text"], k, query["user_id"])
            adapter.cleanup()

    Four lifecycle methods, and nothing that reports a measurement Memrank takes
    itself: latency is timed at Memrank's own call boundary, so an engine neither
    has to report it nor can flatter it (ATO-2136). What only an engine can know
    it may DECLARE, and both declarations are optional: :meth:`token_metrics` for
    what a provider billed it, and :meth:`declared_latency` for its own spend
    inside the hop Memrank timed around it.

    Adapters MUST be deterministic given the same seed (or document
    non-determinism explicitly).
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
    # The environment variable that moves this adapter's engine address, named so a failure can
    # quote it. Every adapter that talks to an engine over the network declares one; the in-process
    # adapters leave it None, which is what makes "there is no address to change" sayable rather
    # than an omission. Read by `memrank.adapters.preflight`, which is the only place a user is
    # told where memrank looked -- a message that describes the setting instead of naming it sends
    # the reader to the source to find out what it is called.
    base_url_env: str | None = None

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
    ) -> Recall:
        """Return what this engine recalled for one query.

        A :class:`~memrank.contract.Recall`: at most ``k`` documents in the order the
        engine ranked them -- the order IS the measurement, so never pad the list -- and
        ``declared``, the provider response untouched, which the runner stores in the
        reproducibility receipt for forensic debugging.

        An engine with nothing to declare leaves ``declared`` empty. Failures raise; an
        empty ``documents`` means "searched, found none".
        """

    @abstractmethod
    def cleanup(self) -> None:
        """Tear down state for the current isolation unit."""

    def declared_latency(self) -> dict[str, list[float]]:
        """Declare timings only this engine can see. Optional, and never the wall clock.

        memrank times every ingest and retrieve at its own call boundary and reports that as the
        run's latency, so there is nothing here for an engine to report twice or to flatter. What
        an engine CAN add is time nobody outside it can see -- a translator's ``engine_ms``, the
        engine's own spend inside the hop memrank measured around it.

        SAMPLES per bucket, in milliseconds, not percentiles: memrank pools them across the
        adapters a ``--workers`` run builds and renders ``<bucket>_p50_ms`` / ``<bucket>_p95_ms``
        itself, so a run at any width reports the same statistic of the same population. An engine
        rendering its own percentiles cannot be pooled, only picked between.

        The conventional buckets are ``ingest_engine`` and ``retrieve_engine``, which is what
        `docs/adapter-contract.md` section 7 already calls the figure to quote when discussing the
        engine rather than the harness. Declared, not verified: memrank cannot check it, and it is
        never the headline.
        """
        return {}

    def token_metrics(self) -> dict[str, float | None]:
        """Declare per-call token usage, where this engine is told what it spent. Optional.

        Keys: ``tokens_per_query_mean``, ``tokens_per_query_p95``, ``tokens_per_ingest_mean``,
        ``tokens_per_ingest_p95``. :class:`memrank.instrumentation.TokenCollector` renders them.

        A key whose value is ``None`` means the engine reported no usage for that bucket, which is
        the common case -- an engine that genuinely spent no tokens reports 0.0. The two are
        different claims and must not share a value. The default declares ``None`` throughout,
        which is the honest answer for an engine that cannot be asked, and is the same shape
        :meth:`describe_engine` returns ``None`` for.

        Not abstract, because an engine is not improved by writing a stub: it was required of
        everyone and never checked, and a run whose engine returned ``{}`` from both metric
        methods completed and produced a composite (ATO-2136). What memrank REPORTS for latency
        is its own measurement; what it reports here is this declaration.
        """
        return dict.fromkeys(REQUIRED_TOKEN_KEYS, None)

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
#
# DERIVED from `memrank.quality.QUALITY_METRICS`, which holds the same prose split into the
# parts a result can carry by name -- what the number is OF, and what it is NOT. These two
# dicts are byte-identical to the literals they replaced and every reader of them is
# unchanged; the split exists so the caveat is reachable from a result rather than only from
# the terminal. `tests/core/test_quality_declarations.py` pins the byte-identity.
QUALITY_METRIC_LABELS = {kind: d.label for kind, d in QUALITY_METRICS.items()}
QUALITY_METRIC_DESCRIPTIONS = {kind: d.description for kind, d in QUALITY_METRICS.items()}



class Benchmark(ABC):
    """The contract every benchmark dataset+scorer implements."""

    name: str = "abstract"
    #: The version of the material this benchmark asks its questions against.
    #: :data:`~memrank.quality.DATASET_VERSION_UNSET` -- the default -- means the author did
    #: not state one. :data:`~memrank.quality.UNFREEZABLE` means the material CANNOT be
    #: frozen, and a run over it makes no reproducibility claim in its receipt. The two are
    #: deliberately different values: one is a gap, the other is an honest statement.
    dataset_version: str = DATASET_VERSION_UNSET
    # Catalog metadata for `evals show`. Declared per benchmark with no default:
    # a benchmark without one fails loudly the first time the catalog asks. Annotated rather
    # than `ClassVar` so a benchmark ASSEMBLED at runtime -- `ComposedEvaluation` -- can declare
    # its own; a class-body assignment and `cls.info` both read exactly as they did.
    info: EvalInfo
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
    # The scored keys this benchmark's questions EXPECT their scorer to produce -- the
    # declaration `memrank.composition.ComposedEvaluation` checks the scorer's against when the
    # two halves are supplied separately (ATO-2149). Empty -- the default, and what all five
    # registered benchmarks declare -- means "whatever the scorer produces", which is what keeps
    # somebody else's criteria acceptable over memrank's questions. Declare it only when this
    # benchmark's own aggregation names a criterion literally and so cannot take another's.
    criterion_names: ClassVar[tuple[str, ...]] = ()
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


#: The engine, under the noun the four-noun model uses. The same class object rather than a
#: subclass, so ``isinstance(x, MemoryAdapter)`` and every registered adapter keep holding
#: while both names are live. `MemoryAdapter` is deprecated and goes at plan step 22.
MemoryEngine = MemoryAdapter

#: The evaluation, under the same rule. `Benchmark` is deprecated and goes at step 22 -- it
#: is also the field's word for a fixed set of tests with a scoreboard, which is what memrank
#: is not.
Evaluation = Benchmark

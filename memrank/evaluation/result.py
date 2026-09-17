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
"""The typed result of one evaluated cell -- and the artifact schema's single owner.

``EvalResult.to_dict()`` emits the per-cell artifact dict byte-for-byte as the pre-split
``_aggregate_cell`` built it (``aggregate.build_result`` constructs the instance, and the
dict form is consumed as-is by ten downstream modules: registry, record, leaderboard,
API projection, the uploader). Two rules keep that contract honest, both pinned by
``tests/orchestration/test_golden_run.py``:

- ``judged_metrics`` is ABSENT when no judge ran, never null -- absent means "no judge
  ran"; null would claim a judge ran and produced nothing.
- ``rollup`` and ``benchmark_config`` are spread LAST, so a benchmark-declared key
  shadows a closed one exactly as the two trailing ``**`` spreads always have.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from memrank.evaluation.constants import DEFAULT_JUDGE_WORKERS


@dataclass(frozen=True)
class EvalResult:
    """One (adapter x benchmark) cell's complete result.

    Frozen: a result is a record of a measurement, and nothing downstream may edit one in
    place. The one post-hoc addition the run lifecycle makes -- the target ref -- goes
    through ``dataclasses.replace``.
    """

    adapter: str
    benchmark: str
    composite: float | None
    #: ``"not_applicable"`` for the cell a capability gate skipped; ``None`` for a cell
    #: that ran. The skipped shell serializes as exactly five keys.
    status: str | None = None
    reason: str | None = None
    per_unit: list[dict[str, Any]] = field(default_factory=list)
    per_query: list[dict[str, Any]] = field(default_factory=list)
    ingested_documents: list[dict[str, Any]] = field(default_factory=list)
    latency_metrics: dict[str, Any] = field(default_factory=dict)
    retrieve_latency_summary: dict[str, Any] | None = None
    ingest_latency_summary: dict[str, Any] | None = None
    ingest_throughput: dict[str, float] | None = None
    token_metrics: dict[str, Any] = field(default_factory=dict)
    corpus_documents: int = 0
    corpus_bytes: int = 0
    corpus_tokens: int = 0
    workers: int = 1
    latency_contended: bool = False
    judge_workers: int = DEFAULT_JUDGE_WORKERS
    context_tokens_mean: float = 0.0
    est_dollars_per_query: float = 0.0
    est_dollars_per_cell: float = 0.0
    cost_basis: dict[str, Any] = field(default_factory=dict)
    cleanup_is_destructive: bool | None = None
    substring_recall_supported: bool = True
    composite_rankable: bool = True
    quality_metric: str = "substring_recall"
    question_text_public: bool = False
    receipt: dict[str, Any] = field(default_factory=dict)
    n_units: int = 0
    k: int = 0
    repeats: int = 0
    #: One record per unit ATTEMPTED, in unit order: ``{"unit_id", "outcome"}`` for a unit that
    #: ran, plus ``stage``/``error``/``message`` for one that did not. Empty for a cell built
    #: without them (``_aggregate_cell``'s legacy callers), which is why the three counts below
    #: are read from this list rather than from ``n_units``.
    unit_outcomes: list[dict[str, Any]] = field(default_factory=list)
    #: Units attempted, units lost, and the ratio -- beside the composite because the composite
    #: is a mean over the units that RAN. 50 of 385 units scored is not a score over 385, and
    #: without these nothing in the artifact says which it is. ``unit_failure_rate`` is None for
    #: a cell with no units, on the same None-vs-0.0 rule the composite follows.
    units_total: int = 0
    units_failed: int = 0
    unit_failure_rate: float | None = None
    #: ``benchmark.rollup(...)`` -- run-level metrics the benchmark reduces itself.
    #: Open keys: the benchmark names them, the schema does not.
    rollup: dict[str, Any] = field(default_factory=dict)
    #: ``benchmark.config_for_receipt()`` -- the benchmark-specific knobs (tier, slice,
    #: task_version, ...). Open keys, same contract as ``rollup``.
    benchmark_config: dict[str, Any] = field(default_factory=dict)
    judged_metrics: dict[str, Any] | None = None
    #: The target REF this cell ran as, injected by the run lifecycle after the fact --
    #: the eval loop measures an adapter and does not know its catalog name.
    target: str | None = None

    @property
    def is_applicable(self) -> bool:
        return self.status != "not_applicable"

    @property
    def headline(self):
        """The one summary figure readers rank on -- `metrics.headline` owns the rule."""
        from memrank.metrics import headline

        return headline.cell_headline(self.to_dict())

    @classmethod
    def not_applicable(cls, adapter_name: str, benchmark_name: str, *,
                       reason: str) -> EvalResult:
        return cls(adapter=adapter_name, benchmark=benchmark_name, composite=None,
                   status="not_applicable", reason=reason)

    def to_dict(self) -> dict[str, Any]:
        """The exact artifact dict, in the construction order the schema has always had."""
        if self.status == "not_applicable":
            return {
                "adapter": self.adapter,
                "benchmark": self.benchmark,
                "status": "not_applicable",
                "composite": None,
                "reason": self.reason,
            }
        out: dict[str, Any] = {
            "adapter": self.adapter,
            "benchmark": self.benchmark,
            "composite": self.composite,
            "per_unit": self.per_unit,
            "per_query": self.per_query,
            "ingested_documents": self.ingested_documents,
            "latency_metrics": self.latency_metrics,
            "retrieve_latency_summary": self.retrieve_latency_summary,
            "ingest_latency_summary": self.ingest_latency_summary,
            "ingest_throughput": self.ingest_throughput,
            "token_metrics": self.token_metrics,
            "corpus_documents": self.corpus_documents,
            "corpus_bytes": self.corpus_bytes,
            "corpus_tokens": self.corpus_tokens,
            "workers": self.workers,
            "latency_contended": self.latency_contended,
            "judge_workers": self.judge_workers,
            "context_tokens_mean": self.context_tokens_mean,
            "est_dollars_per_query": self.est_dollars_per_query,
            "est_dollars_per_cell": self.est_dollars_per_cell,
            "cost_basis": self.cost_basis,
            "cleanup_is_destructive": self.cleanup_is_destructive,
            "substring_recall_supported": self.substring_recall_supported,
            "composite_rankable": self.composite_rankable,
            "quality_metric": self.quality_metric,
            "question_text_public": self.question_text_public,
            "receipt": self.receipt,
            "n_units": self.n_units,
            "k": self.k,
            "repeats": self.repeats,
            "unit_outcomes": self.unit_outcomes,
            "units_total": self.units_total,
            "units_failed": self.units_failed,
            "unit_failure_rate": self.unit_failure_rate,
            **self.rollup,
            **self.benchmark_config,
        }
        if self.judged_metrics is not None:
            out["judged_metrics"] = self.judged_metrics
        if self.target is not None:
            out["target"] = self.target
        return out

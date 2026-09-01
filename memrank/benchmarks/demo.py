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
"""Hand-crafted demo benchmark.

A small, synthetic, multi-session conversation with durable facts, distractors,
and a negative/abstention query -- authored so engines genuinely differ and a
lazy "non-empty retrieval" cannot win. Scored by the evidence-based scorer.
"""

from __future__ import annotations

import json
import os
from collections import defaultdict
from pathlib import Path
from typing import Any

from memrank.core import AdapterResponse, Benchmark, BenchmarkUnit, Document, EvalInfo
from memrank.metrics.scoring import score_query, spec_from_query

_DEFAULT_DATA = (
    Path(__file__).resolve().parents[2] / "examples" / "data" / "demo_scenario.json"
)


class DemoBenchmark(Benchmark):
    """Single-unit synthetic benchmark loaded from a JSON scenario file."""

    name = "demo"
    dataset_version = "memrank-demo@v1"
    info = EvalInfo(unit="scenario",
                    units_declared="1 hand-crafted multi-session scenario (bundled JSON)",
                    slices=())

    def __init__(self, slice: str | None = None, k: int = 10,
                 data_path: str | None = None) -> None:
        self.k = k
        env = os.environ.get("DEMO_DATA_PATH") or data_path
        self._path = Path(env) if env else _DEFAULT_DATA
        # Only the bundled scenario is synthetic; a DEMO_DATA_PATH/data_path
        # override may point at real data, so it is NOT egress-safe by default.
        self.is_synthetic = env is None
        # Question text is public only when using the bundled synthetic scenario.
        self.question_text_public = self.is_synthetic

    def load(self) -> list[BenchmarkUnit]:
        raw = json.loads(self._path.read_text(encoding="utf-8"))
        documents = [
            Document(id=d["id"], content=d["content"], user_id=raw["isolation_id"],
                     metadata={"doc_id": d.get("doc_id", d["id"])})
            for d in raw["documents"]
        ]
        return [BenchmarkUnit(
            unit_id=raw["unit_id"], isolation_id=raw["isolation_id"],
            documents=documents, queries=raw["queries"])]

    def score(self, unit: BenchmarkUnit,
              responses: list[AdapterResponse]) -> dict[str, Any]:
        by_id = {r.query_id: r for r in responses}
        per_category: dict[str, list[int]] = defaultdict(list)
        all_hits: list[int] = []
        for q in unit.queries:
            r = by_id.get(q["id"])
            res = score_query(spec_from_query(q), r.documents if r else [])
            hit = 1 if res.hit else 0
            all_hits.append(hit)
            per_category[q.get("category", "uncategorized")].append(hit)
        composite = sum(all_hits) / len(all_hits) if all_hits else 0.0
        return {
            "composite": composite,
            "per_category": {c: sum(v) / len(v) for c, v in per_category.items()},
            "n_queries": len(all_hits),
            "metric": "evidence_recall (retrieval proxy; not answer correctness)",
        }

    def report_template(self) -> str:
        return (
            "# Demo report -- {adapter}\n\n"
            "> Quality = retrieval recall proxy, NOT answer correctness.\n\n"
            "- Composite: **{composite}**\n"
            "- Dataset: {dataset_version}\n- k: {k}\n\n"
            "## Per-category recall\n{per_category_md}\n"
        )

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
"""Wire YOUR OWN benchmark into the eval loop -- three methods, no registration.

Run from the repo root:

    python examples/custom-benchmark.py

`memrank.run` takes any `Benchmark` INSTANCE, so a private eval -- your tickets, your
transcripts, your gold answers -- rides the same loop, receipt and `EvalResult` as the
shipped benchmarks. Nothing here touches the registry, the CLI, or the network: the
target is the offline `word-overlap` control arm, and nothing is written to disk.
"""

import memrank
from memrank import Benchmark, BenchmarkUnit, Document
from memrank.metrics.scoring import score_query, spec_from_query


class TicketsBenchmark(Benchmark):
    """A toy 'does the engine remember our support customers' eval.

    The whole third-party contract is the three methods below; judge shape, rollups,
    receipt knobs and rankability flags all have working defaults on the ABC.
    """

    name = "tickets"
    dataset_version = "internal@2026-08"

    def load(self) -> list[BenchmarkUnit]:
        # One unit = one independently scored world (here: one customer). Units are
        # isolated from each other by `isolation_id` -- engines never see across them.
        return [
            BenchmarkUnit(
                unit_id="acme", isolation_id="acme",
                documents=[
                    Document(id="t1", user_id="acme",
                             content="Acme upgraded to the enterprise plan in March."),
                    Document(id="t2", user_id="acme",
                             content="Acme's outage was traced to an expired webhook secret."),
                ],
                # A query dict NEEDS only `id` and `text`. The span-scoring fields
                # (`required_spans`, `forbidden_spans`, `evidence_doc_ids`, `kind`)
                # feed `score()` below; a --judge run would additionally want
                # `gold_answers` and a `category` the judge shape recognizes.
                queries=[
                    {"id": "q_plan", "text": "What plan is Acme on?",
                     "required_spans": ["enterprise"], "evidence_doc_ids": ["t1"]},
                    {"id": "q_outage", "text": "What caused Acme's outage?",
                     "required_spans": ["webhook secret"], "evidence_doc_ids": ["t2"]},
                    # A negative query: the engine should NOT surface this claim.
                    {"id": "q_refund", "text": "Was Acme promised a refund?",
                     "kind": "negative", "forbidden_spans": ["refund approved"]},
                ],
            ),
        ]

    def score(self, unit, responses):
        # Convention: return at least `composite` in [0, 1], plus `per_category` and
        # `n_queries`. `score_query`/`spec_from_query` are the same span helpers the
        # shipped benchmarks use -- reuse them unless your gold is not span-shaped.
        by_id = {r.query_id: r for r in responses}
        hits = [
            1 if score_query(spec_from_query(q),
                             (by_id[q["id"]].documents if q["id"] in by_id else [])).hit
            else 0
            for q in unit.queries
        ]
        return {"composite": sum(hits) / len(hits), "per_category": {},
                "n_queries": len(hits)}

    def report_template(self) -> str:
        return "# tickets {adapter} {composite}"


def main() -> None:
    result = memrank.run("word-overlap", TicketsBenchmark(), repeats=1)

    print(f"composite: {result.composite:.3f}  ({result.benchmark} × {result.target})")
    for row in result.per_query:
        print(f"  {row['query_id']}: {'HIT ' if row['hit'] else 'MISS'} "
              f"matched={row['matched_doc_id'] or '-'}")
    # The receipt travels with every result -- a custom benchmark is a first-class cell.
    print("config hash:", result.receipt["config_hash"])


if __name__ == "__main__":
    main()

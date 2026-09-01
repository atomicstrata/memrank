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
"""Wire YOUR OWN memory engine into the eval loop -- six methods, no registration.

Run from the repo root:

    python examples/custom-engine.py

`memrank.run` takes any `MemoryAdapter` INSTANCE, so an engine that exists only in
your codebase runs the same loop and returns the same `EvalResult` as the shipped
targets. The instance door is library-only: no catalog ref, so no `memrank submit`,
no cloud, and no `workers>1`. For full CLI citizenship, register the same class -- see
examples/custom-target/ -- or serve the HTTP translator contract if your engine is not
Python: examples/native-adapter/.
"""

import time

from memrank import Document, MemoryAdapter, run
from memrank.instrumentation import LatencyCollector, TokenCollector


class ToyEngine(MemoryAdapter):
    """An in-memory engine ranking by word overlap -- deterministic and offline.

    The whole third-party contract is the six methods below. The collectors are the
    documented one-liner way to satisfy the two metric getters; hand-rolling the key
    sets works too, but drifts.
    """

    name = "toy-engine"
    version = "0.1"
    engine_version = "0.1"

    def __init__(self) -> None:
        self._store: list[Document] = []
        self._latency = LatencyCollector()
        self._tokens = TokenCollector()

    def prepare(self, isolation_unit: str) -> None:
        # Called once per benchmark unit with a UNIQUE id. Your duty: a fresh,
        # isolated memory bank -- leaked state inflates every score after the first
        # (it is the most consequential check `memrank targets verify` runs).
        self._store = []

    def ingest(self, documents: list[Document]) -> None:
        started = time.perf_counter()
        self._store.extend(documents)
        self._latency.record("ingest", (time.perf_counter() - started) * 1000.0)

    def retrieve(self, query: str, k: int, user_id: str, query_timestamp=None):
        # Contract: return (ranked documents, raw provider payload). ORDER is the
        # measurement -- scoring walks the list and takes the first hit. Conventions
        # the drill-in reads: metadata["doc_id"] ties a memory back to its source
        # document (evidence gating); metadata["score"] is your relevance figure --
        # report what the engine computed, never invent one. Return at MOST k, never
        # pad. Failures should raise; an empty list must mean "searched, found none".
        started = time.perf_counter()
        words = set(query.lower().split())
        ranked = sorted(
            self._store,
            key=lambda d: len(words & set(d.content.lower().split())),
            reverse=True,
        )[:k]
        hits = [
            Document(id=d.id, content=d.content, user_id=d.user_id,
                     metadata={"doc_id": (d.metadata or {}).get("doc_id", d.id),
                               "score": len(words & set(d.content.lower().split()))})
            for d in ranked
        ]
        self._latency.record("retrieve", (time.perf_counter() - started) * 1000.0)
        return hits, {"engine": self.name, "considered": len(self._store)}

    def cleanup(self) -> None:
        # Idempotent, and safe to call before any prepare().
        self._store = []

    def latency_metrics(self):
        return self._latency.as_metrics()

    def token_metrics(self):
        # None for an unsampled bucket means "not reported", never zero -- this toy
        # engine spends no LLM tokens, and saying 0 would claim it measured that.
        return self._tokens.as_metrics()


def main() -> None:
    result = run(ToyEngine(), "demo", repeats=1)

    print(f"composite: {result.composite:.3f}  ({result.adapter} × {result.benchmark})")
    for row in result.per_query:
        print(f"  {row['query_id']}: {'HIT ' if row['hit'] else 'MISS'} "
              f"matched={row['matched_doc_id'] or '-'}")
    print("retrieve p50:", result.latency_metrics["retrieve_p50_ms"], "ms")
    print("config hash:", result.receipt["config_hash"])


if __name__ == "__main__":
    main()

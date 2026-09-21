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
"""The evaluations memrank ships, as functions -- `from memrank.evaluations import demo`.

`memrank.evaluation("demo")` needs the string first, and a string is not navigable: nothing in
an editor follows it, nothing states what a tier or a slice may be, and nothing tells a reader
what else is out there. Each function here takes the keywords its benchmark takes, typed, and
returns the same `memrank.Evaluation` the string form returns -- they call
`memrank.evaluation(...)` underneath, so there is one conversion and not two.

============  ======================================================================
name          what it needs
============  ======================================================================
demo()        nothing -- a bundled synthetic scenario
relation_gr.  nothing -- in-repo fixtures
locomo()      a one-time download, or LOCOMO_DATA_PATH; judging for any quality number
longmemeval() a one-time download, or LONGMEMEVAL_DATA_PATH; judging likewise
beam()        a one-time download, or BEAM_DATA_PATH; judging likewise
============  ======================================================================

Each benchmark class is imported INSIDE its function. `import memrank` reaches this module, and
a dataset loader's module graph is not something a caller who asked for `demo()` should pay
for. `memrank.catalog()` prints this table at runtime.
"""

from __future__ import annotations

from memrank.instrument.catalog import ShippedEvaluation, evaluation
from memrank.instrument.evaluation import Evaluation


def demo(slice: str | None = None, k: int = 10,
         data_path: str | None = None) -> Evaluation:
    """One hand-crafted multi-session scenario: 5 questions about what it was told earlier.

    Needs nothing -- the scenario is bundled, synthetic and offline, so this is the evaluation
    a first number is taken on. Measures a substring retrieval proxy (`word-match`) plus the
    benchmark's own evidence recall, latency and failure rate; no judge, no key.

    `data_path` (or DEMO_DATA_PATH) points the loader at a scenario of your own, which is then
    no longer synthetic and no longer egress-safe.
    """
    from memrank.benchmarks.demo import DemoBenchmark

    return evaluation(DemoBenchmark(slice=slice, k=k, data_path=data_path))


def relation_graph(slice: str | None = None, k: int = 10) -> Evaluation:
    """Four synthetic fixtures asking whether a memory built the right relations between facts.

    Needs nothing -- the fixtures are in the repository -- but the system must be graph-capable:
    it has to supply the normalized graph snapshot the fixtures are scored against. Measures the
    benchmark's own structural graph score, which is self-contained and needs no judge, plus
    latency and failure rate.
    """
    from memrank.benchmarks.relation_graph import RelationGraphBenchmark

    return evaluation(RelationGraphBenchmark(slice=slice, k=k))


def locomo(slice: str | None = None, k: int = 10) -> Evaluation:
    """Ten multi-session conversations, ~199 QA pairs each, about what was said across sessions.

    Needs a one-time download (or LOCOMO_DATA_PATH pointing at the dataset), and a judge for any
    quality number at all: LoCoMo's published protocol grades the generated answer, and its
    derived answers ("3 times", "2022") can never appear verbatim in retrieved context, so no
    substring proxy is computed. Unjudged, this measures latency and failure rate and nothing
    else. `slice` is "smoke", "mini" or None for the full set.
    """
    from memrank.benchmarks.locomo import LoCoMoBenchmark

    return evaluation(LoCoMoBenchmark(slice=slice, k=k))


def longmemeval(slice: str | None = None, k: int = 10) -> Evaluation:
    """~500 questions across six question types, each with its own haystack of sessions.

    Needs a one-time download (or LONGMEMEVAL_DATA_PATH), and a judge for any quality number:
    the published metric is judged QA accuracy and the paper rejects exact matching, so no
    substring proxy is computed. Unjudged, this measures latency and failure rate. `slice` is
    "smoke", "mini" or None for the full set.
    """
    from memrank.benchmarks.longmemeval import LongMemEvalBenchmark

    return evaluation(LongMemEvalBenchmark(slice=slice, k=k))


def beam(tier: str = "100k", slice: str | None = None, k: int = 10) -> Evaluation:
    """20 conversations / 400 questions at 100k, 35 / 700 at 500k and 1m; 2 questions per ability.

    Needs a one-time download from HuggingFace (or BEAM_DATA_PATH), and a judge for any quality
    number: BEAM's gold answers are prose rubrics rather than verbatim spans, so no substring
    proxy is computed and the raw composite is withheld from ranking until judged. Unjudged,
    this measures latency and failure rate. `tier` is "100k", "500k" or "1m", and an unknown one
    is refused here, before anything is fetched.
    """
    from memrank.benchmarks.beam import BEAMBenchmark

    return evaluation(BEAMBenchmark(tier=tier, slice=slice, k=k))


#: The same table the module docstring carries, in the form `memrank.catalog()` prints. One
#: entry per name in `memrank.benchmarks.REGISTRY`, which `tests/instrument` holds it to.
SHIPPED: tuple[ShippedEvaluation, ...] = (
    ShippedEvaluation("demo", "demo", "a substring retrieval proxy and evidence recall",
                      "nothing -- a bundled synthetic scenario"),
    ShippedEvaluation("relation_graph", "relation_graph", "a structural graph score",
                      "nothing -- in-repo fixtures, and a graph-capable system"),
    ShippedEvaluation("locomo", "locomo", "latency and failures; quality needs a judge",
                      "a one-time download, or LOCOMO_DATA_PATH"),
    ShippedEvaluation("longmemeval", "longmemeval", "latency and failures; quality needs a judge",
                      "a one-time download, or LONGMEMEVAL_DATA_PATH"),
    ShippedEvaluation("beam", "beam", "latency and failures; quality needs a judge",
                      "a one-time download, or BEAM_DATA_PATH"),
)

__all__ = ["SHIPPED", "beam", "demo", "locomo", "longmemeval", "relation_graph"]

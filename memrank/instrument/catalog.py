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
"""`memrank.evaluation("demo")` and `memrank.system("word-overlap")` -- the shipped names.

Two constructors, one idea: the things memrank ships are reached by the catalog name they are
printed under, so the first line a person copies stays inside the seven words. `system` hands
back a constructed shipped system; `evaluation` converts an in-tree benchmark into an
`Evaluation`.

memrank's own evaluations and a person's are the same kind of thing, so this produces exactly
what a person writes by hand: tasks, measures, a clearing rule. One group per unit, the unit's
documents as the group's context, and the benchmark's own `score()` wrapped as one measure
beside the measures that need no answer writer.

What does not convert is carried honestly rather than approximated: a benchmark whose span
proxy is meaningless (`substring_recall_supported = False`) ships no `WordMatch`, and nothing
here judges, because judging needs an answer and an answer needs a writer and a key.
"""

from __future__ import annotations

from collections.abc import Sequence
from typing import Any

from memrank.core import Benchmark, BenchmarkUnit
from memrank.instrument.evaluation import UNFREEZABLE, Clearing, Evaluation
from memrank.instrument.measure import Measure
from memrank.instrument.measures import BenchmarkScore, FailureRate, Latency, WordMatch
from memrank.instrument.system import System
from memrank.instrument.task import Expected, Task

#: Query keys the five registered loaders fill that are NOT part of `Task`'s own fields, and
#: that something downstream reads. Anything else a loader puts in a query dict is dropped.
CARRIED_METADATA = ("judge_prompt_key", "retrieval_scoreable", "ordering_tested",
                    "query_timestamp", "gold_ids", "expected_retrieval")


def _expected(query: dict[str, Any]) -> Expected:
    """What a correct outcome looks like, from the query dict the loader produced."""
    return Expected(
        answers=tuple(query.get("gold_answers") or ()),
        required_spans=tuple(query.get("required_spans") or ()),
        forbidden_spans=tuple(query.get("forbidden_spans") or ()),
        evidence_doc_ids=tuple(query.get("evidence_doc_ids") or ()),
        rubric=tuple(query.get("rubric") or ()),
        polarity="negative" if query.get("kind") == "negative" else "positive")


def task_from_query(query: dict[str, Any], unit: BenchmarkUnit) -> Task:
    """One query of one unit, as a task. The unit is the group, so the unit is the state."""
    return Task(
        id=str(query["id"]),
        prompt=str(query.get("text") or ""),
        expected=_expected(query),
        group=unit.isolation_id,
        context=tuple(unit.documents),
        category=query.get("category"),
        metadata={key: query[key] for key in CARRIED_METADATA if key in query})


def _version(benchmark: Benchmark) -> str:
    """The version of what this evaluation asks. A gap and a statement stay different values."""
    from memrank.quality import UNFREEZABLE as BENCHMARK_UNFREEZABLE

    declared = benchmark.dataset_version
    if declared == BENCHMARK_UNFREEZABLE:
        return UNFREEZABLE
    return f"{declared}+def{benchmark.VERSION}"


def _measures(benchmark: Benchmark, units: Sequence[BenchmarkUnit]) -> tuple[Measure, ...]:
    """The benchmark's own score, plus every measure that needs no answer writer."""
    shipped: list[Measure] = [BenchmarkScore(benchmark, units)]
    if benchmark.substring_recall_supported:
        shipped.append(WordMatch())
    shipped.extend((Latency(), FailureRate()))
    return tuple(shipped)


def from_benchmark(benchmark: Benchmark, units: Sequence[BenchmarkUnit] | None = None,
                   *, name: str | None = None) -> Evaluation:
    """Convert an in-tree benchmark into an evaluation. `units` defaults to `benchmark.load()`.

    Passing `units` is how a caller converts without loading -- the loaders that download do
    it in `load()`, and a conversion is not a reason to fetch a dataset.
    """
    loaded = list(units if units is not None else benchmark.load())
    tasks = tuple(task_from_query(query, unit) for unit in loaded for query in unit.queries)
    return Evaluation(
        name=name or benchmark.name,
        version=_version(benchmark),
        tasks=tasks,
        measures=_measures(benchmark, loaded),
        clearing=Clearing.PER_GROUP,
        metadata={"benchmark": benchmark.name,
                  "quality_metric": benchmark.quality_metric,
                  "task_version": benchmark.VERSION,
                  "units": len(loaded)})


def evaluation(ref: str | Benchmark, **overrides: Any) -> Evaluation:
    """The evaluation an in-tree ref names -- `memrank.evaluation("demo")`.

    ``ref`` takes the same grammar as the rest of memrank (`"beam:100k-smoke"`), or a
    `Benchmark` already built. Loading happens here, which is where a dataset may be fetched.
    """
    if isinstance(ref, Benchmark):
        return from_benchmark(ref)
    from memrank.benchmarks import from_ref

    return from_benchmark(from_ref(ref, **overrides))


def system(name: str, **options: Any) -> System:
    """The shipped system that catalog name names -- `memrank.system("word-overlap")`.

    The names are the ones `memrank list-adapters` prints, and `options` goes straight to the
    constructor, which is how a client for a running service is given its `base_url=` and its
    `api_key=`. An unknown name is refused with the known ones named, because the alternative
    is a reader guessing at a spelling memrank could simply have told them.
    """
    from memrank.adapters import REGISTRY

    if name not in REGISTRY:
        known = ", ".join(sorted(REGISTRY))
        raise ValueError(f"Unknown system: {name!r}. memrank ships: {known}")
    return REGISTRY[name](**options)

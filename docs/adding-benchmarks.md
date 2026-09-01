# Adding a benchmark

A benchmark wraps a dataset (loader) and its scoring methodology (scorer).
Memrank treats benchmarks as opaque pairs: the runner does not know how
LoCoMo differs from BEAM -- it only knows how to call `load()` then `score()`.

## 1. Subclass `Benchmark`

```python
from memrank.core import AdapterResponse, Benchmark, BenchmarkUnit, Document, EvalInfo


class MyBenchmark(Benchmark):
    name = "mybench"
    dataset_version = "myorg/mybench@v1"   # the data
    VERSION = 0                            # the load/score definition; bump on any break

    # Required, with no default: `memrank evals show` reads it, and a benchmark
    # without one fails the first time the catalog is asked. DECLARED, never loaded --
    # rendering it must not construct units or touch the dataset cache.
    info = EvalInfo(unit="conversation",
                    units_declared="10 conversations (dataset's own description)",
                    slices=("smoke", "mini"))

    def load(self) -> list[BenchmarkUnit]: ...
    def score(self, unit, responses) -> dict: ...
    def report_template(self) -> str: ...
```

### Declare what your score is

The runner does not infer these, and getting one wrong is how a number comes to mean something
other than it appears to. Each is a class attribute with a default that suits a benchmark whose
gold answers are verbatim spans:

| | Default | Set it when |
|---|---|---|
| `substring_recall_supported` | `True` | your gold answers are prose, not verbatim spans -- substring recall is then structurally ~0 and must be withheld in favour of a judge |
| `composite_rankable` | `True` | your raw `composite` is not a score to rank as-is without a judge |
| `quality_metric` | `"substring_recall"` | your composite is something else (`"graph_score"`, ...); it names the displayed column |
| `context_policy` | `"matched"` | your benchmark's own protocol hands the reader everything retrieval returned -- `"uncapped"` |
| `is_synthetic` | `False` | the data is synthetic and safe to send to a judge without egress consent |
| `requires_graph` | `False` | scoring needs an adapter's graph snapshot; cells with a non-graph adapter are then skipped as `not_applicable` |

`substring_recall_supported` and `composite_rankable` are decoupled on purpose: a graph benchmark
sets the first `False` (substring recall is not applicable) and the second `True` (its composite
*is* a real score).

## 2. Implement `load()`

Return a list of `BenchmarkUnit`. Each unit is a self-contained scoring
context: documents to ingest, queries to ask, and an `isolation_id` so
adapters can scope their state.

For datasets with a per-conversation isolation primitive (LoCoMo, BEAM),
emit one unit per conversation. For per-question isolation
(LongMemEval), emit one unit per question.

## 3. Implement `score()`

Take a single unit plus the adapter's responses for that unit and return a
dict with at least:

```python
{
    "composite": 0.0,        # float in [0, 1]
    "per_category": {...},   # category breakdown, when applicable
    "metric": "...",         # human-readable metric name
}
```

If your benchmark's answers are graded differently from "one answer, one verdict,
one boolean", override `judge_shape()` and return a `JudgeShape`
(`memrank/judging/shape.py`). A shape declares two things: what grading one query
**costs**, split into the cache-shared control half and the per-engine context half,
and what grading one **yields** -- a `JudgedQuery` whose `score` is a float in [0, 1].

Most benchmarks need none of this. The default `BinaryJudgeShape` is right for any
benchmark whose questions have a single gold answer. BEAM is the exception: it scores
against a rubric of atomic nuggets, one judge call each, averaged within the question.

Do **not** reach for a `judge` callable in the constructor -- an earlier version of this
document told you to, and nothing ever implemented it.

## 4. Use auto-download

Drop the dataset into the cache root that ``memrank.benchmarks.cache_root()``
returns, or fetch from HuggingFace lazily on first call. Honor a
`<NAME>_DATA_PATH` env var so users can point at a local copy.

## 5. Register the benchmark

Add the class to `memrank/benchmarks/__init__.py`'s `REGISTRY`. It then appears in
`memrank evals ls`, and `memrank evals show <name>` renders the `EvalInfo` you declared.

## 6. Write your own tests

Tests for a benchmark go in `tests/benchmarks/`, beside the families already
there. A file belongs there iff its subject is a `Benchmark` implementation:
loading, scoring, or a methodology claim. Split by concern rather than by file
size -- `test_<name>_loading.py`, `test_<name>_scoring.py`,
`test_<name>_methodology.py` is the shape the existing benchmarks use, and the
methodology file is the one a reviewer reads first.

A test that runs your benchmark end to end through the runner is about the run
rather than about the benchmark, and goes in `tests/orchestration/`.
[`tests/README.md`](../tests/README.md) states the rule for every directory.

## 7. Document the methodology

Per the vendor-neutral charter ([SPEC.md section 7.3](SPEC.md)), a methodology change goes through
public proposal and comment before it merges, and does not merge without matching documentation.

A new benchmark needs a section in [`methodology.md`](methodology.md): what it scores, how it is
built, what its labels mean, and -- the part readers rely on -- what its numbers do *not* license
anyone to say. Add the axis there too if it introduces one.

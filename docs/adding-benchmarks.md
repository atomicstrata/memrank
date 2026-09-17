# Adding a benchmark

A benchmark is two pieces of yours: a **loader** that produces the data, and a **scorer** that says
what a good answer is. Memrank supplies everything around them -- running an engine over your units,
isolating one unit from the next, timing it, accounting for cost, judging where you ask for one, and
the receipt that records what actually ran.

You do not have to put your benchmark inside this package to run it, and you do not have to give it
a name. Pass the instance.

## 1. Run your own benchmark: pass the instance

`memrank.run` takes a `Benchmark` instance wherever it takes an eval ref, so an eval that exists
only in your own file runs the same loop, and returns the same `EvalResult`, as the shipped ones:

```python
import memrank
from memrank import Benchmark, BenchmarkUnit


class TicketsBenchmark(Benchmark):
    name = "tickets"
    dataset_version = "internal@2026-08"

    def load(self) -> list[BenchmarkUnit]: ...
    def score(self, unit, responses) -> dict: ...
    def report_template(self) -> str: ...


result = memrank.run("word-overlap", TicketsBenchmark(), repeats=1)
print(result.composite, result.benchmark)
```

Those three methods are the whole third-party contract. Nothing here touches the registry, the
command line, a configuration setting or a file inside `memrank/` -- and the first argument is a
target the same way: a catalog ref, or an engine instance of your own (see
[adding an adapter](adding-adapters.md)).

The runnable version of exactly this, offline and in about a second, is
[`examples/custom-benchmark.py`](../examples/custom-benchmark.py):

```bash
python examples/custom-benchmark.py
```

**What the instance route does not reach.** A benchmark passed as an object has no catalog ref, so
`memrank submit`, cloud placement and `memrank evals ls` do not know it exists. Reaching those means
giving it a name, which is [section 5](#5-share-it-registration-the-cli-and-runs-by-name).

## 2. Implement `load()`

Return a list of `BenchmarkUnit`. Each unit is a self-contained scoring context: documents to
ingest, queries to ask, and an `isolation_id` so adapters can scope their state. Units never see
each other.

For datasets with a per-conversation isolation primitive (LoCoMo, BEAM), emit one unit per
conversation. For per-question isolation (LongMemEval), emit one unit per question.

A query dictionary needs only `id` and `text`. The span-scoring fields (`required_spans`,
`forbidden_spans`, `evidence_doc_ids`, `kind`) are what `score()` reads; a judged run additionally
wants `gold_answers` and a `category` your judge shape recognizes.

## 3. Implement `score()`

Take a single unit plus the adapter's responses for that unit and return a dict with at least:

```python
{
    "composite": 0.0,        # float in [0, 1]
    "per_category": {...},   # category breakdown, when applicable
    "metric": "...",         # human-readable metric name
}
```

`memrank.metrics.scoring`'s `score_query` and `spec_from_query` are the same span helpers the
shipped benchmarks use; reuse them unless your gold is not span-shaped.

If your benchmark's answers are graded differently from "one answer, one verdict, one boolean",
override `judge_shape()` and return a `JudgeShape` (`memrank/judging/shape.py`). A shape declares
two things: what grading one query **costs**, split into the cache-shared control half and the
per-engine context half, and what grading one **yields** -- a `JudgedQuery` whose `score` is a float
in [0, 1].

Most benchmarks need none of this. The default `BinaryJudgeShape` is right for any benchmark whose
questions have a single gold answer. BEAM is the exception: it scores against a rubric of atomic
nuggets, one judge call each, averaged within the question.

Do **not** reach for a `judge` callable in the constructor -- an earlier version of this document
told you to, and nothing ever implemented it.

### Declare what your score is

The runner does not infer these, and getting one wrong is how a number comes to mean something
other than it appears to. They apply to an instance exactly as they do to a registered benchmark.
Each is a class attribute with a default that suits a benchmark whose gold answers are verbatim
spans:

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

`composite_rankable` is also what `memrank.run(judge=None)` asks: a benchmark whose composite is not
rankable gets a judge by default, because an unjudged run of it measures latency and cost and
nothing else.

## 4. Where the data comes from

`load()` may read whatever you like -- a file beside your script, a database, an API. For a dataset
you want cached rather than carried, drop it into the cache root that
``memrank.benchmarks.cache_root()`` returns, or fetch it from HuggingFace lazily on first call, and
honor a `<NAME>_DATA_PATH` env var so a reader can point at a local copy.

## 5. Share it: registration, the CLI, and runs by name

Everything above runs from Python and stays in your own repository. Do the rest of this section when
the benchmark should be runnable **by name** -- from the command line, in the cloud, in a sweep, or
by other people.

### Register the benchmark

Add the class to `memrank/benchmarks/__init__.py`'s `REGISTRY`. It then has a ref: `memrank evals ls`
lists it, `memrank submit <target> <name>` runs it, and the cloud can resolve it.

Registration decides where the code lives and what may address it. It changes nothing about how the
benchmark is loaded or scored.

### Declare `EvalInfo` for the catalog

A registered benchmark needs `info`, because `memrank evals show <name>` renders it and a registered
benchmark without one fails the first time the catalog is asked. It is required only on this route:
an instance runs without it.

```python
from memrank.core import EvalInfo


class MyBenchmark(Benchmark):
    # DECLARED, never loaded -- rendering it must not construct units or touch
    # the dataset cache.
    info = EvalInfo(unit="conversation",
                    units_declared="10 conversations (dataset's own description)",
                    slices=("smoke", "mini"))
```

### Write tests beside the others

Tests for an in-tree benchmark go in `tests/benchmarks/`, beside the families already there. A file
belongs there iff its subject is a `Benchmark` implementation: loading, scoring, or a methodology
claim. Split by concern rather than by file size -- `test_<name>_loading.py`,
`test_<name>_scoring.py`, `test_<name>_methodology.py` is the shape the existing benchmarks use, and
the methodology file is the one a reviewer reads first.

A test that runs your benchmark end to end through the runner is about the run rather than about the
benchmark, and goes in `tests/orchestration/`. [`tests/README.md`](../tests/README.md) states the
rule for every directory.

### Document the methodology

Per the vendor-neutral charter ([SPEC.md section 7.3](SPEC.md)), a methodology change goes through
public proposal and comment before it merges, and does not merge without matching documentation.

A shared benchmark needs a section in [`methodology.md`](methodology.md): what it scores, how it is
built, what its labels mean, and -- the part readers rely on -- what its numbers do *not* license
anyone to say. Add the axis there too if it introduces one.

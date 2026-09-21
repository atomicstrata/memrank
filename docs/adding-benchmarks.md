# Adding an evaluation

An **evaluation** is a named, versioned bundle: its tasks, the measures it ships with, and the
rule for when the system's state is cleared. No scoring lives in it -- scoring lives in
**measures**, which an evaluation only bundles. That separation is the point: bringing your own
questions does not mean writing your own measure, and bringing your own measure does not mean
writing questions.

memrank's own evaluations and yours are the same kind of object. You do not have to put yours
inside this package to run it, and you do not have to give it a name.

**One note on names.** A *named* evaluation -- one the command line and the cloud can resolve
by string -- is still built from the `Benchmark` class in this tree, and the command line still
calls it an *eval*. `memrank.evaluation("demo")` is what converts one into the `Evaluation` the
seven words use. Renaming that class is a later change; both halves of this document are live
today.

## 1. Write the evaluation directly

Tasks are plain data, and a measure memrank ships does the deciding:

```python
import memrank
from memrank import Clearing, Document, Evaluation, Expected, Task
from memrank.adapters import WordOverlapAdapter

notes = (Document(id="t1", user_id="acme",
                  content="Acme moved to the enterprise plan in March."),)

tickets = Evaluation(
    name="tickets", version="internal@2026-09",
    tasks=(Task(id="q_plan", prompt="What plan is Acme on?", group="acme", context=notes,
                expected=Expected(answers=("enterprise",), required_spans=("enterprise",),
                                  evidence_doc_ids=("t1",))),),
    measures=(memrank.WordMatch(),),
    clearing=Clearing.PER_GROUP)

result = memrank.run(WordOverlapAdapter(), tickets)
print(result.values_of("word-match")[0].value)
```

A **task** carries the context to give the system first, the prompt, and what a correct outcome
looks like -- and no rule about correctness. `Expected` is where that description lives:
`answers`, `required_spans`, `forbidden_spans`, `evidence_doc_ids`, `rubric`, and `polarity`,
which is `"negative"` for a task whose correct outcome is that the wrong memory is *not*
surfaced.

Tasks that share state carry the same `group`. A run gives a group's documents once, in
first-seen order and deduplicated by id, and clears between groups -- never inside one.
`Clearing.PER_TASK` and `Clearing.AT_END` are the other two rules, and the result records
which one was in force and whether the system could be observed to have cleared.

`version` is the version of what this evaluation asks. Where its material cannot be frozen,
say so rather than inventing a version:
`memrank.instrument.evaluation.UNFREEZABLE` is that statement, and it is recorded in every
result. A gap and an honest statement are different values.

Two results can be laid side by side only when they share the evaluation *and* its version, so
changing the tasks under a name that stays the same is what makes a comparison quietly wrong.

The runnable version is
[`examples/03-your-own-evaluation/`](../examples/03-your-own-evaluation/README.md):

```bash
uv run python examples/03-your-own-evaluation/run.py
```

## 1a. Write the measure instead

A measure is a named rule from traces to values. It declares its scope (one task, or the whole
run), which trace fields and value names it reads, and who decides. Because measuring is not
inside the run loop, one you think of afterwards runs over traces already stored --
`memrank.measure(result, MyMeasure())`, with the system never touched again. A measure that
reads a name nothing in the run produces is refused before the run.

[`examples/04-your-own-measure/`](../examples/04-your-own-measure/README.md) is a worked one,
applied to a result loaded back off disk.

## 2. Or write a named benchmark: `load()` and `score()`

A named evaluation the command line and the cloud can resolve is still a `Benchmark`: a
**loader** that produces the data, and a **scorer** that says what a good answer is. Memrank
supplies everything around them -- running a system over your units, isolating one unit from
the next, timing it, accounting for cost, judging where you ask for one, and the receipt that
records what actually ran. `memrank.evaluation(MyBenchmark())` converts one into an
`Evaluation`: each unit becomes a group, its documents the group's context, its queries the
tasks, and its own `score()` one measure beside the ones that need no answer writer.

```python
import memrank
from memrank import Benchmark, BenchmarkUnit
from memrank.adapters import WordOverlapAdapter


class TicketsBenchmark(Benchmark):
    name = "tickets"
    dataset_version = "internal@2026-08"

    def load(self) -> list[BenchmarkUnit]: ...
    def score(self, unit, responses) -> dict: ...
    def report_template(self) -> str: ...


result = memrank.run(WordOverlapAdapter(), memrank.evaluation(TicketsBenchmark()))
print(result.values_of("tickets-score")[0].value, result.evaluation.name)
```

Those three methods are the whole third-party contract. Nothing here touches the registry, the
command line, a configuration setting or a file inside `memrank/`.

## 2a. Bring one half: `ComposedEvaluation`

The two pieces do not have to come from the same person. `ComposedEvaluation` builds a
benchmark from a question half and a scoring half supplied independently, so bringing one
does not mean writing the other:

```python
from memrank import ComposedEvaluation, Scorer
from memrank.benchmarks.demo import DemoBenchmark

# My questions, memrank's scorer. No scoring is written.
mine = ComposedEvaluation(name="tickets", questions=[unit, ...])

# memrank's questions, my scorer. No loader is written.
class MyScorer(Scorer):
    criterion_names = ("composite",)
    identity = "my-own-rules/v1"

    def score(self, unit, responses) -> dict:
        ...

theirs = ComposedEvaluation(name="demo+mine", questions=DemoBenchmark(), scorer=MyScorer())

# Both mine.
both = ComposedEvaluation(name="tickets", questions=[unit, ...], scorer=MyScorer())
```

`questions` takes a `Benchmark`, a list of `BenchmarkUnit`s, or a callable returning them. When
it is a `Benchmark`, its own declarations come with it -- dataset version, egress safety, graph
requirement, reader-context policy, run-level rollup and judge shape -- so swapping the scorer
changes what is measured and nothing else. The scorer decides the *kind* of number
(`quality_metric`) and is named in the receipt, because two scorers are not one reproducible run.

**Both halves declare, and a disagreement is refused before any task runs.** A scorer names the
scored keys it produces (`criterion_names`); a question source names the ones its own aggregation
expects. Where both speak and they disagree, composition raises `CriteriaMismatch` naming both
lists, rather than failing late on a `KeyError` or reducing over whichever criterion happened to
be there. The same check runs on the judge side: a scorer whose `judge_shape()` defines per-type
grading prompts is compared against the prompt keys the questions carry, because grading a query
under a prompt written for a different question type is how 12% of a benchmark was graded against
the wrong object for months (`memrank/judging/shape.py`, `BinaryJudgeShape._prompt_for`).

Declaring nothing is the default and is not a disagreement: all five registered benchmarks
declare no criteria, which is what keeps somebody else's scorer acceptable over their questions.

**What the instance route does not reach.** A benchmark passed as an object has no catalog ref, so
`memrank submit`, cloud placement and `memrank evals ls` do not know it exists. Reaching those means
giving it a name, which is [section 6](#6-share-it-registration-the-cli-and-runs-by-name).

## 3. Implement `load()`

Return a list of `BenchmarkUnit`. Each unit is a self-contained scoring context: documents to
ingest, queries to ask, and an `isolation_id` so a system can scope its state. Units never see
each other, and a unit becomes a task **group** when the benchmark is converted.

For datasets with a per-conversation isolation primitive (LoCoMo, BEAM), emit one unit per
conversation. For per-question isolation (LongMemEval), emit one unit per question.

A query dictionary needs only `id` and `text`. The span-scoring fields (`required_spans`,
`forbidden_spans`, `evidence_doc_ids`, `kind`) are what `score()` reads; a judged run additionally
wants `gold_answers` and a `category` your judge shape recognizes. Those are the same fields
`Expected` carries on a task, which is what the conversion in section 2 maps them onto.

## 4. Implement `score()`

Take a single unit plus the system's responses for that unit and return a dict with at least:

```python
{
    "composite": 0.0,        # float in [0, 1]
    "per_category": {...},   # category breakdown, when applicable
    "metric": "...",         # human-readable metric name
}
```

If your gold is span-shaped, you do not have to write `score()` at all: `memrank.SpanRecall` is
the scorer the shipped demo benchmark uses, and it returns exactly the dict above.

```python
from memrank import SpanRecall

class MyBenchmark(Benchmark):
    scorer = SpanRecall()

    def score(self, unit, responses):
        return self.scorer.score(unit, responses)
```

It marks whether a query's gold spans appear verbatim in a retrieved document -- a retrieval
proxy, never answer correctness, which is what its `METRIC_LABEL` says in every unit it scores.
`memrank.WordMatch` is the same arithmetic as a measure, per task rather than per unit, and it
carries the same caveat on every value.
`memrank.metrics`'s `score_query` and `spec_from_query` are the per-query pieces it is built
from, for a scorer that needs the verdict rather than the unit mean.

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

`composite_rankable` is also what the previous run's `judge=None` asks: a benchmark whose composite
is not rankable gets a judge by default, because an unjudged run of it measures latency and cost
and nothing else. `substring_recall_supported` also decides the conversion: a benchmark whose span
proxy is meaningless ships no `WordMatch` measure rather than a number that means nothing.

## 5. Where the data comes from

`load()` may read whatever you like -- a file beside your script, a database, an API. For a dataset
you want cached rather than carried, drop it into the cache root that
``memrank.benchmarks.cache_root()`` returns, or fetch it from HuggingFace lazily on first call, and
honor a `<NAME>_DATA_PATH` env var so a reader can point at a local copy.

## 6. Share it: registration, the CLI, and runs by name

Everything above runs from Python and stays in your own repository. Do the rest of this section when
the evaluation should be runnable **by name** -- from the command line, in the cloud, in a sweep, or
by other people. This is where the command line's own vocabulary starts: *eval* is its word for a
named evaluation, and `Benchmark` is the class it resolves one to.

### Register the benchmark

Add the class to `memrank/benchmarks/__init__.py`'s `REGISTRY`. It then has a ref: `memrank evals ls`
lists it, `memrank submit <target> <name>` runs it, and the cloud can resolve it.

Registration decides where the code lives and what may address it. It changes nothing about how the
evaluation is loaded or scored.

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

A test that runs your evaluation end to end through the runner is about the run rather than about
the evaluation, and goes in `tests/orchestration/`. [`tests/README.md`](../tests/README.md) states the
rule for every directory.

### Document the methodology

Per the vendor-neutral charter ([SPEC.md section 7.3](SPEC.md)), a methodology change goes through
public proposal and comment before it merges, and does not merge without matching documentation.

A shared evaluation needs a section in [`methodology.md`](methodology.md): what it scores, how it is
built, what its labels mean, and -- the part readers rely on -- what its numbers do *not* license
anyone to say. Add the axis there too if it introduces one.

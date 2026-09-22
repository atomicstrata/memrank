# result

## An instance, first

A **result** is what a [run](run.md) hands back: the records of what happened, and the numbers
read off them. Print one and it lays itself out -- which system, which evaluation, every value
with the measure that produced it and who decided it, and how many traces were recorded:

```python
import memrank
from memrank.evaluations import demo
from memrank.systems import WordOverlap

result = memrank.run(WordOverlap(), demo())

print(result.system.name, "|", result.system.kind, "|", result.evaluation.name)
for value in result.values_of("word-match"):
    print(f"{value.task_id:<14} {value.value}  decided by {value.decider.value}")
print(len(result.traces), "traces,", sum(1 for t in result.traces if t.error), "with errors")
```

```console
WordOverlap | memory | demo
q_job          1.0  decided by rule
q_animal       1.0  decided by rule
q_visit        1.0  decided by rule
q_diet         0.0  decided by rule
q_allergy_neg  1.0  decided by rule
5 traces, 0 with errors
```

## What it is

A result holds two things and refuses to collapse them:

- **`traces`** -- one [trace](trace.md) per task per attempt: what was given, what came back,
  what each step timed, and the error with the step it broke at when it broke.
- **`values`** -- what the [measures](measure.md) produced. **Every value carries the measure's
  name and its decider**, and most carry a `why`. There is no bare number anywhere in a result,
  and no overall score across measures: memrank invents none.

It is a record, not a verdict. Nothing in a result says which system is better -- that depends
on what you are buying, and the numbers do not know what that is.

Three rules it enforces that are easy to lose elsewhere:

- **Absent is not zero.** A system that declared no token usage records `None`. A measure that
  could not decide records `None` with the reason. Conflating the two fabricates a win for every
  system that stayed quiet.
- **A failed task is a row, not a gap.** Its trace is there, `failure-rate` counts it, and every
  task-scope measure records `None` for it.
- **A refused run has no traces and a reason.** `result.refusal` says why, and nothing was
  touched.

A result is typed and it persists. `result.save(path)` writes it; `memrank.Result.load(path)`
reads it back in another process, days later, with the traces intact -- which is what lets
`memrank.measure` apply a new measure without rerunning anything.

## Who supplies what

| You supply | Memrank supplies |
|---|---|
| nothing -- a result is returned to you | the traces, the values, the provenance on each value |
| where to save it, if you want it kept | the typed round trip through JSON |

## The Python names

```python
import memrank
from memrank import Result
from memrank.evaluations import demo
from memrank.systems import WordOverlap

result = memrank.run(WordOverlap(), demo())
result.save("/tmp/demo-run.json")
reloaded = Result.load("/tmp/demo-run.json")

print(len(reloaded.traces), "traces read back;", reloaded.refusal, "refusal")
print(sorted({value.measure for value in reloaded.values}))
```

```console
5 traces read back; None refusal
['demo-score', 'failure-rate', 'latency.ingest.p50', 'latency.ingest.p95', 'latency.retrieve.p50', 'latency.retrieve.p95', 'word-match']
```

- `memrank.Result` -- fields `schema_version`, `system`, `evaluation`, `refusal`, `traces`,
  `values`, `started`, `finished`.
- `result.values_of("<measure name>")` -- one measure's values, picked out of the rest.
- `result.traces_of("<task id>")` -- the traces of one task. Where you dig when a value is low.
- `result.save(path)` and `Result.load(path)` -- to disk and back, typed.
- `memrank.measure(result, MyMeasure())` -- a new measure over traces already stored.
- `memrank.paired(a, b)` -- [two results side by side](paired.md).

## Going deeper

- [trace](trace.md) and [measure](measure.md) -- the two halves a result holds.
- [Methodology](../methodology.md) -- what a value does and does not license you to say.
- [paired](paired.md) -- comparing two of them.

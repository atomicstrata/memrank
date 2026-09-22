# result

A **result** is what a [run](run.md) returns: the records of what happened, and the values read
off them. This page is about reading one.

```python
from memrank.evaluations import Demo
from memrank.systems import WordOverlap

result = Demo().run(system=WordOverlap())

print(result.system.name, "|", result.system.kind, "|", result.evaluation.name)
for value in result.values_of("word-match"):
    print(f"{value.task_id:<14} {value.value}  decided by {value.decider.value}")
print(len(result.traces), "traces,", sum(1 for t in result.traces if t.error), "with errors")
```

<!-- output: exact -->
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
- **`values`** -- what the [measures](measure.md) produced. Every value carries the measure's
  name and its decider, and most carry a `why`. There is no bare number anywhere in a result,
  and no overall score across measures.

It is a record, not a verdict. Nothing in a result says which system is better -- that depends
on what you are buying, and the values do not know what that is.

Three rules it enforces:

- **Absent is not zero.** A system that declared no token usage records `None`; a measure that
  could not decide records `None` with the reason. Conflating the two fabricates a win for every
  system that stayed quiet.
- **A failed task is a row, not a gap.** Its trace is there, `failure-rate` counts it, and every
  task-scope measure records `None` for it.
- **A refused run has no traces and a reason.** `result.refusal` says why, and nothing was
  touched.

`result.save(path)` writes a result; `memrank.Result.load(path)` reads it back in another
process, days later, with the traces intact. That is what lets `memrank.measure` apply a new
measure without rerunning anything.

## Who supplies what

A result is returned to you. You supply nothing beyond where to save it.

## The Python names

```python
from memrank import Result
from memrank.evaluations import Demo
from memrank.systems import WordOverlap

result = Demo().run(system=WordOverlap())
result.save("/tmp/demo-run.json")
reloaded = Result.load("/tmp/demo-run.json")

print(len(reloaded.traces), "traces read back;", reloaded.refusal, "refusal")
print(sorted({value.measure for value in reloaded.values}))
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
- [paired](paired.md) -- comparing two of them.
- [Methodology](../methodology.md) -- what a value does and does not license you to say.

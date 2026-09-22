# run

A **run** is the act of putting an [evaluation](evaluation.md)'s questions to a
[system](system.md) and recording what happened. It is one line.

```python
from memrank.evaluations import Demo
from memrank.systems import WordOverlap

result = Demo().run(system=WordOverlap())
print(len(result.traces), "traces,", len(result.values), "values")
```

That call gave `WordOverlap` the three documents of the `demo` conversation, put the five
questions to it one at a time, timed every call at memrank's own boundary, recorded one
[trace](trace.md) per question, and applied the [measures](measure.md) `demo` bundles. It needed
no engine, no network and no key.

## What it is

`evaluation.run(system=...)` is the entry point of the package. The evaluation is what you are
holding and the system is what you are putting it to, so the run is a verb on the one and takes
the other. `run(a, b)` gives a reader nothing to tell them which of the two arguments is the
system, which is the question people actually asked.

You compose the run at the call. There is no configuration file between you and it, and nothing
is registered in advance.

What it does, in order:

1. **It refuses, or it does not.** Before touching the system, memrank checks the run can be set
   up at all. It refuses -- with a stated reason and no traces -- when the system is not a kind
   memrank knows, when it lacks a verb its kind requires, when a measure reads a name nothing in
   the run produces, or when the evaluation carries documents to give and the system has no verb
   to be told things with. A run that cannot produce what is asked of it costs you nothing.
2. **It gives, asks and records.** Per group of tasks: clear, give the group's documents once,
   then put each prompt. One trace per task per attempt, including when a task raises -- the run
   never stops on a task's failure.
3. **It measures.** The evaluation's measures read the traces and produce named values.
4. **It returns a [result](result.md).**

## Who supplies what

You supply the evaluation and the system, and optionally `k=`, `attempts=` and `answerer=`.
Memrank supplies the refusal check, the run loop, the isolation, the clock, and one trace per
task per attempt.

## The Python names

```python
import inspect

from memrank.evaluations import Demo

print(inspect.signature(Demo().run))
```

- `evaluation.run(system=...)` -- the system is the only positional argument; the evaluation is
  the receiver. Every other argument is keyword-only.
- `k=` -- how many documents to ask a memory or retriever for. Default 10.
- `attempts=` -- how many times to put each task. Default 1.
- `answerer=` -- a writer that turns what was recalled into an answer, needed when a measure
  reads `answered` and the system only recalls.
- `result.refusal` -- the reason, when the run refused. `None` when it went ahead.

## Going deeper

- [result](result.md) -- what comes back.
- [Methodology](../methodology.md) -- the context-budget control, the arms, and what a run is
  evidence of.
- [`examples/01-first-result/`](../../examples/01-first-result/) -- the shortest working run.

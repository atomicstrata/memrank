# run

## An instance, first

A **run** is the act of putting an evaluation's questions to a system and recording what
happened. One line:

```python
import memrank
from memrank.evaluations import demo
from memrank.systems import WordOverlap

result = memrank.run(WordOverlap(), demo())
print(len(result.traces), "traces,", len(result.values), "values")
```

```console
5 traces, 11 values
```

That call gave `WordOverlap` the three documents of the `demo` conversation, put the five
questions to it one at a time, timed every call at memrank's own boundary, recorded one
[trace](trace.md) per question, and then applied the [measures](measure.md) `demo` bundles.
It needed no engine, no network and no API key.

## What it is

`memrank.run(system, evaluation)` is the entry point of the package, and it takes exactly the
two things a number needs: the [system](system.md) under test and the [evaluation](evaluation.md)
to put to it. You compose the run at the call -- there is no configuration file between you and
it, and nothing is registered in advance.

What it does, in order:

1. **It refuses, or it does not.** Before touching the system, memrank checks that the run can
   be set up at all. It refuses -- with a stated reason and no traces -- when the system is not
   a kind memrank knows, when it lacks a verb its kind requires, when a measure reads a name
   nothing in the run produces, or when the evaluation carries documents to give and the system
   has no verb to be told things with.
2. **It gives, asks and records.** Per group of tasks: clear, give the group's documents once,
   then put each prompt. One trace per task per attempt, including when a task raises -- the
   run never stops on a task's failure.
3. **It measures.** The evaluation's measures read the traces and produce named values.
4. **It returns a [result](result.md).**

Refusing before the run rather than during it is the point of the declarations: a run that
cannot produce what is asked of it costs you nothing and tells you why.

## Who supplies what

| You supply | Memrank supplies |
|---|---|
| the system instance, or a name | the run loop, the isolation, the clock |
| the evaluation, yours or one that ships | the refusal check before anything is touched |
| optionally `k=`, `attempts=`, `answerer=` | one trace per task per attempt, and the values |

## The Python names

```python
import inspect

import memrank

print(inspect.signature(memrank.run))
```

```console
(system: 'System', evaluation: 'Evaluation', *, answerer: 'Answerer | None' = None, k: 'int' = 10, attempts: 'int' = 1) -> 'Result'
```

- `memrank.run(system, evaluation)` -- the two positional arguments, in that order.
- `k=` -- how many documents to ask a memory or retriever for. Default 10.
- `attempts=` -- how many times to put each task. Default 1.
- `answerer=` -- a writer that turns what was recalled into an answer, needed when a measure
  reads `answered` and the system only recalls.
- `result.refusal` -- the reason, when the run refused. `None` when it went ahead.

## Going deeper

- [result](result.md) -- what comes back.
- [`examples/01-first-result/`](../../examples/01-first-result/) -- the shortest working run.
- [Methodology](../methodology.md) -- the context-budget control, the arms, and what a run is
  evidence of.

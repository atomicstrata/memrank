# measure

## An instance, first

A **measure** is one named rule that reads what happened and produces named numbers. Four ship
with the package:

- **`word-match`** -- did the expected words actually appear in something the system recalled?
  For `q_job`, whose expected span is `marine biologist`, it is 1.0 when that phrase is in a
  recalled document and 0.0 when it is not. Decided by a fixed rule, and it is retrieval, not
  answer correctness -- it says so on every value it produces.
- **`latency`** -- how long ingest and retrieve took, at memrank's own call boundary. Decided
  by memrank's clock.
- **`failure-rate`** -- how many traces carry an error. Decided by memrank's bookkeeping.
- **`judge`** -- was the answer actually right? Decided by a model, which is why it needs a key
  and the others do not.

```python
import memrank

word_match = memrank.WordMatch()
print(word_match.name, word_match.scope.value, word_match.reads, word_match.decider.value)
```

```console
word-match task ('recalled',) rule
```

## What it is

A measure declares three things **before** it runs:

1. **`scope`** -- `Scope.TASK` (one value per task) or `Scope.RUN` (one value for the whole
   run);
2. **`reads`** -- which [trace](trace.md) fields and which other measures' values it needs;
3. **`decider`** -- who is responsible for the number. `Decider.MEMRANK` is memrank's own clock
   and bookkeeping, `Decider.RULE` a fixed rule, `Decider.MODEL` a model that adjudicated, and
   `Decider.SYSTEM` the system's own word.

The declaration is not decoration. A measure that reads a name nothing in the run produces is
refused *before* the run, naming what is available, rather than raising halfway through one.

Measuring is not inside the run loop. That is what lets a measure you thought of afterwards run
over traces already stored: `memrank.measure(result, MyMeasure())` returns a new result with
the extra values in it, and the system is never touched again.

A measure that produces several numbers names each under its own name -- `latency.retrieve.p50`
and `latency.retrieve.p95` are two values of one measure, told apart by name and never by
position. Memrank invents no overall score across measures.

A measure that could not decide returns `None` with the reason, never `0.0`.

## Who supplies what

| You supply | Memrank supplies |
|---|---|
| a measure of your own, when you have a question the shipped ones do not answer | `WordMatch`, `Latency`, `FailureRate` and `Judge` |
| its `name`, `scope`, `reads` and `decider` | the refusal when `reads` names something nothing produces |
| the `measure()` method: traces and values in, values out | the traces to run it over, during the run or long after |

## The Python names

```python
from collections.abc import Sequence

import memrank
from memrank import Decider, Measure, Scope, Trace, Value
from memrank.evaluations import Demo
from memrank.systems import WordOverlap


class RecalledCount(Measure):
    """How many documents came back for each task."""

    name, scope, reads, decider = "recalled-count", Scope.TASK, ("recalled",), Decider.RULE

    def measure(self, traces: Sequence[Trace], values: Sequence[Value]) -> list[Value]:
        return [Value(measure=self.name, decider=self.decider, task_id=trace.task_id,
                      value=float(len(trace.recalled.documents)) if trace.recalled else None,
                      why="documents the system returned")
                for trace in traces]


result = Demo().run(system=WordOverlap())
measured = memrank.measure(result, RecalledCount())
print(measured.values_of("recalled-count")[0].value)
```

```console
2.0
```

- `memrank.Measure` -- the base class. You set `name`, `scope`, `reads`, `decider` and write
  `measure(traces, values)`.
- `memrank.Scope` -- `TASK`, `RUN`.
- `memrank.Decider` -- `MEMRANK`, `RULE`, `MODEL`, `SYSTEM`.
- `memrank.Value` -- what a measure produces: `measure`, `decider`, `task_id`, `group`,
  `value`, `why`.
- `memrank.WordMatch`, `memrank.Latency`, `memrank.FailureRate`, `memrank.Judge` -- the four
  that ship. They are ordinary measures and nothing more.
- `memrank.measure(result, *measures)` -- applying measures to a [result](result.md) already
  stored.

## Going deeper

- [`examples/04-your-own-measure/`](../../examples/04-your-own-measure/) -- a working one.
- [Adding an evaluation](../evaluations.md) -- bundling measures into an evaluation.
- [Methodology](../methodology.md) -- what each shipped measure actually measures, and what a
  number licenses you to say.

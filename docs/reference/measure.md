# measure

A **measure** is one named rule that reads [traces](trace.md) and produces named values. Four
ship with the package:

| Measure | What it answers | Decided by |
|---|---|---|
| `word-match` | did the expected words appear in something the system recalled? It is retrieval, not answer correctness, and says so on every value | a fixed rule |
| `latency` | how long ingest and retrieve took, at memrank's own call boundary | memrank's clock |
| `failure-rate` | how many traces carry an error | memrank's bookkeeping |
| `judge` | was the answer right? | a model, which is why it needs a key and the others do not |

```python
import memrank

word_match = memrank.WordMatch()
print(word_match.name, word_match.scope.value, word_match.reads, word_match.decider.value)
```

## What it is

A measure declares three things **before** it runs:

1. **`scope`** -- `Scope.TASK` (one value per task) or `Scope.RUN` (one for the whole run);
2. **`reads`** -- which trace fields and which other measures' values it needs;
3. **`decider`** -- who is responsible for the value. `Decider.MEMRANK` is memrank's own clock
   and bookkeeping, `Decider.RULE` a fixed rule, `Decider.MODEL` a model that adjudicated, and
   `Decider.SYSTEM` the system's own word.

A measure that reads a name nothing in the run produces is refused *before* the run, naming what
is available, rather than raising halfway through one.

Measuring is not inside the run loop, so a measure you thought of afterwards runs over traces
already stored: `memrank.measure(result, MyMeasure())` returns a new [result](result.md) with
the extra values in it, and the system is never touched again.

A measure that produces several values names each one -- `latency.retrieve.p50` and
`latency.retrieve.p95` are told apart by name and never by position. Memrank invents no overall
score across measures.

A measure that could not decide returns `None` with the reason, never `0.0`.

## Who supplies what

Memrank supplies the four above, the traces to run a measure over, and the refusal when `reads`
names something nothing produces. You supply a measure of your own when the shipped ones do not
answer your question: its `name`, `scope`, `reads`, `decider`, and a `measure()` method taking
traces and values and returning values.

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

- `memrank.Measure` -- the base class. You set `name`, `scope`, `reads`, `decider` and write
  `measure(traces, values)`.
- `memrank.Scope` -- `TASK`, `RUN`.
- `memrank.Decider` -- `MEMRANK`, `RULE`, `MODEL`, `SYSTEM`.
- `memrank.Value` -- what a measure produces: `measure`, `decider`, `task_id`, `group`,
  `value`, `why`.
- `memrank.WordMatch`, `memrank.Latency`, `memrank.FailureRate`, `memrank.Judge` -- the four
  that ship. They are ordinary measures and nothing more.
- `memrank.measure(result, *measures)` -- applying measures to a result already stored.

## Going deeper

- [The measures memrank ships](../measures.md) -- each one in full.
- [Methodology](../methodology.md) -- what a value licenses you to say.
- [`examples/04-your-own-measure/`](../../examples/04-your-own-measure/) -- a working one.

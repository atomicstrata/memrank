# trace

A **trace** is the record of one [task](task.md) being put to the system: what was given, what
came back, how long each step took, and what broke if anything did. It is what lets a value be
traced to the thing it is a value about.

```python
from memrank.evaluations import Demo
from memrank.systems import WordOverlap

result = Demo().run(system=WordOverlap())
trace = result.traces_of("q_job")[0]

print("task:    ", trace.task.id, "|", trace.task.prompt)
print("given:   ", trace.given.count, "document(s):", trace.given.document_ids)
print("recalled:", [document.id for document in trace.recalled.documents])
print("timed:   ", sorted(trace.timings_ms))
print("error:   ", trace.error)
```

## What it is

Exactly one trace is recorded per task per attempt, **including on failure**. A task that raised
does not vanish and does not become a gap: its trace carries the step it broke at and the
message, and every task-scope [measure](measure.md) records `None` with that as the reason.

| Field | What it holds |
|---|---|
| `task` | the task that was put, in full |
| `group` | the group whose state was in force |
| `attempt` | which attempt this was, when a run asks more than once |
| `given` | what memrank gave the system before the prompt: the document ids and how many |
| `recalled` | what a memory or retriever returned -- the passages, ranked best first |
| `answered` | what a model or assistant wrote, when the system is one that answers |
| `timings_ms` | memrank's own clock, per step, at memrank's own call boundary |
| `declared` | what only the system knew and chose to state: its version, tokens a provider billed, time only it can see, a fingerprint of its state. `None` means "did not state", never zero |
| `error` | the step it broke at and the message, or `None` |
| `started`, `finished` | when |

The order of `recalled.documents` **is** the measurement: a system returns its best guess first,
and nothing re-ranks it afterwards.

Traces are the durable part. Scoring does not happen inside the run loop, so a measure you think
of a week later runs over traces already stored and the system is never touched again.

## Who supplies what

You write nothing: memrank records every field above as the task ran, and your system optionally
declares what only it knew.

## The Python names

- `memrank.Trace` -- the class. Fields as above.
- `result.traces` -- every trace of a run, in order.
- `result.traces_of("<task id>")` -- the traces of one task. Where you dig when a value is low.
- `trace.recalled` is a `memrank.Recall`: `documents`, and whatever the system chose to
  `declare` about the call.
- `result.save(path)` and `memrank.Result.load(path)` -- traces written to disk and read back,
  typed, in another process.

## Going deeper

- [result](result.md) -- the object holding the traces and the values together.
- [measure](measure.md) -- the rules that read traces and produce values.
- [The translator contract](../system-contract.md) -- which endpoint fills which trace field
  when the system is driven over HTTP.

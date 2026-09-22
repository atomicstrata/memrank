# NoContext -- `no-context`

```python
from memrank.systems import NoContext

system = NoContext()
```

A control that retrieves nothing, so the reader has to answer from what it already knows.

## How it works

It accepts every document it is told, stores it, and then returns an empty list to every
question. The [run](../reference/run.md) proceeds normally: the reader is handed no context and
answers closed-book.

## Why it matters

It bounds the question from below. If a model answers as well with no memory at all, the
[result](../reference/result.md) for an engine on that [evaluation](../reference/evaluation.md)
says nothing about memory -- the questions were answerable without it.

One honest limit: it is only meaningful on a judged [measure](../reference/measure.md). Measured
on retrieval alone it can only score on questions a system is supposed to decline, since it
retrieves nothing by construction.

## What it needs

Nothing. No service, no network, no key, no download.

## References

- [Methodology](../methodology.md) -- the three controls, why each belongs beside an engine, and
  the published names for this condition.
- [Roberts et al., EMNLP 2020](https://aclanthology.org/2020.emnlp-main.437/) -- the same
  condition under the field's older name, *closed-book*.
- [fixed-context](fixed-context.md) and [full-context](full-context.md) -- the other two
  controls.

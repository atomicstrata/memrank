# FullContext -- `full-context`

```python
from memrank.systems import FullContext

system = FullContext()
```

A control that hands over the whole corpus with no cap: the ceiling retrieval is aiming at.

## How it works

The same as [fixed-context](fixed-context.md) -- store everything, return everything unranked --
except that no token budget cuts it. The reader is given the corpus.

## Why it matters

It answers whether memory is needed here at all. Where the corpus fits in a model's context
window, this arm is what a system with no retrieval problem to solve would score, so an engine
that matches it has matched the ceiling and an [evaluation](../reference/evaluation.md) whose
corpus is that small cannot tell engines apart.

It is deliberately rare for that reason: it belongs on small corpora, as a ceiling, not on every
row.

## What it needs

Nothing. No service, no network, no key, no download. It does need a corpus that fits, which is
a property of the evaluation rather than of this system.

## References

- [Methodology](../methodology.md) -- why an uncapped arm is rare, and what an uncapped budget
  does to comparability.
- [no-context](no-context.md) and [fixed-context](fixed-context.md) -- the other two controls.

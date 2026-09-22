# FixedContext -- `fixed-context`

```python
from memrank.systems import FixedContext

system = FixedContext()
```

A control that hands over the corpus unranked, cut off at the same token budget the engine
beside it was held to.

## How it works

It stores every document it is told, and answers every question with all of them, in the order
they arrived. It selects nothing and ranks nothing. Where a judged measure hands that text to a
reader, the run's shared token budget cuts it at the same size the engine under test was
allowed, which is what makes the comparison a fair one.

## Why it matters

It separates *selecting well* from *sending more*. Held to the same number of tokens, an engine
that beats this arm beat it by choosing what to retrieve -- not by filling more of the prompt.
Without a matched control, better recall and a larger prompt look identical in a
[result](../reference/result.md).

One honest limit: reading from the start is not neutral. A corpus whose answers sit late is
harder for this arm than for ranked retrieval, in a way the numbers will not show you.

## What it needs

Nothing. No service, no network, no key, no download.

## References

- [Methodology](../methodology.md) -- the token budget as a fairness control, and the arm's
  published counterparts.
- [Laitenberger, Manning & Liu, EMNLP 2025](https://arxiv.org/abs/2506.03989) -- the argument
  for matching budgets across arms.
- [no-context](no-context.md) and [full-context](full-context.md) -- the other two controls.

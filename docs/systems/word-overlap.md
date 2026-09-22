# WordOverlap -- `word-overlap`

```python
from memrank.systems import WordOverlap

system = WordOverlap()
```

Keyword retrieval in about thirty lines: the floor a real memory engine has to beat.

## How it works

It keeps every document it is told in a Python list, one list per group of
[tasks](../reference/task.md). When asked a question it splits the question into words, counts
how many of those words each stored document contains, drops the documents that share none, and
returns the highest counts first.

That is the whole mechanism. No weighting by how rare a word is, no sentence meaning, no model,
no index. It is not BM25 and does not claim to be.

## Why it matters

It is the dumb-memory floor. A system that does not beat plain word counting is not earning
what it costs, so a row with `word-overlap` beside it says whether the system's retrieval is
doing anything at all.

It is also the baseline [TFIDF](tfidf.md) and [BM25](bm25.md) are read against: the same
keyword idea with no weighting at all. Its latency is not comparable with an engine reached over
HTTP -- it runs inside your own process, and it declares
that, so [methodology](../methodology.md) can keep the two apart.

## What it needs

Nothing. No service, no network, no key, no download.

## References

- [system](../reference/system.md) -- what a system is.
- [Methodology](../methodology.md) -- why this is a memory floor rather than a control arm, and
  the published arm names it maps onto.
- [BEIR](https://arxiv.org/abs/2104.08663) -- names the family above this one, *lexical*
  retrieval, of which unweighted word overlap is the simplest member.

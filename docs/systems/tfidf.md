# TFIDF -- `tfidf`

```python
from memrank.systems import TFIDF

system = TFIDF()
```

Keyword search weighted by how rare each word is: the classic lexical baseline, in plain Python.

## How it works

It keeps every document it is told in a Python list, one list per group of
[tasks](../reference/task.md). When asked a question it splits the question and every stored
document into words -- lowercased, cut at anything that is not a letter or a digit -- and gives
each word a weight with two halves.

The first half is how often the word occurs in that document. The second is how rare the word is
across the group: `ln(N / df)`, where `N` is how many documents there are and `df` how many of
them contain the word. A word in every document scores exactly zero, which is what stops *the*
and *was* from deciding the ranking.

Question and document each become a vector of those weights, and the score is the **cosine**
between them -- the overlap divided by both lengths. Dividing by the document's length is what
lets a short document that is mostly about the question outrank a long one that merely mentions
it. Documents scoring zero are dropped, and the rest come back highest first.

No index, no model, no dependency. [`BM25`](bm25.md) is the same corpus under the weighting that
replaced this one, and the two share a tokeniser so the scoring is the only difference between
them.

## Why it matters

It is the baseline a reader recognises. TF-IDF is over fifty years old and is what every
retrieval result has been compared against since, so a row with `tfidf` beside it is a number
whose meaning does not have to be explained: a system that does not beat weighted keyword
matching is not earning what it costs.

It is also the system a first number is taken on, because it needs nothing. Its latency is not
comparable with an engine reached over HTTP -- it runs inside your own process, and it declares
that, so [methodology](../methodology.md) can keep the two apart.

## What it needs

Nothing. No service, no network, no key, no download.

## References

- [system](../reference/system.md) -- what a system is.
- [`BM25`](bm25.md) -- the same corpus, scored by the method that replaced this one for ranking.
- [`WordOverlap`](word-overlap.md) -- the same idea with neither half of the weighting, kept as
  the dumb-memory floor.
- [Methodology](../methodology.md) -- what a value licenses you to say.
- Karen Sparck Jones, [*A statistical interpretation of term specificity and its application in
  retrieval*](https://doi.org/10.1108/eb026526), Journal of Documentation 28(1), 1972 -- where
  inverse document frequency comes from.
- Gerard Salton, A. Wong and C. S. Yang, [*A vector space model for automatic
  indexing*](https://doi.org/10.1145/361219.361220), Communications of the ACM 18(11), 1975 --
  the vector model this ranks with, cosine and all.

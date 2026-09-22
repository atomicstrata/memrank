# Hindsight -- `hindsight`

```python
from memrank.systems import Hindsight

system = Hindsight(base_url="http://localhost:8888", api_key="...")
```

Vectorize.io's open-source agent memory, driven over its HTTP API.

## How it works

The engine runs as a service. Memrank gives each group of [tasks](../reference/task.md) its own
bank, retains each document into that bank as the [evaluation](../reference/evaluation.md) hands
it over, and recalls against the bank at question time.

Hindsight's own design, as its authors describe it: retaining splits a document into facts;
recall runs several strategies at once -- meaning-based, keyword, graph expansion and temporal --
fuses their orderings, reranks the survivors, and packs them to a token budget. It answers with a
token budget rather than a fixed number of results, which is why memrank's own budget is the
thing holding the arms level.

## Why it matters

It is one of the engines memrank exists to measure neutrally. Its authors publish strong numbers
on public evaluations, obtained at their own retrieval depth and with their own reader and judge;
a memrank row is a different measurement, taken under one budget with controls beside it, so the
two are not interchangeable.

## What it needs

A running Hindsight service. Its address comes from `base_url=` or `HINDSIGHT_API_URL`,
defaulting to `http://localhost:8888`, and a key, where auth is enabled, from
`HINDSIGHT_API_KEY`.

## References

- [vectorize-io/hindsight](https://github.com/vectorize-io/hindsight) -- the engine, MIT
  licensed.
- [arXiv:2512.12818](https://arxiv.org/abs/2512.12818) -- *Hindsight is 20/20: Building Agent
  Memory that Retains, Recalls, and Reflects*.
- [Methodology](../methodology.md) -- why a vendor's published number and a memrank row are not
  the same measurement.

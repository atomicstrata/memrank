# BEAM -- `beam`

<!-- runnable: no -- a one-time dataset download the first time it is constructed -->
```python
from memrank.evaluations import BEAM

evaluation = BEAM()
```

One continuous story per conversation, hundreds of thousands of tokens long, with questions
aimed at ten distinct memory abilities.

## How it works

Each conversation is a single user's narrative rather than stitched-together chats, and comes in
size tiers -- memrank supports 100K, 500K and 1M tokens. Memrank gives one conversation to the
[system](../reference/system.md), then asks that conversation's probing questions; each
conversation is its own group and is cleared afterwards.

The ten abilities include three that the other evaluations here do not test at all: noticing that
a later statement contradicts an earlier one, putting events in the order they happened, and
following an instruction given long ago.

Engines are handed nothing but who said what. No rendered dates, no machine timestamps -- which
is what every published harness for it does, including the authors' own baselines, and is what
makes a memrank number on it a number about the same task.

## Why it matters

It is the scale test. Where an evaluation whose corpus fits in a context window cannot separate
memory from simply reading everything, these conversations cannot be read at all, so retrieval is
doing real work and the result says something a smaller evaluation cannot.

**Quality here requires a judge.** The authors grade an answer against a rubric of small atomic
facts, one judgement each, averaged within the question -- and for the ordering ability, by how
well the answer's order matches the rubric's, because averaging would score a reversed answer as
highly as a correct one. Memrank grades it that way and no other. Without a judge this evaluation
reports latency, failures and counts: an earlier retrieval proxy here was withdrawn because a
number that is displayed gets quoted whatever label sits beside it.

Its own protocol hands the reader everything retrieval returned, so memrank's token budget is
lifted for it, symmetrically across every system.

## What it needs

A one-time download of the dataset, cached after the first run, or a local copy pointed at with
`BEAM_DATA_PATH`. The largest tier lives in a separate dataset and is not covered here.

Quality also needs a judge, which means a model key and sending question text to that model.

The data is share-alike licensed, which is stricter than its code license and carries over to
anything derived from it.

## References

- [mohammadtavakoli78/BEAM](https://github.com/mohammadtavakoli78/BEAM) -- the authors' code, MIT.
- [arXiv:2510.27246](https://arxiv.org/abs/2510.27246) -- *Beyond a Million Tokens: Benchmarking
  and Enhancing Long-Term Memory in LLMs*, ICLR 2026.
- [Methodology](../methodology.md) -- the token budget, and the evaluations exempt from it.

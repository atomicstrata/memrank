# LoCoMo -- `locomo`

<!-- runnable: no -- a one-time dataset download the first time it is constructed -->
```python
from memrank.evaluations import LoCoMo

evaluation = LoCoMo()
```

Ten very long dated conversations, with about 1,500 scored questions about what was said in them.

## How it works

Each conversation runs over weeks of dated sessions between two speakers -- hundreds of turns,
tens of thousands of words. Memrank gives one conversation at a time to the
[system](../reference/system.md), session by session, then asks that conversation's questions.
Each conversation is its own group, so the memory is cleared between them and one conversation
cannot answer another's questions.

The questions come in four kinds: one fact from one session, a fact assembled from several, a
question about *when* something happened, and one that needs outside knowledge as well. A fifth
kind in the data -- deliberately unanswerable questions -- is excluded, because the release ships
almost none of them with an answer to grade against.

## Why it matters

It is the public evaluation most memory vendors quote, so it is the one where a neutral, budget-
matched number is most worth having. It is also the one to be most careful with: its conversations
fit inside a current model's context window, so [full-context](../systems/full-context.md) can
reach the ceiling on it, and a strong score does not establish that memory was needed.

**Quality here requires a judge.** The published protocol grades the generated answer against a
reference, which no fixed rule can do: the reference answers are derived -- *"three times"*,
*"2022"* -- rather than quotes, so looking for them in retrieved text measures how literally an
engine stored things. Without a judge this evaluation reports latency, failures and question
counts, and no quality number at all.

## What it needs

A one-time download of the dataset, cached after the first run, or a local copy pointed at with
`LOCOMO_DATA_PATH`. The cached file is checked against a pinned checksum on every load, so a
drifted or revised copy fails loudly rather than quietly scoring.

Quality also needs a judge, which means a model key and sending question text to that model.

The data is licensed for non-commercial use. Check that before you build on a number from it.

## References

- [snap-research/locomo](https://github.com/snap-research/locomo) -- the data and the authors'
  own harness.
- [arXiv:2402.17753](https://arxiv.org/abs/2402.17753) -- *Evaluating Very Long-Term
  Conversational Memory of LLM Agents*, ACL 2024.
- [Methodology](../methodology.md) -- why quality needs a judge, and what a non-discriminative
  evaluation licenses you to say.

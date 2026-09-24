# SQuAD (Stanford Question Answering Dataset) -- `squad`

<!-- runnable: yes -- the quick-start subset is bundled; no download -->
```python
from memrank.evaluations import SQuAD

evaluation = SQuAD()
```

A fixed subset of SQuAD v1.1's development set, used to retrieve passages that answer questions.

## How it works

SQuAD natively supplies a passage alongside questions about it. Memrank instead supplies the
[system](../reference/system.md) with all 32 passages as documents in one isolated pool, then asks
64 questions. The subset is the first 32 paragraphs in article/paragraph array order, with
the first two questions from each paragraph's question array. There is no sampling.
The JSON records this rule, source checksum and attribution in its provenance field. A tracked
run's receipt -- the command line writes one -- records the bounds and the actual data checksum;
`evaluation.run()` in Python returns a [result](../reference/result.md), which carries no receipt.

Source answer spans establish which passage answers each question. The scorer never inspects
an answer: a hit requires the entire source passage inside a returned document, with whitespace
collapsed and case preserved. Document IDs alone do not earn credit. Missing responses are misses.
The composite is the fraction of questions with a retrieved passage, with breakdowns by article title.
The default retrieval limit is 10 documents per question.

## Why it matters

This measures **full-passage retrieval recall, not answer-span or end-to-end answer correctness**.
It is a passage-retrieval adaptation of SQuAD, not SQuAD's native exact-match or answer-token F1
score. It tests whether the system can retrieve the passage known to answer a question; it does
not test whether the system can produce the answer. Returning more passages can increase recall;
this measure does not penalize irrelevant returned passages. Keep retrieval limits comparable.

The 32-passage pool is an installation check, not evidence of performance over a full corpus.
Its scores are not directly comparable with published open-domain retrieval results.

TF-IDF and BM25 are standard passage-retrieval baselines in open-domain question answering
([Karpukhin et al., 2020](https://arxiv.org/abs/2004.04906) calls them "the de facto method").

## What it needs

The default needs no download, API key or service. The package includes 32 passages and 64
questions (62,472 bytes of JSON). `slice="smoke"` selects this same bundled mode;
`slice="full"` selects the complete development set, below. [TFIDF](../systems/tfidf.md) runs it
locally.
[Demo](demo.md) remains the dependency-free synthetic smoke evaluation.

The complete development set is an explicit choice: 2,067 passages and 10,570 questions.
It downloads 4,854,279 bytes once to `~/.memrank/datasets/squad/dev-v1.1.json`, or under
`MEMRANK_CACHE_DIR` when set. The complete file is verified against SHA256
`95aa6a52d5d6a735563366753ca50492a658031da74f301ac5238b03966972c9` before use.

<!-- runnable: no -- a one-time dataset download the first time it is constructed -->
```python
from memrank.evaluations import SQuAD

evaluation = SQuAD(slice="full")
```

`SQUAD_DATA_PATH` or `data_path=` selects a local v1.1 file. Default mode still applies the
32-passage/two-question bounds; full mode uses every passage and question. A local override
is recorded in the receipt. A missing bundle, invalid selected file, checksum failure or failed
download raises an error; none substitutes another dataset or mode.

## Licence and references

SQuAD v1.1 is CC BY-SA 4.0. The bundled subset retains that licence separately from memrank's
Apache-2.0 code. Credit: Pranav Rajpurkar, Jian Zhang, Konstantin Lopyrev and Percy Liang (2016).
The [packaged notice](../../memrank/benchmarks/data/SQUAD-NOTICE.md) records source links for every
passage, the selection and JSON reformatting, attribution and warranty disclaimer.

- [SQuAD paper](https://aclanthology.org/D16-1264/).
- [Canonical v1.1 development data](https://rajpurkar.github.io/SQuAD-explorer/dataset/dev-v1.1.json).
- [Official v1.1 licence statement](https://github.com/rajpurkar/SQuAD-explorer/blob/4a0f39d91d78da3236682ccf7b6eb9b1045d1f40/index.html).
- [CC BY-SA 4.0](https://creativecommons.org/licenses/by-sa/4.0/).
- [Methodology](../methodology.md).

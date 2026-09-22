# The evaluations that ship

An [evaluation](../reference/evaluation.md) is a named, versioned bundle: the
[tasks](../reference/task.md) to put to a [system](../reference/system.md), the
[measures](../reference/measure.md) it comes with, and the rule for when the system's memory is
cleared. Memrank ships six. One page each.

| Evaluation | Key | What it measures | What it needs |
|---|---|---|---|
| [SQuAD](squad.md) | `squad` | full-passage retrieval recall, not answer-span or end-to-end answer correctness | nothing; the quick-start subset is bundled |
| [Demo](demo.md) | `demo` | one small hand-written conversation and five questions about it -- the dependency-free smoke evaluation | nothing |
| [RelationGraph](relation-graph.md) | `relation_graph` | four situations that are easy to store and hard to store *correctly*, scored on what the system's memory graph did with them | nothing, and a graph-capable system |
| [LoCoMo](locomo.md) | `locomo` | ten very long dated conversations, with about 1,500 scored questions about what was said in them | a one-time download; a judge for quality |
| [LongMemEval](longmemeval.md) | `longmemeval` | five hundred questions, each one buried in its own separately built pile of chat sessions | a one-time download; a judge for quality |
| [BEAM](beam.md) | `beam` | one continuous story per conversation, hundreds of thousands of tokens long, with questions aimed at ten distinct memory abilities | a one-time download; a judge for quality |

`memrank.catalog()` prints the same list at runtime, and `squad`, `demo` and `relation_graph` are the three
that need nothing at all.

## The standard every page follows

The real name with its string key, and under it the one block that loads it; one line saying
what it is; how it works, in simple terms; why it matters -- what it measures and what kind of
value that is, a proxy or a judged one; what it needs; references. Nothing beyond what makes the
concept clear.

The words a page leans on -- [system](../reference/system.md), evaluation, task,
[trace](../reference/trace.md), measure, [run](../reference/run.md),
[result](../reference/result.md) -- are each defined once in
[the reference](../reference/README.md) and linked from here rather than explained again.

No page prints a result. What a value licenses you to say is
[methodology](../methodology.md)'s subject.

## Proxy or judged, and why it is on every page

Three of the six ship no quality number of their own. Their published protocol grades a
*generated answer* against a reference, which takes a model to adjudicate, and the two retrieval
proxies tried in their place were withdrawn for measuring the wrong thing -- one scored every
system zero, the other rewarded storing text verbatim. Without a judge those evaluations report
latency and failures and say so, rather than reporting a number that ranks.

`squad` checks whether the full source passage was retrieved; it never grades an answer.
`demo` uses an answer-substring proxy by design: its expected answers are literal spans, so a word match is a
meaningful proxy there, and it is labelled a retrieval proxy on every value it produces.
`relation_graph` scores structure rather than answers, which needs no judge.

## Using one

Pick an [evaluation](README.md), pick a [system](../systems/README.md), and hand the one to the
other.

```python
from memrank.evaluations import Demo
from memrank.systems import WordOverlap

result = Demo().run(system=WordOverlap())
```

## Where to go from here

- [evaluation](../reference/evaluation.md) -- what an evaluation is.
- [Adding an evaluation](../evaluations.md) -- bringing your own tasks and clearing rule.
- [Measures](../measures.md) -- the measure contract, and measuring stored traces afterwards.
- [The systems that ship](../systems/README.md) -- what to run one against.
- [Methodology](../methodology.md) -- what each shipped measure actually measures.

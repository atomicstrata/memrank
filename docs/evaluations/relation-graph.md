# RelationGraph -- `relation_graph`

```python
from memrank.evaluations import RelationGraph

evaluation = RelationGraph()
```

Four situations that are easy to store and hard to store *correctly*, scored on what the engine's
memory graph did with them.

## How it works

Each of the four fixtures sets a trap that ordinary retrieval scoring cannot see:

- a preference is stated, then changed in wording close enough that a careless engine keeps both;
- two different people share a name, and a fact about one must not attach to the other;
- something is implied rather than said, alongside a distractor that would support the wrong
  inference;
- one document at once updates an earlier fact, extends another, and implies a third.

Memrank hands each fixture to the [system](../reference/system.md), then reads the graph the
engine reports -- its memories and the relations between them, in one normalized shape -- and
scores the structure: did the superseded fact get marked superseded, did the collision stay
separate, was the inference drawn and the distractor left alone.

## Why it matters

It measures a different thing from every other evaluation here. The others ask whether the right
thing came back; this one asks whether what the engine *believes* is right. An engine can retrieve
the correct document and still hold two contradictory facts about the same person, which is the
failure that shows up later as a confidently wrong answer.

Its score is **structural and decided by a fixed rule** -- no judge, no model, no proxy for
something else. It is the only quality number here that stands on its own without a judge.

## What it needs

Nothing to download. It does need a system that reports its memory graph in the normalized shape.
A system that does not is recorded as not applicable, with that reason, before it is touched at
all -- never scored as though it had reported an empty graph.

## References

- [evaluation](../reference/evaluation.md) -- what an evaluation is.
- [Adding a system](../systems.md) -- what a system declares to report a graph.
- [supermemory](../systems/supermemory.md) and [atomicmemory](../systems/atomicmemory.md) -- two
  shipped systems that report one.

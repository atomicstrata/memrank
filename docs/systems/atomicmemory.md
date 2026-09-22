# AtomicMemory -- `atomicmemory`

```python
from memrank.systems import AtomicMemory

system = AtomicMemory(base_url="http://localhost:3070", api_key="...")
```

AtomicStrata's own memory engine, driven over its HTTP API.

## How it works

The engine runs as a service. Memrank posts each document to its memories endpoint as the
[evaluation](../reference/evaluation.md) hands them over, then asks it at question time for the
memories relevant to the question, and passes what comes back on as the recalled documents. Each
group of [tasks](../reference/task.md) gets its own namespace, which is deleted afterwards, so
nothing one group stored can answer another group's questions.

It also returns a graph of what it extracted, in the normalized shape the
[relation-graph evaluation](../evaluations/relation-graph.md) reads.

## Why it matters

It is the engine this instrument's maintainer builds, which is exactly why it is measured by the
same harness as everyone else's and given no shortcut: same
[measures](../reference/measure.md), same token budget, same controls beside it. Memrank
publishes no separate engine specification for it, so a row for it carries no vendor headline to
be compared against -- only the number the run produced.

## What it needs

A running AtomicMemory service. Its address comes from `base_url=` or `ATOMICMEMORY_API_URL`,
and a key, where the service wants one, from `ATOMICMEMORY_API_KEY`.

Cleanup deletes the namespaces it was given. Never point it at a store whose contents you want
to keep.

## References

- [system](../reference/system.md) -- what a system is, and what memrank measures rather than
  asking the engine for.
- [Engine images](../misc/engine-images.md) -- whether you can obtain a container for it.
- [Methodology](../methodology.md) -- comparability between an engine over HTTP and a control
  that runs in-process.

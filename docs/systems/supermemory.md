# Supermemory -- `supermemory`

```python
from memrank.systems import Supermemory

system = Supermemory(base_url="http://localhost:6767")
```

Supermemory AI's memory API, driven over HTTP against the self-hosted server.

## How it works

The engine runs as a service. Memrank clears the namespace for a group of
[tasks](../reference/task.md), stores each document it is given as memories -- splitting a long
one, because the engine caps how much a single memory holds -- and searches that namespace at
question time.

Supermemory's own design, as its authors describe it: memories are atomic and linked to each
other by exactly three relations -- one memory *updates* another, *extends* it, or is *derived*
from it -- and search combines meaning, keyword and graph. Memrank reads that graph in the
normalized shape the [relation-graph evaluation](../evaluations/relation-graph.md) needs.

## Why it matters

It is one of the engines memrank exists to measure neutrally, and one where the distinction
between what is published and what you can run yourself is sharp: the vendor's headline numbers
were taken on their hosted platform, and this system drives the self-hosted binary, whose memory
engine is not open source. A row here describes what you can actually run.

## What it needs

A running Supermemory server. Its address comes from `base_url=` or `SUPERMEMORY_BASE_URL`,
defaulting to `http://localhost:6767`.

Preparing a group of tasks clears that namespace first. Never point it at a store whose contents
you want to keep.

## References

- [supermemoryai/supermemory](https://github.com/supermemoryai/supermemory) -- the monorepo, MIT
  licensed. It carries the application and SDK layer; the memory engine ships as a prebuilt
  binary and its source is not in the repository.
- [supermemoryai/memorybench](https://github.com/supermemoryai/memorybench) -- the vendor's own
  harness.
- [Methodology](../methodology.md) -- why a hosted headline and a self-hosted row are not the
  same measurement.

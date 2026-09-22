# system

A **system** is the thing under test: a memory backend you run as a service, a class you wrote
around your own store, or one of the systems that ship with the package.

```python
from memrank.systems import TFIDF

system = TFIDF()
print(system.name, system.version)
```

[`TFIDF`](../systems/tfidf.md) ranks documents by the words they share with the query, weighted
by how rare each word is. It needs no engine, no network and no key.

## System and engine

A **system** is the object memrank drives and measures. An **engine** is the external service or
library a system talks to: the vendor's running product, not the system itself.

- `TFIDF` has no engine. It is pure Python running in your own process, so the system is all
  there is.
- AtomicMemory is an engine: a service AtomicStrata runs, with its own HTTP API. The system is
  [`memrank.systems.AtomicMemory`](../systems/atomicmemory.md), the class that drives that
  service -- sends it documents, asks it for what is relevant, and clears it.

So a result names a system, and an engine appears only as what a system reports about the
service behind it -- its engine version, what a provider billed it. A system you write may wrap
an engine or be the whole of the thing, and memrank measures it the same way either way.

## The four kinds

A system's **kind** is the class you subclass, so a kind cannot be declared wrong.

| Kind | The verb it is for | What it must implement |
|---|---|---|
| `memrank.Memory` | told things, asked later for what is relevant | `prepare`, `ingest`, `retrieve`, `cleanup` |
| `memrank.Model` | given a prompt, returns text | `complete` |
| `memrank.Retriever` | given a query, returns the top `k` of a corpus it already holds; nothing is told to it | `rank` |
| `memrank.Assistant` | given a list of `role`/`content` messages, replies however it likes | `respond` |

Those verbs are the whole of what a kind requires. Memrank times every ingest and retrieve at
its own call boundary, so latency is neither your job nor something your system could flatter.
What only your system knows -- its engine version, what a provider billed it, time only it can
see -- it declares through optional methods that return `None` until you say otherwise, and
`None` is recorded as "did not state", never as zero.

A [run](run.md) refuses before touching the system when it is not a kind memrank knows, or when
it lacks a verb its kind requires.

## Who supplies what

You supply the system and its configuration -- `base_url=`, `api_key=`, whatever it needs.
Memrank supplies the run loop, isolation between groups of [tasks](task.md), and the latency and
token instrumentation.

## The Python names

```python
import memrank
from memrank.systems import TFIDF, NoContext

print(TFIDF().name, NoContext().name)
print(memrank.system("tfidf").name)          # the same thing, by string
print(isinstance(TFIDF(), memrank.Memory))   # its kind, which the class decides
```

- `memrank.System` -- the base every kind derives from; what `result.system` describes.
- `memrank.Memory`, `memrank.Model`, `memrank.Retriever`, `memrank.Assistant` -- the four kinds
  you subclass.
- `memrank.systems` -- the module holding what ships: `TFIDF`, `BM25`, `WordOverlap`,
  `NoContext`, `FixedContext`, `FullContext`, `AtomicMemory`, `Hindsight`, `Supermemory`,
  `Mem0`, `Native`.
- `memrank.system("<name>")` -- the same things by string, which is the form a config file has.
- `memrank.Document` and `memrank.Recall` -- what `ingest` is given and what `retrieve` returns.

## Going deeper

- [Adding a system](../systems.md) -- the four kinds, their verbs and the optional declarations,
  in full.
- [The translator contract](../system-contract.md) -- a system memrank drives over HTTP rather
  than imports.
- [Systems that ship](../systems/README.md) -- one page each.
- [`examples/02-your-own-system/`](../../examples/02-your-own-system/) -- a working one.

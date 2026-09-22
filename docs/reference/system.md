# system

A **system** is the thing under test: a memory backend you run as a service, a class you wrote
around your own store, or one of the systems that ship with the package.

```python
from memrank.systems import WordOverlap

system = WordOverlap()
print(system.name, system.version)
```

[`WordOverlap`](../systems/word-overlap.md) ranks documents by how many words they share with
the query. It needs no engine, no network and no key.

## The four kinds

A system's **kind** is the class you subclass, so a kind cannot be declared wrong.

| Kind | The verb it is for | What it must implement |
|---|---|---|
| `memrank.Memory` | told things, asked later for what is relevant | `prepare`, `ingest`, `retrieve`, `cleanup` |
| `memrank.Model` | given a prompt, returns text | `complete` |
| `memrank.Retriever` | given a query and candidates, orders them | `rank` |
| `memrank.Assistant` | given a prompt, answers it however it likes | `respond` |

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
from memrank.systems import NoContext, WordOverlap

print(WordOverlap().name, NoContext().name)
print(memrank.system("word-overlap").name)          # the same thing, by string
print(isinstance(WordOverlap(), memrank.Memory))    # its kind, which the class decides
```

- `memrank.System` -- the base every kind derives from; what `result.system` describes.
- `memrank.Memory`, `memrank.Model`, `memrank.Retriever`, `memrank.Assistant` -- the four kinds
  you subclass.
- `memrank.systems` -- the module holding what ships: `WordOverlap`, `NoContext`,
  `FixedContext`, `FullContext`, `AtomicMemory`, `Hindsight`, `Supermemory`, `Mem0`, `Native`.
- `memrank.system("<name>")` -- the same things by string, which is the form a config file has.
- `memrank.Document` and `memrank.Recall` -- what `ingest` is given and what `retrieve` returns.

## Going deeper

- [Adding a system](../systems.md) -- the four kinds, their verbs and the optional declarations,
  in full.
- [The translator contract](../system-contract.md) -- a system memrank drives over HTTP rather
  than imports.
- [Systems that ship](../systems/README.md) -- one page each.
- [`examples/02-your-own-system/`](../../examples/02-your-own-system/) -- a working one.

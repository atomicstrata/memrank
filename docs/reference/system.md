# system

## An instance, first

A **system** is the thing you are measuring. Concretely, it is one of these:

- a memory backend you run as a service -- Mem0, Supermemory, Hindsight, AtomicMemory -- that
  you feed documents and later ask for the ones relevant to a question;
- a class you wrote yourself around your own store, a vector database, or a pile of notes;
- `WordOverlap`, which ships with the package: about thirty lines that keep documents in a
  Python list and rank them by how many words they share with the query. It needs no engine, no
  network and no API key, and it exists so you can get a number before you have wired anything
  up.

```python
from memrank.systems import WordOverlap

system = WordOverlap()
print(system.name, system.version)
```

```console
word-overlap 0.1.0
```

## What it is

A system is the thing under test, and its **kind** is the class you subclass, so a kind cannot
be declared wrong. There are four:

| Kind | The verb it is for | What it must implement |
|---|---|---|
| `memrank.Memory` | told things, asked later for what is relevant | `prepare`, `ingest`, `retrieve`, `cleanup` |
| `memrank.Model` | given a prompt, returns text | `complete` |
| `memrank.Retriever` | given a query and candidates, orders them | `rank` |
| `memrank.Assistant` | given a prompt, answers it however it likes | `respond` |

Those verbs are the whole of what a kind requires. None of them reports a measurement memrank
takes itself: memrank times every ingest and retrieve at its own call boundary, so latency is
neither your job nor something your system could flatter. What only your system knows -- its
engine version, what a provider billed it, time only it can see -- it *declares* through
optional methods that return `None` until you say otherwise, and `None` is recorded as "did not
state", never as zero.

A [run](run.md) refuses before touching anything when the system is not a kind memrank knows,
or when it lacks a verb its kind requires.

## Who supplies what

| You supply | Memrank supplies |
|---|---|
| the system: an instance of a kind, or a name from what ships | the run loop that drives it |
| its configuration -- `base_url=`, `api_key=`, whatever it needs | isolation between groups of tasks |
| nothing else | latency and token instrumentation, and the material to give it |

## The Python names

```python
import memrank
from memrank.systems import NoContext, WordOverlap

print(WordOverlap().name, NoContext().name)
print(memrank.system("word-overlap").name)          # the same thing, by string
print(isinstance(WordOverlap(), memrank.Memory))    # its kind, which the class decides
```

```console
word-overlap no-context
word-overlap
True
```

- `memrank.System` -- the base every kind derives from; what `result.system` describes.
- `memrank.Memory`, `memrank.Model`, `memrank.Retriever`, `memrank.Assistant` -- the four kinds
  you subclass.
- `memrank.systems` -- the module holding what ships: `WordOverlap`, `NoContext`,
  `FixedContext`, `FullContext`, `AtomicMemory`, `Hindsight`, `Supermemory`, `Mem0`, `Native`.
- `memrank.system("<name>")` -- the same things by string, which is the form a config file and
  the command line have.
- `memrank.Document` and `memrank.Recall` -- what `ingest` is given and what `retrieve` returns.

## Going deeper

- [Adding a system](../systems.md) -- the four kinds, their verbs, and the optional
  declarations, in full.
- [The translator contract](../system-contract.md) -- when your system is a service in another
  language that memrank drives over HTTP rather than a class it imports.
- [`examples/02-your-own-system/`](../../examples/02-your-own-system/) -- a working one.
- [catalog](catalog.md) -- finding the names of the systems that ship.

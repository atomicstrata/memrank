# catalog

## An instance, first

You have installed memrank and you do not know a single name. What can you measure, and what
can you measure it against? One call answers both:

```python
import memrank

memrank.catalog()
```

```console
memrank ships 9 system(s) and 5 evaluation(s).

systems -- `from memrank.systems import WordOverlap`, or `memrank.system("word-overlap")`

  WordOverlap   'word-overlap'    memory   nothing -- in-process, offline
  NoContext     'no-context'      control  nothing -- the floor: retrieves nothing, answers closed-book
  FixedContext  'fixed-context'   control  nothing -- the corpus unranked, capped by the token budget
  FullContext   'full-context'    control  nothing -- the corpus uncapped: the ceiling retrieval aims at
  AtomicMemory  'atomicmemory'    memory   a running engine, at base_url= or ATOMICMEMORY_API_URL
  Hindsight     'hindsight'       memory   a running engine, at base_url= or HINDSIGHT_API_URL
  Supermemory   'supermemory'     memory   a running engine, at base_url= or SUPERMEMORY_BASE_URL
  Mem0          'mem0'            memory   the mem0 SDK, or a running engine at MEM0_HTTP_URL
  Native        'native'          memory   a running translator of memrank's system contract, at NATIVE_API_URL

evaluations -- `from memrank.evaluations import Demo`, or `memrank.evaluation("demo")`

  Demo()           'demo'            nothing -- a bundled synthetic scenario
                                     measures a substring retrieval proxy and evidence recall
  RelationGraph()  'relation_graph'  nothing -- in-repo fixtures, and a graph-capable system
                                     measures a structural graph score
  LoCoMo()         'locomo'          a one-time download, or LOCOMO_DATA_PATH
                                     measures latency and failures; quality needs a judge
  LongMemEval()    'longmemeval'     a one-time download, or LONGMEMEVAL_DATA_PATH
                                     measures latency and failures; quality needs a judge
  BEAM()           'beam'            a one-time download, or BEAM_DATA_PATH
                                     measures latency and failures; quality needs a judge
```

## What it is

The catalog is what memrank ships, printed. It is not one of the seven words and not a thing
you build -- it is the door onto the ones memrank already has.

Every row carries three things: the **Python name** you can import and an editor can follow,
the **string** the same thing answers to, and **what it needs from you** -- a running engine, a
download, an environment variable, or nothing at all. That third column is the useful one:
`WordOverlap` and `Demo` need nothing, which is why they are what a first result is made of.

`catalog()` both prints and returns, because there are two readers. A person runs it for the
table; a program reads `catalog().systems` and `catalog().evaluations` for the entries.

The two forms are the same things:

- `from memrank.systems import WordOverlap` gives you the class -- the form to use when you
  want to pass options, subclass, or have an editor follow the definition.
- `memrank.system("word-overlap")` gives you an instance from the string -- the form a config
  file and the command line have, and the one to use when the name is data rather than code.

## Who supplies what

| You supply | Memrank supplies |
|---|---|
| nothing | nine systems and five evaluations, with what each one needs stated |
| a name, once you have found one | both ways to reach it: the class and the string |

## The Python names

```python
import memrank
from memrank import evaluations, systems

print(len(systems.SHIPPED), "systems,", len(evaluations.SHIPPED), "evaluations")
print(memrank.system("word-overlap").name)
print(memrank.evaluation("demo").name)
```

```console
9 systems, 5 evaluations
word-overlap
demo
```

- `memrank.catalog()` -- prints the table and returns it.
- `memrank.systems` -- the module: `WordOverlap`, `NoContext`, `FixedContext`, `FullContext`,
  `AtomicMemory`, `Hindsight`, `Supermemory`, `Mem0`, `Native`.
- `memrank.evaluations` -- the module: `Demo`, `RelationGraph`, `LoCoMo`, `LongMemEval`,
  `BEAM`.
- `memrank.system("<name>")` and `memrank.evaluation("<name>")` -- the same things by string.

## Going deeper

- [system](system.md) and [evaluation](evaluation.md) -- what these entries are instances of.
- [Adding a system](../systems.md) -- getting your own into the catalog, when it should
  be reachable by name.
- [Engine images](../misc/engine-images.md) -- per shipped memory engine, whether you can actually
  obtain the container to run it.

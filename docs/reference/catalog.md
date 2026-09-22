# catalog

`memrank.catalog()` prints every system and every evaluation that ships, so you do not have to
know a name to find one. This page is about reading that table.

```python
import memrank

memrank.catalog()
```

<!-- output: exact -->
```console
memrank ships 11 system(s) and 6 evaluation(s).

systems -- `from memrank.systems import TFIDF`, or `memrank.system("tfidf")`

  TFIDF         'tfidf'           memory   nothing -- in-process, offline
  BM25          'bm25'            memory   nothing -- in-process, offline
  WordOverlap   'word-overlap'    memory   nothing -- in-process, offline
  NoContext     'no-context'      control  nothing -- the floor: retrieves nothing, answers closed-book
  FixedContext  'fixed-context'   control  nothing -- the corpus unranked, capped by the token budget
  FullContext   'full-context'    control  nothing -- the corpus uncapped: the ceiling retrieval aims at
  AtomicMemory  'atomicmemory'    memory   a running engine, at base_url= or ATOMICMEMORY_API_URL
  Hindsight     'hindsight'       memory   a running engine, at base_url= or HINDSIGHT_API_URL
  Supermemory   'supermemory'     memory   a running engine, at base_url= or SUPERMEMORY_BASE_URL
  Mem0          'mem0'            memory   the mem0 SDK, or a running engine at MEM0_HTTP_URL
  Native        'native'          memory   a running translator of memrank's system contract, at NATIVE_API_URL

evaluations -- `from memrank.evaluations import SQuAD`, or `memrank.evaluation("squad")`

  SQuAD()          'squad'           nothing -- 32 bundled passages, 64 questions
                                     measures full-passage retrieval recall, not answer-span or end-to-end answer correctness
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

Every row carries the **Python name** you can import and an editor can follow, the **string**
the same thing answers to, and **what it needs from you** -- a running engine, a download, an
environment variable, or nothing at all. That last column is the useful one: `TFIDF` and `SQuAD`
need nothing, which is why they are what a first result is made of.

A system row carries one more column, its role: `memory` for a system under test, `control` for
a floor or a ceiling to read it against. It is not the system's [kind](system.md) -- every
control is a `Memory`, and `result.system.kind` reports `memory` for one.

`catalog()` both prints and returns, because there are two readers. A person runs it for the
table; a program reads `catalog().systems` and `catalog().evaluations` for the entries.

The two forms reach the same things. `from memrank.systems import TFIDF` gives you the
class -- use it to pass options, to subclass, or to have an editor follow the definition.
`memrank.system("tfidf")` gives you an instance from the string -- use it when the name
is data rather than code.

## Who supplies what

Memrank supplies eleven [systems](system.md) and six [evaluations](evaluation.md), with what
each one needs stated, and both ways to reach each of them. You supply nothing.

## The Python names

```python
import memrank
from memrank import evaluations, systems

print(len(systems.SHIPPED), "systems,", len(evaluations.SHIPPED), "evaluations")
print(memrank.system("tfidf").name)
print(memrank.evaluation("squad").name)
```

- `memrank.catalog()` -- prints the table and returns it.
- `memrank.systems` -- the module: `TFIDF`, `BM25`, `WordOverlap`, `NoContext`, `FixedContext`,
  `FullContext`, `AtomicMemory`, `Hindsight`, `Supermemory`, `Mem0`, `Native`.
- `memrank.evaluations` -- the module: `SQuAD`, `Demo`, `RelationGraph`, `LoCoMo`,
  `LongMemEval`, `BEAM`.
- `memrank.system("<name>")` and `memrank.evaluation("<name>")` -- the same things by string.

## Going deeper

- [Systems that ship](../systems/README.md) and [evaluations that ship](../evaluations/README.md)
  -- one page each.
- [Adding a system](../systems.md) -- getting your own into the catalog.
- [Engine images](../misc/engine-images.md) -- per shipped memory engine, whether you can obtain
  the container to run it.

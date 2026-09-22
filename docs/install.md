# Installing memrank

Memrank is a Python package. You add it to a project, `import memrank`, and a few lines later you
have a [result](reference/result.md) with named values in it. Nothing on this page needs a running
engine, a network or an API key.

## 1. Add memrank to a project

```bash
uv add memrank
```

Already have a virtualenv and no [uv](https://docs.astral.sh/uv/)? `pip install memrank` into it
does the same thing.

No project yet? `uv init memrank-try` makes one in a new directory, and `uv add memrank` is run
from inside it. If you do not have uv at all:

```bash
curl -LsSf https://astral.sh/uv/install.sh | sh     # macOS / Linux
```

Memrank needs Python 3.10 or newer; uv installs one for you if the machine has none.

## 2. Run an evaluation

`WordOverlap` is a trivial in-process [system](reference/system.md) that ships with the package:
it keeps documents in a Python list and ranks them by how many words they share with the query.
`demo` is a small synthetic [evaluation](reference/evaluation.md) that ships with it -- five
questions about a short conversation. Neither needs anything you have not just installed.

Save this as `first_run.py`:

```python
import memrank
from memrank.evaluations import demo
from memrank.systems import WordOverlap

result = memrank.run(WordOverlap(), demo())

print(result.system.name, "on", result.evaluation.name)
for value in result.values_of("word-match"):
    print(f"{value.task_id:<14} {value.value}  decided by {value.decider.value}")
print(len(result.traces), "traces recorded")
```

Run it with `uv run python first_run.py`, or with `python first_run.py` in the virtualenv you
installed into:

```console
WordOverlap on demo
q_job          1.0  decided by rule
q_animal       1.0  decided by rule
q_visit        1.0  decided by rule
q_diet         0.0  decided by rule
q_allergy_neg  1.0  decided by rule
5 traces recorded
```

That is the whole of the loop. [`memrank.run`](reference/run.md) puts each
[task](reference/task.md) to the system, records one [trace](reference/trace.md) per task, and
applies the evaluation's [measures](reference/measure.md) to those traces. What comes back is a
[result](reference/result.md): the traces, and the values read off them. Every value names the
measure that produced it and who decided it -- here, a fixed rule -- so no number on the way out is
anonymous. `word-match` is a retrieval proxy and not answer correctness, which is what its own
`why` says on every value it produces.

`print(result)` instead of the loop above lays the whole thing out: the system, the evaluation, and
every value with its decider and its reason. Nothing you write has to format it.

## 3. See what else ships

[`memrank.catalog()`](reference/catalog.md) prints everything installed, with what each thing
needs, so you do not have to know a name to find one:

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

evaluations -- `from memrank.evaluations import demo`, or `memrank.evaluation("demo")`

  demo()            'demo'            nothing -- a bundled synthetic scenario
                                      measures a substring retrieval proxy and evidence recall
  relation_graph()  'relation_graph'  nothing -- in-repo fixtures, and a graph-capable system
                                      measures a structural graph score
  locomo()          'locomo'          a one-time download, or LOCOMO_DATA_PATH
                                      measures latency and failures; quality needs a judge
  longmemeval()     'longmemeval'     a one-time download, or LONGMEMEVAL_DATA_PATH
                                      measures latency and failures; quality needs a judge
  beam()            'beam'            a one-time download, or BEAM_DATA_PATH
                                      measures latency and failures; quality needs a judge
```

The engine-backed systems take a `base_url=` (and `api_key=` where the engine authenticates) where
`WordOverlap()` goes, and each reads its own environment variable when the argument is left out.
Whether you can obtain a given engine's image at all differs per engine --
[engine images](misc/engine-images.md) says which, and what to run for the two you cannot pull.

## 4. Upgrading

```bash
uv lock --upgrade-package memrank && uv sync      # or: pip install --upgrade memrank
```

`memrank.__version__` is what you are actually running:

```python
import memrank

print(memrank.__version__)
```

```console
0.4.0
```

<details>
<summary>Working on memrank itself</summary>

Take a checkout rather than a package install -- the repository is public, so this needs no GitHub
credential:

```bash
git clone https://github.com/atomicstrata/memrank
cd memrank
uv sync --extra dev
```

Your edits then apply immediately, and `uv run python first_run.py` from that checkout uses them.
For the test suite and the rest of the development loop, see
[local development](local-development.md).

To use an unreleased memrank from a project of your own, add the checkout instead of the package:
`uv add --editable ../memrank`.
</details>

## Known limitations

Nothing on this page is affected by the limitations memrank currently carries: every one of them
concerns a run submitted to the hosted platform and followed from the command line, and they are
listed under [known limitations](misc/command-line.md) there. A run you start from Python happens
in this process, against the system you constructed, and its result is the object you get back.

What a value does and does not license you to say is a different question, and a more important
one: [methodology](methodology.md) states it, and the README's *What a value is, and what it is
not* is the short form.

## Telling us something broke

`memrank.__version__` and the code you ran make a report actionable. Paste the whole error text:
messages are written to name the fix, and one that does not is itself worth reporting.

## The command line

Memrank ships a `memrank` command as well, and it is not core: you never need it to get a number,
and it keeps an older vocabulary of its own. [The command line](misc/command-line.md) is where it
lives, along with the tool install that puts it on your PATH, tracked runs, placement, the hosted
platform and the MCP server.

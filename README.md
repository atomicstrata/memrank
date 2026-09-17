# Memrank

> An instrument for measuring AI memory engines -- on your own machine, on your own data,
> under a configuration you can read and a result you can re-run.

**Status:** v0.3, in active development. Interfaces still move between releases.

Memrank runs a memory engine against a task set and emits a number with everything needed to
re-run it attached: the configuration, the dataset version, the model, the seed, and the
version of the instrument itself. It measures **quality, latency, cost, and token
efficiency** in one pass.

## What you bring, and what memrank takes care of

You bring the memory engine you want measured -- the one you are building, or one you already run.
You bring the questions you want it measured on, if you have data of your own; if you do not,
memrank ships its own. If you want a written answer judged rather than just the recalled text
scored, you also bring the model that answers from what the engine recalled and the rule that
decides whether that answer is right -- memrank has a default for both. Everything between those
pieces is memrank's: it feeds each case in and asks the questions back, runs the same measurement
against built-in comparison engines so your number has something to sit beside, scores the result
with labels that say what was actually measured and what was not, times every write and every
recall, adds up what the run cost in tokens and money, and writes down the versions, settings and
seed that produced the number so the same run can be done again.

## Install

```bash
uv tool install memrank
memrank --version
```

If you do not have [uv](https://docs.astral.sh/uv/): `curl -LsSf https://astral.sh/uv/install.sh | sh`.

Working on memrank itself? Clone it and see [Local development](docs/local-development.md).
Full install detail, upgrading, PATH and MCP setup: **[Installing memrank](docs/install.md)**.

## Run something in one minute

Memrank is a Python package, and `memrank.run(engine, evaluation)` is its entry point. Each of the
two arguments takes either a name from the catalog or an object you built yourself; the two forms
are interchangeable, and neither is the privileged one.

`word-overlap` is a trivial in-process retriever that ships with the package, and `demo` is a small
synthetic evaluation that ships with it too. Together they need no engine, no network, and no API
key:

```python
import memrank

result = memrank.run("word-overlap", "demo", repeats=1)
print(f"{result.composite:.3f}  {result.adapter} x {result.benchmark}")
```

```console
0.800  word-overlap x demo
```

### The same call, with your own engine and your own evaluation

An engine is any `MemoryAdapter` -- six methods -- and an evaluation is any `Benchmark` -- three.
Pass the instances where the names went. Nothing is registered, nothing is named, and no file is
written inside memrank:

```python
import memrank
from memrank import Benchmark, BenchmarkUnit, Document, MemoryAdapter
from memrank.instrumentation import LatencyCollector, TokenCollector


class MyEngine(MemoryAdapter):                      # your engine, six methods
    name, version, engine_version = "my-engine", "0.1", "0.1"

    def __init__(self):
        self.docs, self.lat, self.tok = [], LatencyCollector(), TokenCollector()

    def prepare(self, isolation_unit): self.docs = []
    def ingest(self, documents): self.docs.extend(documents)

    def retrieve(self, query, k, user_id, query_timestamp=None):
        words = set(query.lower().split())
        ranked = sorted(self.docs, key=lambda d: len(words & set(d.content.lower().split())),
                        reverse=True)
        return ranked[:k], {"engine": self.name}

    def cleanup(self): self.docs = []
    def latency_metrics(self): return self.lat.as_metrics()
    def token_metrics(self): return self.tok.as_metrics()


class MyEval(Benchmark):                            # your data, three methods
    name, dataset_version = "my-eval", "internal@1"

    def load(self):
        return [BenchmarkUnit(
            unit_id="u1", isolation_id="u1",
            documents=[Document(id="d1", user_id="u1",
                                content="Acme moved to the enterprise plan in March.")],
            queries=[{"id": "q1", "text": "What plan is Acme on?",
                      "required_spans": ["enterprise"]}])]

    def score(self, unit, responses):
        from memrank.metrics.scoring import score_query, spec_from_query
        by_id = {r.query_id: r for r in responses}
        hits = [score_query(spec_from_query(q), by_id[q["id"]].documents).hit for q in unit.queries]
        return {"composite": sum(hits) / len(hits), "per_category": {}, "n_queries": len(hits)}

    def report_template(self): return "composite: {composite}"


result = memrank.run(MyEngine(), MyEval(), repeats=1)
print(f"{result.composite:.3f}  {result.adapter} x {result.benchmark}")
```

```console
1.000  my-engine x my-eval
```

Registering an engine or an evaluation is how it becomes **shareable** -- reachable by name from the
command line, from a comparison, and from someone else's run -- never a precondition for measuring
it. [`examples/custom-engine.py`](examples/custom-engine.py) and
[`examples/custom-benchmark.py`](examples/custom-benchmark.py) are the two halves above as
commented, runnable scripts.

## The same run from the command line

The command line drives the same evaluation for the cases a script does not cover: a run you want
tracked, compared, or placed somewhere other than this process. The two shipped pieces above, by
name:

```console
$ memrank submit word-overlap demo
run 20260826-213813__demo__7becda  (word-overlap × demo)
track: memrank watch 20260826-213813__demo__7becda

$ memrank runs ls
ID                             TARGET        EVAL  PLACE  STATE  AGE  DONE  SCORE
20260826-213813__demo__7becda  word-overlap  demo  local  done     8s  100%  0.8000
```

`submit` returns immediately with a run id; `watch <id>` blocks on it, `runs show <id>` gives the
full record -- state, where it ran, exit code, artifact location -- and `kill <id>` stops it.

Finding your way around:

```bash
memrank targets ls               # what can be evaluated (hindsight, atomicmemory, word-overlap, ...)
memrank evals ls                 # what to evaluate against (locomo, beam, longmemeval, demo, ...)
memrank targets show hindsight   # the exact composition, and ✔/✘ per secret it needs
memrank submit --help       # every flag, grouped
```

## Running against a real engine

A **target** is a named composition -- an engine plus the embedder and LLM it is configured with --
so a row can never mean two different systems. Refs are `[namespace/]name[:preset]`; a bare ref is
the vendor's own configuration, and memrank's budget-matched comparison arm carries the suffix
(`hindsight` vs `hindsight:matched`).

`--on` says where the engine runs:

| | |
|---|---|
| `--on none` (default) | talk to an engine you are already running |
| `--on local` | provision a disposable, isolated stack per run from the target manifest (needs Docker) |
| `--on cloud` | submit to the hosted memrank platform (needs `memrank auth login`; membership is not self-served yet) |

```bash
export HINDSIGHT_API_URL=http://localhost:7000
memrank submit hindsight locomo:smoke --on none
```

Which engines you can actually obtain differs per target, and two of them you cannot pull at all.
[Engine images](docs/engine-images.md) states it per target, with what to run instead.

Judged runs send benchmark content to Anthropic and need `ANTHROPIC_API_KEY`. They are on by
default for `locomo`, `longmemeval` and `beam`, whose only quality metric is the judge's;
`--no-judge` measures latency and cost without paying for quality.

## What the scores mean -- and what they do not

This is the part worth reading before quoting a number.

- **`composite` is not answer correctness unless the benchmark says so.** LoCoMo, LongMemEval
  and `demo` compute a deterministic substring-recall proxy. Where that proxy is not meaningful
  for a benchmark, the rankable surfaces **withhold** the composite rather than printing one with
  a footnote. BEAM withholds its raw composite from ranking unless the run was judged.
- **A slice is not a measurement.** `beam:100k-smoke` and `locomo:mini` take the *first* N units,
  and the first units are not a fair sample -- measured, one benchmark's first conversation scores
  0.318 against 0.158 for the full tier. Slices exist to debug plumbing cheaply.
- **Absent is not zero.** An engine that reports no token usage records `null`, never `0.0`.
  Conflating them fabricates an efficiency win for every engine that stays quiet.
- **Context budget is the decisive variable.** Every arm in a comparison is held to the same
  retrieval token budget, unless the benchmark's own protocol declares the reader uncapped (BEAM
  and LongMemEval do). Without that control, "retrieved better" and "returned more text" are the
  same number.
- **A run from a mutable checkout is not evidence.** It is recorded as a
  `development_observation` with `publishable: false`, however clean the git tree -- a commit
  identifies source, not the executable that ran.

The full contract is [docs/methodology.md](docs/methodology.md), which states what a number does
and does not license you to say.

## Documentation

| | |
|---|---|
| [Installing memrank](docs/install.md) | install, sign-in, MCP, what works today |
| [Local development](docs/local-development.md) | working on memrank itself: environment, tests, checks |
| [Methodology](docs/methodology.md) | the four axes, the budget control, the control arms, evidence classes |
| [Adding an adapter](docs/adding-adapters.md) | in-tree adapters, and the out-of-tree translator |
| [Adding a benchmark](docs/adding-benchmarks.md) | loaders, scorers, registration |
| [`examples/`](examples/) | runnable scripts: the three-line run, a custom engine, a custom benchmark |
| [SPEC.md](docs/SPEC.md) | the specification: what memrank measures, and the governance it commits to |

## Contributing

Adding an engine does not require a fork or a pull request: write a **translator** that speaks the
adapter contract over HTTP in any language, point memrank at it, and run.
[`examples/native-adapter/`](examples/native-adapter/README.md) is a working one in about 150
lines of standard-library Python.

An **in-tree** adapter is for an engine that should be measurable by everyone who installs memrank.
It subclasses `MemoryAdapter`, lives in `memrank/adapters/`, and must pass
`tests/live/conformance/test_adapter_contract.py`. See [adding an adapter](docs/adding-adapters.md) and
[adding a benchmark](docs/adding-benchmarks.md).

Methodology changes need a matching change to [docs/methodology.md](docs/methodology.md). A
scoring change that is not documented is not a scoring change we can accept.

## Governance

Memrank is maintained by [AtomicStrata](https://atomicstrata.ai) under a vendor-neutral charter:
anyone may submit an adapter, results are published as measured, methodology changes go through
public proposal and comment, and competitor adapters are run with the same diligence as our own.
The commitments and their enforcement are in [SPEC.md section 5](docs/SPEC.md).

**Disclosure.** AtomicStrata also ships a memory engine, AtomicMemory. It is measured by this
instrument and has placed below a no-memory-layer control arm in our own runs. The only useful
response to that conflict is to make the method checkable rather than to assert neutrality --
which is what the audits under [`docs/`](docs/README.md) are for.

## License

Apache 2.0 -- see [LICENSE](LICENSE).

## Contact

- Methodology questions and disagreements: open an issue.
- Anything else: hello@atomicstrata.ai

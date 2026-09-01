# Memrank

> An instrument for measuring AI memory engines -- on your own machine, on your own data,
> under a configuration you can read and a result you can re-run.

**Status:** v0.2, in active development. Interfaces still move between releases.

Memrank runs a memory engine against a task set and emits a number with everything needed to
re-run it attached: the configuration, the dataset version, the model, the seed, and the
version of the instrument itself. It measures **quality, latency, cost, and token
efficiency** in one pass.

## Install

Memrank is not on PyPI yet. Install the CLI from the repository:

```bash
uv tool install --force --refresh git+https://github.com/atomicstrata/memrank
memrank --version
```

`--force --refresh` is also the upgrade command, which is why there is only one to remember.
If you do not have [uv](https://docs.astral.sh/uv/): `curl -LsSf https://astral.sh/uv/install.sh | sh`.

Working on memrank itself? Clone it and see [Local development](docs/local-development.md).
Full install detail, including PATH and MCP setup: **[Installing memrank](docs/install.md)**.

## Run something in one minute

`demo` is a small synthetic benchmark that ships with the repository, and `word-overlap` is a
trivial in-process retriever. Together they need no engine, no network, and no API key:

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
memrank targets ls          # what can be evaluated (mem0, atomicmemory, word-overlap, ...)
memrank evals ls            # what to evaluate against (locomo, beam, longmemeval, demo, ...)
memrank targets show mem0   # the exact composition, and ✔/✘ per secret it needs
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
export MEM0_HTTP_URL=http://localhost:8888
memrank submit mem0 locomo:smoke --on none
```

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

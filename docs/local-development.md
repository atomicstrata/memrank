# Local development

Working **on** memrank, rather than with it. If you only want to run evaluations, install the CLI
instead -- see [installing memrank](install.md).

memrank uses Python 3.12 locally and [uv](https://docs.astral.sh/uv/) for interpreter, environment
and dependency management. Run every command from the repository root.

## Set up the environment

```bash
git clone https://github.com/atomicstrata/memrank
cd memrank
uv sync --extra dev
```

`uv sync --locked --extra dev` installs the exact versions in `uv.lock` and fails rather than
resolving anything fresh. Use it when you want this repository's resolution rather than today's:
reproducing a published result, or bisecting a failure that may be a dependency's.

`.python-version` pins the local interpreter to 3.12 and uv installs it if the machine has none.
**Python 3.10 is the supported floor** -- `pyproject.toml` declares `requires-python = ">=3.10"`
and mypy targets 3.10 -- so a change that needs a newer language feature is a change to that floor,
not a local decision.

Optional extras, each added to the same environment:

```bash
uv sync --extra dev --extra mem0          # the Mem0 SDK, for the SDK-backed adapter path
uv sync --extra dev --extra benchmarks    # dataset loaders
uv sync --extra dev --extra mcp           # the MCP server (`memrank-mcp`)
```

## Run the CLI from the checkout

```bash
uv run memrank --help
uv run memrank targets ls
uv run memrank evals ls
```

`uv run memrank` runs the console script inside the synced environment, so it always reflects the
working tree. `uv run python -m memrank.runner --help` is equivalent and is what to reach for when
you need to be certain no installed copy is shadowing the checkout.

To get `memrank` on your PATH pointing at the working tree instead:

```bash
uv tool install --editable .
```

Code edits then apply immediately; changing *dependencies* needs a re-install.

## Run a benchmark

The synthetic `demo` benchmark and the in-process `word-overlap` target need no backend, no
network and no API key -- this is the sanity check to run after any change to the evaluation loop:

```bash
uv run python -m memrank.runner submit word-overlap demo
```

For live engine runs, start the target backend first and set its URL if it differs from the
default:

```bash
export ATOMICMEMORY_API_URL=http://localhost:3070
export MEM0_HTTP_URL=http://localhost:8888
export HINDSIGHT_API_URL=http://localhost:7000
export SUPERMEMORY_BASE_URL=http://localhost:6767

uv run memrank submit atomicmemory locomo:smoke --on none
```

`--on local` provisions a disposable, isolated stack per run from the target's manifest instead,
which needs Docker. `memrank targets show <ref>` prints the composition and marks ✔/✘ per secret
before anything is spent.

Judged runs send benchmark content to Anthropic:

```bash
export ANTHROPIC_API_KEY=...
uv run memrank submit atomicmemory beam:100k-smoke --judge
```

Datasets download on first use and cache under `MEMRANK_CACHE_DIR`. Each loader also honours a
local path override -- `LOCOMO_DATA_PATH`, `BEAM_DATA_PATH`, `LONGMEMEVAL_DATA_PATH`,
`DEMO_DATA_PATH` -- so you can point one at a copy you already have.

Run output lands under `results/`, which is gitignored.

## Tests and checks

Three commands gate a change. Run them before you hand anything off:

```bash
uv run pytest
uv run ruff check .
uv run mypy memrank
```

Tests that need a live memory engine skip when none is running; that is expected, and static
adapter conformance still has to pass. During iteration, run the focused suite for what you
touched rather than the whole thing:

| You changed | Run |
|---|---|
| an adapter, or the adapter registry | `uv run pytest tests/live/conformance/test_adapter_contract.py` |
| latency or token collection | `uv run pytest tests/instrumentation/` |
| the CLI or the runner | `uv run pytest tests/cli/test_runner_help.py`, plus the command by hand |
| judging | `uv run pytest tests/judging/` |
| documentation | `uv run pytest tests/repo/test_doc_links.py tests/repo/test_docs_teach_the_current_cli.py` |
| a core contract in `memrank/core.py` | everything |

The two documentation gates are worth knowing about before they fail on you.
`tests/repo/test_doc_links.py` asserts that every relative markdown link resolves.
`tests/repo/test_docs_teach_the_current_cli.py` walks every command in every doc and script and fails
if one teaches a flag or verb the CLI has retired -- so a doc cannot go on telling a reader to type
something that exits 2.

## Where things live

```
memrank/
├── core.py ............ the contracts: Document, AdapterResponse, BenchmarkUnit,
│                        MemoryAdapter, Benchmark
├── runner.py .......... the Typer CLI's entry point
├── cli/ ............... one module per CLI noun (auth, runs, secrets, targets, ...)
├── adapters/ .......... memory-engine adapters and the adapter REGISTRY
├── benchmarks/ ........ dataset loaders, scorers, and the benchmark REGISTRY
├── evaluation/ ........ the pure evaluation loop
├── orchestration/ ..... a run's lifecycle around that loop
├── instrumentation/ ... latency and token collectors
├── judging/ ........... LLM-as-judge: scorer, client, versioned prompts
├── metrics/ ........... judge-free scoring arithmetic
├── provenance/ ........ reproducibility receipts
├── targets/ ........... what is under test -- the named compositions
├── placement/ ......... where it runs -- none / local / cloud
└── term/ .............. terminal output, formatting, progress
```

Each package's `__init__.py` says what belongs in it and what does not. Read that before adding a
module.

`tests/live/conformance/test_adapter_contract.py` is the suite every registered adapter must satisfy.
`publish.toml` classifies every path public or internal, and `tests/repo/test_public_boundary.py`
checks that classification holds -- which is why this repository can verify its own boundary rather
than asking you to trust that someone did.

## Adding something

- **An engine, without touching memrank at all** -- write a translator that speaks the
  [adapter contract](adapter-contract.md) over HTTP, in any language.
  [`examples/native-adapter/`](../examples/native-adapter/README.md) is a working one.
- **An in-tree adapter** -- [adding an adapter](adding-adapters.md).
- **A benchmark** -- [adding a benchmark](adding-benchmarks.md).

A change that affects how anything is scored needs a matching change to
[methodology.md](methodology.md). That is not a review preference: a
scoring change nobody can see in the documentation is the failure mode this instrument exists to
rule out.

## Why this repository carries the program that produces it

`tools/` is the projector. `publish.toml` classifies every path in the source repository as public
or internal, and `python -m tools.project --out <dir> --rev <sha>` writes the public tree from a
committed revision. Both ship deliberately, in the manner of Google's Copybara: the boundary is
data a reader can inspect rather than a claim they have to take on faith, and
`tests/repo/test_public_boundary.py` and `tests/repo/test_projection.py` re-check it here, in the published
tree, against the same rules. A repository that cannot verify its own boundary is one nobody
checks after the split.

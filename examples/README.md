# Memrank examples

Runnable scripts that demonstrate the most common Memrank workflows. Run each from the repository
root.

| File | What it shows | Needs |
| --- | --- | --- |
| [`explore-benchmark.py`](explore-benchmark.py) | Load one benchmark and look at it -- no runs, nothing written. | nothing |
| [`run-existing-target.py`](run-existing-target.py) | Evaluate a catalog target from a script, resolving the ref exactly as `memrank submit` does. | nothing |
| [`custom-engine.py`](custom-engine.py) | Wire your own engine into the eval loop -- six methods, no registration. | nothing |
| [`custom-benchmark.py`](custom-benchmark.py) | Wire your own benchmark in -- three methods, no registration. | nothing |
| [`custom-target/`](custom-target/README.md) | Register an engine memrank does not ship, so `memrank submit` drives it like any other target. | nothing |
| [`3-line-example.py`](3-line-example.py) | The smallest real run: one adapter, one benchmark, smoke slice. | a live engine |
| [`native-adapter/`](native-adapter/README.md) | A translator: the adapter contract over HTTP, in any language, without touching memrank. | nothing |

Everything except `3-line-example.py` uses `demo`, which ships with the repository, so they run
offline and instantly.

## Prerequisites

```bash
uv sync --extra dev          # from the repository root
uv run python examples/explore-benchmark.py
```

Or, with memrank already installed as a tool (see [installing memrank](../docs/install.md)),
`python examples/explore-benchmark.py` works directly.

`3-line-example.py` needs a backend for the adapter it evaluates:

- **AtomicMemory:** `ATOMICMEMORY_API_URL` (default `http://localhost:3070`)
- **Mem0 OSS:** `MEM0_HTTP_URL` (default `http://localhost:8888`), or the `mem0ai` SDK installed
- **Hindsight:** `HINDSIGHT_API_URL` (default `http://localhost:7000`)

If a backend is not reachable, the example fails with a clear connection error -- memrank does not
silently fall back.

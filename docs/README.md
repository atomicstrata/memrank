---
status: active
last_reviewed: 2026-08-31
---

# Documentation

Everything memrank documents about itself, in reading order. The repository-root
[README](../README.md) is the shorter introduction; this page is the map.

## Start here

| | |
|---|---|
| [Installing memrank](install.md) | install the CLI, run something, connect an agent |
| [Methodology](methodology.md) | the four axes, the context-budget control, the control arms, evidence classes |
| [Engine images](engine-images.md) | per target: whether you can obtain the engine, and what to run when you cannot |
| [SPEC.md](SPEC.md) | the specification: what memrank measures, what it refuses to claim, and the governance the maintainer commits to |

## Contributing

| | |
|---|---|
| [Local development](local-development.md) | environment, the test suite, the checks a change has to pass |
| [Adapter contract](adapter-contract.md) | what an engine must implement to be measurable, in full |
| [Adding an adapter](adding-adapters.md) | run your own engine by passing the instance; registration when it needs a name |
| [Adding a benchmark](adding-benchmarks.md) | run your own eval by passing the instance; loaders, scorers, registration |
| [Runnable examples](../examples/README.md) | the library API, a custom engine, a custom benchmark, and wiring in a target memrank does not ship |

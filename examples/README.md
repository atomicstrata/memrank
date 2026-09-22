# Memrank examples

One folder per thing a person does, in the order the value appears. Each holds a short `run.py`
and a README of a few lines saying what it shows and what it prints. Open 01, run it, and read a
number with its measure and its decider; every folder after that adds one idea.

Run them from the repository root, or from inside any one of the folders -- nothing depends on
where you start:

```bash
uv sync --extra dev
uv run python examples/01-first-result/run.py
```

| Folder | | Needs |
| --- | --- | --- |
| [`01-first-result/`](01-first-result/README.md) | A system memrank ships, on the evaluation memrank ships. Values, with their measures and deciders. | nothing |
| [`02-your-own-system/`](02-your-own-system/README.md) | A memory of your own, in the four verbs its kind requires. | nothing |
| [`03-your-own-evaluation/`](03-your-own-evaluation/README.md) | Your own tasks and context, measured by a measure memrank ships. | nothing |
| [`04-your-own-measure/`](04-your-own-measure/README.md) | A measure you wrote, applied to a saved result loaded back. Nothing reruns. | nothing |
| [`05-against-a-baseline/`](05-against-a-baseline/README.md) | A system against the no-context and full-context controls, paired. | nothing |
| [`06-new-version-vs-old/`](06-new-version-vs-old/README.md) | Two versions of your own system, paired: gap, flips, caution. | nothing |
| [`07-against-a-known-engine/`](07-against-a-known-engine/README.md) | Your system against an engine you did not write, paired. | nothing |

Everything above runs offline, against evaluations that ship with the repository. Nothing
downloads a dataset, calls a paid API, or needs a key.

Each `run.py` is self-contained: it imports `memrank` and nothing else of this repository, so
you can copy one into your own project and it runs there. What that costs is a little
duplication between folders, which is the price of being able to read any one of them on its
own. Nothing formats a result: what a folder prints is what `print()` on memrank's own result
and paired-reading objects produces.

[`more/`](more/README.md) is not a step in the walk and is not core: it keeps the material
that drives memrank's previous run loop -- the one
[the command line](../docs/misc/command-line.md) calls, with its older vocabulary of *target*
for a named system -- or that needs a live engine or Docker.

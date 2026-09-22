# Installing memrank

Memrank is a Python package. This page adds it to a project, runs one evaluation and checks the
[result](reference/result.md). Installing needs the network; the run after it needs no network,
no API key and no running service.

This page is written to be followed by a coding agent as well as by a person. An agent should do
the steps in order, stop at the first failure, and report what it saw.

## 1. Prerequisites

- **[uv](https://docs.astral.sh/uv/), or pip into a virtualenv.** `uv --version` says whether uv
  is there. If it is not: `curl -LsSf https://astral.sh/uv/install.sh | sh` on macOS or Linux.
- **Python 3.10 or newer.** uv installs one itself, so with uv there is nothing to check. With
  pip, check the interpreter of the virtualenv you are installing into: `python -V`.
- **On macOS, `/usr/bin/python3` is Python 3.9**, which is below the floor. Installing into it
  fails with `Could not find a version that satisfies the requirement memrank (from versions:
  none)`. The package exists; the interpreter is too old. Use uv, or make a virtualenv with
  Python 3.10 or newer: `python3.12 -m venv .venv`.
- **A project to install into.** If you have none, `uv init memrank-try` makes one in a new
  directory.

## 2. Install

```bash
uv add memrank                  # or, into a virtualenv you already have: pip install memrank
```

## 3. Run the quick-start evaluation

Save this as `first_run.py`:

```python
from memrank.evaluations import SQuAD
from memrank.systems import TFIDF

evaluation = SQuAD()
result = evaluation.run(system=TFIDF())

print(result)
```

Run it with `uv run python first_run.py`, or with `python first_run.py` in the virtualenv you
installed into.

[`TFIDF`](systems/tfidf.md) is keyword search weighted by how rare each word is.
[`SQuAD`](evaluations/squad.md) is 64 questions about 32 passages bundled with the package. It
measures full-passage retrieval recall, not answer-span or end-to-end answer correctness.

## 4. What done looks like

The run prints a `system:` line naming `TFIDF`, an `evaluation:` line naming `squad` with 64
tasks, the measured values, and a `traces:` line reading `64 recorded, 0 with errors`. That is
the whole check. An agent reports the `system:`, `evaluation:` and `traces:` lines, and nothing
else.

[`memrank.catalog()`](reference/catalog.md) lists every system and evaluation installed, and what
each one needs.

## What not to do

- Do not install memrank globally as a command-line tool. It is a library, and this page installs
  it into one project. The `memrank` command is documented in
  [the command line](misc/command-line.md).
- Do not edit shell configuration, PATH or any file outside the project.
- Do not work around a failure. Stop at it, show the error text in full, and ask. Every message
  memrank prints is written to name the fix; one that does not is itself worth reporting.

## Upgrading

```bash
uv lock --upgrade-package memrank && uv sync      # or: pip install --upgrade memrank
```

This prints the installed version:

```python
import memrank

print(memrank.__version__)
```

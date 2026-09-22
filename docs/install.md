# Installing memrank

Memrank is a Python package: you add it to a project, and a few lines later you have a
[result](reference/result.md). Nothing on this page needs a running engine, a network or an API
key.

This page is written to be followed by a coding agent as well as by a person. An agent should do
the steps in order, stop at the first failure, and report what it saw.

## 1. Prerequisites

- **[uv](https://docs.astral.sh/uv/), or pip into a virtualenv.** `uv --version` says whether uv
  is there. If it is not: `curl -LsSf https://astral.sh/uv/install.sh | sh` on macOS or Linux.
- **Python 3.10 or newer.** `uv` installs one itself, so with uv there is nothing to check. With
  pip, check the interpreter of the virtualenv you are installing into: `python -V`.
- **On macOS, `/usr/bin/python3` is Python 3.9** and is below the floor. Installing into it fails
  with `Could not find a version that satisfies the requirement memrank (from versions: none)`,
  which reads as though the package does not exist. It does; that interpreter is too old. Use uv,
  or make a virtualenv with a 3.10-or-newer interpreter: `python3.12 -m venv .venv`.
- **A project to install into.** `uv init memrank-try` makes one in a new directory if there is
  none yet.

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
installed into. [`TFIDF`](systems/tfidf.md) is keyword search weighted by how rare each word is,
and [`SQuAD`](evaluations/squad.md) is 64 questions about 32 bundled passages, so this needs
nothing beyond what you just installed. It measures full-passage retrieval recall, not
answer-span or end-to-end answer correctness.

## 4. What done looks like

The run prints a `system:` line naming `TFIDF`, an `evaluation:` line naming `squad` with 64
tasks, one line per value, and a `traces:` line reading `64 recorded, 0 with errors`. That is the
whole of the check. An agent reports those two heading lines and the traces line back, and
nothing else.

## What not to do

- Do not install memrank globally as a command-line tool. It is a library, and this page installs
  it into one project.
- Do not edit shell configuration, PATH or any file outside the project.
- Do not work around a failure. Stop at it, show the error text in full, and ask. Every message
  memrank prints is written to name the fix; one that does not is itself worth reporting.

## Upgrading

```bash
uv lock --upgrade-package memrank && uv sync      # or: pip install --upgrade memrank
```

```python
import memrank

print(memrank.__version__)
```

## What else ships

[`memrank.catalog()`](reference/catalog.md) prints every system and evaluation installed, with
what each one needs, so you do not have to know a name to find one. The engine-backed systems
take a `base_url=` (and `api_key=` where the engine authenticates) where `WordOverlap()` goes,
and each reads its own environment variable when the argument is left out. Which engine images
you can obtain at all differs per engine: [engine images](misc/engine-images.md) says which.

## Working on memrank itself

The repository is public, so a checkout needs no credential:

```bash
git clone https://github.com/atomicstrata/memrank
cd memrank
uv sync --extra dev
```

[Local development](local-development.md) has the tests and the rest of the loop. To use an
unreleased memrank from a project of your own, add the checkout instead of the package:
`uv add --editable ../memrank`.

## The command line

Memrank ships a `memrank` command as well, and it is not core: nothing above needs it, and it
keeps an older vocabulary of its own. [The command line](misc/command-line.md) is where it lives,
along with the tool install that puts it on your PATH, tracked runs, the hosted platform and the
MCP server.

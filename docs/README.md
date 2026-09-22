---
status: active
last_reviewed: 2026-09-21
---

# Documentation

Memrank is a Python package: you put an **evaluation** to a **system** -- `evaluation.run(system=...)`
-- and get back a **result** whose values each name the **measure** that produced them and who
decided them. Everything below is in reading order.

## The entry path

Read in this order. Every page here leads with Python, and none of them needs the command line to
reach a number.

| | |
|---|---|
| [README](../README.md) | what memrank is, and a first result in a few lines of Python |
| [Reference](reference/README.md) | one page per word -- system, evaluation, task, trace, measure, run, result -- each opening with a concrete instance |
| [Installing memrank](install.md) | add the package to a project, import it, and print a result; upgrading |
| [The systems that ship](systems/README.md) | one page per shipped system: what it is, how it works, why it matters, what it needs |
| [The evaluations that ship](evaluations/README.md) | one page per shipped evaluation, to the same standard, including whether its quality number needs a judge |
| [Adding a system](systems.md) | bring the thing under test: the kinds, the verbs each requires, and running yours without naming it |
| [The system contract](system-contract.md) | the wire contract for a system memrank drives as a process rather than imports, in any language |
| [Adding an evaluation](evaluations.md) | bring your own tasks and the rule for when the system's state is cleared |
| [Measures](measures.md) | the measure contract: what a measure reads, who decides, and measuring stored traces afterwards |
| [Runnable examples](../examples/README.md) | one folder per thing a person does, from a first result to two systems read as a pair |
| [Methodology](methodology.md) | what each shipped measure actually measures, the context budget, the control arms, and what a value licenses you to say |
| [SPEC.md](SPEC.md) | the specification: what memrank measures, what it refuses to claim, and the governance the maintainer commits to |

## Not core: the command line and the catalog

This is not the entry path. Memrank's interface is the Python package; the pages below describe an
older surface that is kept working but not developed, and they keep its own older vocabulary --
*target*, *eval*, *adapter*, *benchmark* -- because those names are on the wire and in stored
artifacts. Reach for it only when you want a run tracked, placed or named.

| | |
|---|---|
| [The command line](misc/command-line.md) | the whole command surface: submitting a run, watching it, listing runs, targets, evals, secrets, config |
| [Engine images](misc/engine-images.md) | per catalog target: whether you can obtain the container, and what to run when you cannot |
| [Wiring in a custom target](../examples/more/custom-target/README.md) | registering a system in the catalog so the command line can drive it by name |

## Working on memrank itself

| | |
|---|---|
| [Local development](local-development.md) | environment, the smoke run, the suites, the checks a change has to pass |
| [The test tree](../tests/README.md) | where a new test file goes, by subsystem |

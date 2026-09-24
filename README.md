# Memrank

[![PyPI release](https://img.shields.io/pypi/v/memrank)](https://pypi.org/project/memrank/)
[![Code license: Apache-2.0](https://img.shields.io/badge/license-Apache--2.0-blue)](https://github.com/atomicstrata/memrank/blob/main/LICENSE)

**Status:** v0.4, in active development. Interfaces still move between releases.

Memrank is a tool for reproducible, auditable evaluation of memory systems.

Compare memory systems and their versions on tasks that matter to your agent or application.
You choose the tasks and success criteria; Memrank runs the evaluation, reports scores and timings,
and records responses and errors so you can investigate differences.

[Start here](https://github.com/atomicstrata/memrank/blob/main/docs/getting-started.md) |
[Compare memory systems and their versions](https://github.com/atomicstrata/memrank/blob/main/docs/comparing.md) |
[Understand results](https://github.com/atomicstrata/memrank/blob/main/docs/results.md)

## Quick start

Check the installation with a small local retrieval evaluation. Installation needs the network;
the Python block below needs no key, service or network. This checks that Memrank works in your
project; it does not establish how a memory system will perform on your workload.

### Do it yourself

Use Python >= 3.10 and an existing project or virtualenv.
[Installation instructions](https://github.com/atomicstrata/memrank/blob/main/docs/install.md)
cover creating one.

```bash
uv add memrank                  # or, into a virtualenv you already have: pip install memrank
```

```python
from memrank.evaluations import SQuAD
from memrank.systems import TFIDF

evaluation = SQuAD()
result = evaluation.run(system=TFIDF())

print(result)
```

[`TFIDF`](https://github.com/atomicstrata/memrank/blob/main/docs/systems/tfidf.md) is keyword search
weighted by how rare each word is.
[`SQuAD`](https://github.com/atomicstrata/memrank/blob/main/docs/evaluations/squad.md) supplies
32 bundled passages and 64 questions. The `squad-score` measures full-passage retrieval recall,
not answer-span or end-to-end answer correctness. Check that the output names the expected system
and evaluation and says `64 recorded, 0 with errors`.
[Read the output](https://github.com/atomicstrata/memrank/blob/main/docs/getting-started.md#read-the-installation-check).

Or paste this to your coding agent:

```text
Install memrank in this project and run its smoke evaluation, following
https://github.com/atomicstrata/memrank/blob/main/docs/install.md. Check the prerequisites
that page lists before you change anything, install into this project only, and do not
install anything globally or edit my shell configuration. When the run finishes, show me the
`system:`, `evaluation:` and `traces:` lines it printed. Stop and ask me if any step fails.
```

## Use cases

<a id="compare-two-systems"></a>
### Compare two memory systems

Run candidates on the same evaluation, inspect coverage and failures, and read each measure's
meaning before interpreting a gap. The [memory systems comparison guide](https://github.com/atomicstrata/memrank/blob/main/docs/comparing.md)
shows how to read the differences, with an offline toy example of task-level pairing.
It also explains when to compare summaries: `memrank.paired` does not compare aggregate
scores such as `squad-score`.

<a id="evaluate-a-system-of-your-own"></a>
### Evaluate a memory system of your own

Use a [shipped client](https://github.com/atomicstrata/memrank/blob/main/docs/systems/README.md)
or [connect your own system](https://github.com/atomicstrata/memrank/blob/main/docs/systems.md).
A memory implements `prepare`, `ingest`, `retrieve` and `cleanup` so Memrank can give it context,
ask questions and clear state between independent cases. An external
[engine](https://github.com/atomicstrata/memrank/blob/main/docs/reference/system.md#system-and-engine)
may need a configured service and credentials.

### Ask your own questions

[Express your evaluation](https://github.com/atomicstrata/memrank/blob/main/docs/evaluations.md)
as tasks, expected outcomes and measures. You decide which cases represent your problem and what
counts as success; Memrank applies those rules and records the evidence.

### Find out why a value is what it is

[Understand results](https://github.com/atomicstrata/memrank/blob/main/docs/results.md) shows how
to inspect a task's trace, distinguish missing values from zero, and save a result for later use.
[Write a measure](https://github.com/atomicstrata/memrank/blob/main/docs/measures.md) to read
something new from stored traces without rerunning the system.

### Check the instrument

[Control examples](https://github.com/atomicstrata/memrank/blob/main/examples/05-against-a-baseline/README.md)
show what happens when retrieval returns no documents or all documents. These checks help expose
what a measure rewards; they do not prove that the evaluation represents your workload.
[Methodology](https://github.com/atomicstrata/memrank/blob/main/docs/methodology.md) states the
measurement rules and limits on claims.

## Where to read more

| Guide | Task |
|---|---|
| [Start here](https://github.com/atomicstrata/memrank/blob/main/docs/getting-started.md) | Start using Memrank |
| [Memory systems comparison guide](https://github.com/atomicstrata/memrank/blob/main/docs/comparing.md) | Compare memory systems or their versions |
| [Understand results](https://github.com/atomicstrata/memrank/blob/main/docs/results.md) | Interpret and save measurements |
| [Systems](https://github.com/atomicstrata/memrank/blob/main/docs/systems/README.md) | Find available integrations |
| [Evaluations](https://github.com/atomicstrata/memrank/blob/main/docs/evaluations/README.md) | Find available task sets |
| [Reference](https://github.com/atomicstrata/memrank/blob/main/docs/reference/README.md) | Look up Python contracts |
| [Documentation index](https://github.com/atomicstrata/memrank/blob/main/docs/README.md) | Find every guide |

The guides above use Python. Memrank also provides a
[command line](https://github.com/atomicstrata/memrank/blob/main/docs/misc/command-line.md) for
tracked and placed runs, and a
[translator contract](https://github.com/atomicstrata/memrank/blob/main/docs/system-contract.md)
for memory systems implemented in other languages.

## Help and contribution

[Contributing and getting help](https://github.com/atomicstrata/memrank/blob/main/docs/contributing.md)
links the issue tracker and development checks. Questions about your setup are easier to reproduce
with the package version, a small example and the error text. Do not include keys or private data.

## Governance

Memrank is maintained by [AtomicStrata](https://atomicstrata.ai) under a vendor-neutral charter:
anyone may submit a system, results are published as measured, and methodology changes go through
public proposal and comment. The commitments are in
[SPEC.md section 7](https://github.com/atomicstrata/memrank/blob/main/docs/SPEC.md#7-governance----the-vendor-neutral-charter).
AtomicStrata also develops AtomicMemory, one of the engines Memrank can evaluate. Comparisons
should be assessed through their method, configuration and recorded evidence.

## Licences

Memrank's code is [Apache-2.0](https://github.com/atomicstrata/memrank/blob/main/LICENSE).
The bundled SQuAD subset is [CC BY-SA 4.0](https://creativecommons.org/licenses/by-sa/4.0/);
its [notice](https://github.com/atomicstrata/memrank/blob/main/memrank/benchmarks/data/SQUAD-NOTICE.md)
credits the creators and passage sources and records the selection and reformatting.

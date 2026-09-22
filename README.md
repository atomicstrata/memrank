# Memrank

Memrank is a tool for reproducible, auditable evaluation of memory systems.

**Status:** v0.4, in active development. Interfaces still move between releases.

## Quick start

Paste this to your agent, and it installs memrank and runs the evaluation below for you:

```text
Install memrank in this project and run its smoke evaluation, following
https://github.com/atomicstrata/memrank/blob/main/docs/install.md. Check the prerequisites
that page lists before you change anything, install into this project only, and do not
install anything globally or edit my shell configuration. When the run finishes, show me the
`system:` and `evaluation:` lines it printed. Stop and ask me if any step fails.
```

### Do it yourself

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
weighted by how rare each word is, and it ships with the package.
[`SQuAD`](https://github.com/atomicstrata/memrank/blob/main/docs/evaluations/squad.md) supplies
32 bundled passages and 64 questions. This measures full-passage retrieval recall, not
answer-span or end-to-end answer correctness. Neither needs an
[engine](https://github.com/atomicstrata/memrank/blob/main/docs/reference/system.md#system-and-engine),
a key or the network.
[Installing memrank](https://github.com/atomicstrata/memrank/blob/main/docs/install.md) covers uv,
Python versions and upgrading.

## Use cases

Each snippet below runs on its own.

### Evaluate a system of your own

Four methods, and the
[system](https://github.com/atomicstrata/memrank/blob/main/docs/reference/system.md) is ready to
evaluate. A memory engine you already run has a client that ships with memrank instead --
`AtomicMemory`, `Hindsight`, `Mem0` and `Supermemory` take a `base_url=` where `NoteBook()` goes
below, and [adding a system](https://github.com/atomicstrata/memrank/blob/main/docs/systems.md) is
the rest.

```python
from memrank import Memory, Recall
from memrank.evaluations import Demo


class NoteBook(Memory):
    name, version, engine_version = "notebook", "0.1", "0.1"

    def prepare(self, isolation_unit):
        self.notes = []

    def ingest(self, documents):
        self.notes.extend(documents)

    def retrieve(self, query, k, user_id, query_timestamp=None) -> Recall:
        wanted = set(query.lower().split())
        ranked = sorted(self.notes, reverse=True,
                        key=lambda note: len(wanted & set(note.content.lower().split())))
        return Recall(documents=ranked[:k])

    def cleanup(self):
        self.notes = []


result = Demo().run(system=NoteBook())
```

### Ask your own questions

An [evaluation](https://github.com/atomicstrata/memrank/blob/main/docs/reference/evaluation.md) you
write by hand and one that ships are the same object:
[tasks](https://github.com/atomicstrata/memrank/blob/main/docs/reference/task.md), the
[measures](https://github.com/atomicstrata/memrank/blob/main/docs/measures.md) that read them, and
when the system is cleared.

```python
from memrank import Clearing, Document, Evaluation, Expected, Task, WordMatch
from memrank.systems import WordOverlap

notes = (Document(id="t1", user_id="acme",
                  content="Acme moved to the enterprise plan in March."),)

tickets = Evaluation(
    name="tickets", version="internal@2026-09",
    tasks=(Task(id="q_plan", prompt="What plan is Acme on?", group="acme", context=notes,
                expected=Expected(required_spans=("enterprise",), evidence_doc_ids=("t1",))),),
    measures=(WordMatch(),), clearing=Clearing.PER_GROUP)

result = tickets.run(system=WordOverlap())
```

### Find out why a value is what it is

Every [value](https://github.com/atomicstrata/memrank/blob/main/docs/reference/result.md) names the
task it came from, and every task kept its
[trace](https://github.com/atomicstrata/memrank/blob/main/docs/reference/trace.md) -- what was
asked, what the evaluation wanted, what came back.

```python
from memrank.evaluations import Demo
from memrank.systems import WordOverlap

result = Demo().run(system=WordOverlap())

lowest = min(result.values_of("word-match"), key=lambda value: value.value or 0.0)
trace = result.traces_of(lowest.task_id)[0]

print(lowest.value, lowest.why)
print(trace.task.prompt, trace.task.expected.required_spans)
for document in trace.recalled.documents:
    print(document.id, document.content)
```

### Compare two systems

[`memrank.paired`](https://github.com/atomicstrata/memrank/blob/main/docs/reference/paired.md)
refuses two results of different evaluations, then reads them task by task and says how often chance
alone produces a gap that size. It never says "better".

```python
import memrank
from memrank.evaluations import Demo
from memrank.systems import NoContext, WordOverlap

evaluation = Demo()

print(memrank.paired(evaluation.run(system=WordOverlap()),
                     evaluation.run(system=NoContext())))
```

### Check the instrument

`NoContext` is the floor: it retrieves nothing. `FullContext` is the ceiling: it is given every
document, unranked. A gap between them is what makes the evaluation worth running at all, and
[methodology](https://github.com/atomicstrata/memrank/blob/main/docs/methodology.md) states what a
value does and does not license you to say.

```python
from memrank.evaluations import Demo
from memrank.systems import FullContext, NoContext, WordOverlap

evaluation = Demo()

for system in (NoContext(), WordOverlap(), FullContext()):
    result = evaluation.run(system=system)
    scored = [value.value for value in result.values_of("word-match")
              if value.value is not None]
    print(result.system.name, sum(scored) / len(scored))
```

## Where to read more

| | |
|---|---|
| [Systems](https://github.com/atomicstrata/memrank/blob/main/docs/systems/README.md) | one page per system memrank ships, and what each one needs |
| [Evaluations](https://github.com/atomicstrata/memrank/blob/main/docs/evaluations/README.md) | one page per evaluation, its tasks and what it measures |
| [Reference](https://github.com/atomicstrata/memrank/blob/main/docs/reference/README.md) | one page per word in the Python surface |
| [Measures](https://github.com/atomicstrata/memrank/blob/main/docs/measures.md) | what a scoring rule declares, and the ones memrank ships |
| [Methodology](https://github.com/atomicstrata/memrank/blob/main/docs/methodology.md) | the axes, the budget control, the control arms, evidence classes |
| [Installing memrank](https://github.com/atomicstrata/memrank/blob/main/docs/install.md) | prerequisites, install, a smoke run, upgrading |
| [Local development](https://github.com/atomicstrata/memrank/blob/main/docs/local-development.md) | working on memrank itself |
| [SPEC.md](https://github.com/atomicstrata/memrank/blob/main/docs/SPEC.md) | what memrank evaluates, and the governance it commits to |

Memrank ships a `memrank` command as well, and it is not core: nothing above needs it, and it keeps
an older vocabulary of its own --
[the command line](https://github.com/atomicstrata/memrank/blob/main/docs/misc/command-line.md) is
where it lives.

## Governance

Memrank is maintained by [AtomicStrata](https://atomicstrata.ai) under a vendor-neutral charter:
anyone may submit a system, results are published as measured, and methodology changes go through
public proposal and comment. The commitments are in
[SPEC.md section 7](https://github.com/atomicstrata/memrank/blob/main/docs/SPEC.md#7-governance----the-vendor-neutral-charter).
AtomicStrata
also ships a memory engine, AtomicMemory, which this tool evaluates and which has placed below a
no-memory control arm in our own runs -- which is why the floor and the ceiling above are in the
package rather than in a report of ours.

## Licences

Memrank's code is [Apache-2.0](https://github.com/atomicstrata/memrank/blob/main/LICENSE).
The bundled SQuAD subset is [CC BY-SA 4.0](https://creativecommons.org/licenses/by-sa/4.0/);
its [notice](https://github.com/atomicstrata/memrank/blob/main/memrank/benchmarks/data/SQUAD-NOTICE.md)
credits the creators and passage sources and records the selection and reformatting.

Methodology questions and disagreements: open an issue. Anything else: hello@atomicstrata.ai

# evaluation

An **evaluation** is a set of questions and the rules for asking them, and it is the object you
call `run(system=...)` on.

```python
from memrank.evaluations import Demo
from memrank.systems import WordOverlap

evaluation = Demo()
print(evaluation.name, evaluation.version, len(evaluation.tasks), "tasks")

result = evaluation.run(system=WordOverlap())
```

[`Demo`](../evaluations/demo.md) is five questions about a short conversation, and needs no
download and no key. [`LoCoMo`, `LongMemEval` and `BEAM`](../evaluations/README.md) are public
benchmarks memrank can download. `tickets` below is one you write yourself.

## What it is

An evaluation is a named, versioned bundle of three things:

1. its **[tasks](task.md)** -- one per thing to put to the system;
2. the **[measures](measure.md)** it ships with. No scoring lives in the evaluation itself;
3. its **clearing rule** -- when the system's state is wiped. Tasks that share state carry the
   same `group`: memrank gives a group's documents once and clears between groups, never inside
   one. `Clearing.PER_GROUP` is that; `Clearing.PER_TASK` and `Clearing.AT_END` are the other
   two.

The version is part of the identity. Two results are comparable only when they are of the same
evaluation at the same version, and [paired](paired.md) refuses when they are not.

## Who supplies what

Memrank ships five evaluations, each bundling its own measures, and enforces the clearing rule
during the run. You supply your own tasks, your own measures, or both -- they are separate
choices, and `memrank.evaluation("demo")` returns exactly the kind of object you would write by
hand.

## The Python names

```python
import memrank
from memrank import Clearing, Document, Evaluation, Expected, Task
from memrank.systems import WordOverlap

notes = (Document(id="t1", user_id="acme",
                  content="Acme moved to the enterprise plan in March."),)

tickets = Evaluation(
    name="tickets", version="internal@2026-09",
    tasks=(Task(id="q_plan", prompt="What plan is Acme on?", group="acme", context=notes,
                expected=Expected(answers=("enterprise",), required_spans=("enterprise",),
                                  evidence_doc_ids=("t1",))),),
    measures=(memrank.WordMatch(),),
    clearing=Clearing.PER_GROUP)

result = tickets.run(system=WordOverlap())
```

- `memrank.Evaluation` -- the class. Fields: `name`, `version`, `tasks`, `measures`,
  `clearing`, `metadata`.
- `evaluation.run(system=...)` -- the [run](run.md), returning a [result](result.md).
- `memrank.Clearing` -- `PER_TASK`, `PER_GROUP`, `AT_END`.
- `memrank.evaluations` -- the module holding what ships: `Demo`, `RelationGraph`, `LoCoMo`,
  `LongMemEval`, `BEAM`.
- `memrank.evaluation("<name>")` -- the same things by string.
- `evaluation.groups()` and `evaluation.group_of(task_id)` -- which tasks share state.

## Going deeper

- [Adding an evaluation](../evaluations.md) -- writing one, and writing only half of one.
- [Evaluations that ship](../evaluations/README.md) -- one page each.
- [Methodology](../methodology.md) -- what the shipped evaluations measure.
- [`examples/03-your-own-evaluation/`](../../examples/03-your-own-evaluation/) -- a working one.

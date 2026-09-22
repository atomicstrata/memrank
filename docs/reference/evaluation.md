# evaluation

## An instance, first

An **evaluation** is a set of questions and the rules for asking them. Concretely:

- `demo`, which ships with the package: five questions about a short conversation between two
  people -- what Alex does for a living, what Alex's favourite animal is, when Dana is
  visiting. Three short documents, five questions, no download, no key;
- `locomo`, `longmemeval` and `beam`, three public benchmarks memrank can download and run;
- `tickets`, which you write yourself in about fifteen lines: your own documents, your own
  questions, and whatever counts as a correct answer to them.

```python
from memrank.evaluations import Demo

evaluation = Demo()
print(evaluation.name, evaluation.version, len(evaluation.tasks), "tasks")
print([task.id for task in evaluation.tasks])
```

```console
demo memrank-demo@v1+def0 5 tasks
['q_job', 'q_animal', 'q_visit', 'q_diet', 'q_allergy_neg']
```

## What it is

An evaluation is a named, versioned bundle of three things:

1. its **[tasks](task.md)** -- one per thing to put to the system;
2. the **[measures](measure.md)** it ships with -- the rules that turn what happened into named
   values. No scoring lives in the evaluation itself; it only bundles measures;
3. its **clearing rule** -- when the system's state is wiped. Tasks that share state carry the
   same `group`: memrank gives a group's documents once and clears between groups, never inside
   one. `Clearing.PER_GROUP` is that; `Clearing.PER_TASK` and `Clearing.AT_END` are the other
   two.

The version is part of the identity. Two results are only comparable when they are of the same
evaluation at the same version, and [paired](paired.md) refuses when they are not.

Memrank's own evaluations and yours are the same kind of object. `memrank.evaluation("demo")`
returns exactly what you would write by hand.

## Who supplies what

| You supply | Memrank supplies |
|---|---|
| your own tasks, if you have them | five evaluations that ship, `Demo` needing nothing at all |
| your own measures, if you have them | the measures each shipped evaluation bundles |
| the clearing rule for an evaluation you write | enforcement of that rule during the run |

Bringing your own questions does not mean writing your own measure, and bringing your own
measure does not mean writing questions. They are separate things on purpose.

## The Python names

```python
import memrank
from memrank import Clearing, Document, Evaluation, Expected, Task

notes = (Document(id="t1", user_id="acme",
                  content="Acme moved to the enterprise plan in March."),)

tickets = Evaluation(
    name="tickets", version="internal@2026-09",
    tasks=(Task(id="q_plan", prompt="What plan is Acme on?", group="acme", context=notes,
                expected=Expected(answers=("enterprise",), required_spans=("enterprise",),
                                  evidence_doc_ids=("t1",))),),
    measures=(memrank.WordMatch(),),
    clearing=Clearing.PER_GROUP)

print(tickets.name, tickets.clearing.value, len(tickets.tasks))
```

```console
tickets per-group 1
```

- `memrank.Evaluation` -- the class. Fields: `name`, `version`, `tasks`, `measures`,
  `clearing`, `metadata`.
- `memrank.Clearing` -- `PER_TASK`, `PER_GROUP`, `AT_END`.
- `memrank.evaluations` -- the module holding what ships: `Demo`, `RelationGraph`, `LoCoMo`,
  `LongMemEval`, `BEAM`.
- `memrank.evaluation("<name>")` -- the same things by string.
- `evaluation.groups()` and `evaluation.group_of(task_id)` -- which tasks share state.

## Going deeper

- [Adding an evaluation](../evaluations.md) -- writing one, and bringing only half of one.
- [`examples/03-your-own-evaluation/`](../../examples/03-your-own-evaluation/) -- a working one.
- [methodology](../methodology.md) -- what the shipped evaluations actually measure.

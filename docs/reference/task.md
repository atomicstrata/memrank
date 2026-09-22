# task

A **task** is one question, the documents the system should have been given before it is asked,
and what a right answer looks like. `q_job`, the first task of
[`demo`](../evaluations/demo.md), asks what Alex does for a living.

```python
from memrank.evaluations import Demo

task = Demo().tasks[0]
print(task.id, "|", task.prompt)
print("group:", task.group, "| context documents:", len(task.context))
print("expected answers:", task.expected.answers)
```

## What it is

A task carries four things that matter:

- **`prompt`** -- what is put to the system.
- **`context`** -- the documents to give it *before* the prompt. Tasks in the same `group` share
  them: memrank gives them once and clears between groups, never inside one. A task with no
  context is asked against whatever the group already established.
- **`group`** -- the state it belongs to, which is what the [evaluation](evaluation.md)'s
  clearing rule acts on.
- **`expected`** -- `answers` are acceptable answers, `required_spans` must appear,
  `forbidden_spans` must not, `evidence_doc_ids` names the documents that hold the answer, and
  `rubric` is prose for a judge to apply.

`expected` is what a task hopes for, not what it scores. Nothing in the task decides anything: a
[measure](measure.md) reads `expected` and decides, and which measure did so is recorded on
every value.

A task with `polarity="negative"` is one whose right answer is a refusal. `q_allergy_neg` asks
whether Alex is allergic to peanuts, and "allergic to peanuts" is its forbidden span.

## Who supplies what

Memrank supplies the tasks of every evaluation that ships, gives the context, puts the prompt,
and records exactly one [trace](trace.md) per task per attempt, including when the task fails.
You supply tasks when you write your own evaluation, and nothing about scoring.

## The Python names

```python
from memrank import Document, Expected, Task

task = Task(id="q_plan", prompt="What plan is Acme on?", group="acme",
            context=(Document(id="t1", user_id="acme",
                              content="Acme moved to the enterprise plan in March."),),
            expected=Expected(answers=("enterprise",), required_spans=("enterprise",),
                              evidence_doc_ids=("t1",)))

print(task.id, task.expected.required_spans, task.expected.polarity)
```

- `memrank.Task` -- fields `id`, `prompt`, `expected`, `group`, `context`, `category`,
  `metadata`.
- `memrank.Expected` -- fields `answers`, `required_spans`, `forbidden_spans`,
  `evidence_doc_ids`, `rubric`, `polarity`.
- `memrank.Document` -- one piece of context: `id`, `content`, `user_id`, `timestamp`,
  `context`, `messages`, `metadata`.

## Going deeper

- [evaluation](evaluation.md) -- the bundle a task belongs to, and its clearing rule.
- [trace](trace.md) -- what is recorded when a task runs.
- [Adding an evaluation](../evaluations.md) -- writing tasks of your own.

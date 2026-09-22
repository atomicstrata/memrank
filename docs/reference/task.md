# task

## An instance, first

A **task** is one question, plus the material the system should have been given before it is
asked, plus what a right answer looks like. Here is one, from the `demo` evaluation that ships
with the package:

- **id** `q_job`
- **prompt** "What is Alex's profession?"
- **context** three short documents -- a conversation in which Alex mentions moving to Portland
  and working as a marine biologist
- **expected** the answer is "marine biologist", the span `marine biologist` should appear, and
  the evidence for it is in the document `sess_1`

```python
from memrank.evaluations import demo

task = demo().tasks[0]
print(task.id, "|", task.prompt)
print("group:", task.group, "| context documents:", len(task.context))
print("expected answers:", task.expected.answers)
```

```console
q_job | What is Alex's profession?
group: demo_alex | context documents: 3
expected answers: ('marine biologist',)
```

## What it is

A task is the unit of asking. It carries four things that matter:

- **`prompt`** -- what is put to the system.
- **`context`** -- the documents to give it *before* the prompt. Tasks in the same `group` share
  that material: memrank gives it once and clears between groups, never inside one. A task with
  no context is asked against whatever the group already established.
- **`group`** -- the state it belongs to, which is what the evaluation's clearing rule acts on.
- **`expected`** -- what a correct outcome looks like. Not one string: `answers` are acceptable
  answers, `required_spans` must appear, `forbidden_spans` must not, `evidence_doc_ids` names
  the documents that actually hold the answer, and `rubric` is prose for a judge to apply.

`expected` is what a task *hopes for*, not what it scores. Nothing in the task decides
anything -- a [measure](measure.md) reads `expected` and decides, and which measure did so is
recorded on every value.

A task with `polarity="negative"` is one whose right answer is a refusal: `q_allergy_neg` asks
whether Alex is allergic to peanuts, and the forbidden span is "allergic to peanuts".

## Who supplies what

| You supply | Memrank supplies |
|---|---|
| tasks, when you write your own evaluation | the tasks of every evaluation that ships |
| the context, the prompt and the expectation | giving the context, putting the prompt, recording what came back |
| nothing about scoring | the measures that read `expected` and decide |

Exactly one [trace](trace.md) is recorded per task per attempt, including when the task fails.

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

```console
q_plan ('enterprise',) positive
```

- `memrank.Task` -- fields `id`, `prompt`, `expected`, `group`, `context`, `category`,
  `metadata`.
- `memrank.Expected` -- fields `answers`, `required_spans`, `forbidden_spans`,
  `evidence_doc_ids`, `rubric`, `polarity`.
- `memrank.Document` -- one piece of context: `id`, `content`, `user_id`, `timestamp`,
  `context`, `messages`, `metadata`.

## Going deeper

- [evaluation](evaluation.md) -- the bundle a task belongs to, and its clearing rule.
- [Adding an evaluation](../evaluations.md) -- writing tasks of your own.
- [trace](trace.md) -- what is recorded when a task runs.

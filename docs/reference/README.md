# Reference: the seven words, one page each

Memrank is a Python package and `memrank.run(system, evaluation)` is its entry point. Seven
words describe everything it does, and two readings sit above them. This folder holds one page
per word. Each page opens with a concrete instance, then says what the word means, then says
who supplies it and what memrank supplies, then names the Python you would type.

Each page stands on its own. You do not have to read them in order, and nothing here assumes
you have read another one.

| Word | What it is | Who supplies it |
|---|---|---|
| [**system**](system.md) | the thing under test. A **memory** is told things and later asked for what is relevant; there are also **model**, **retriever** and **assistant** kinds | you, or memrank |
| [**evaluation**](evaluation.md) | a named, versioned bundle: its tasks, the measures it ships with, and the rule for when the system's state is cleared | either half, from either of you |
| [**task**](task.md) | one thing to put to the system: the context to give it, the prompt, and what a correct outcome looks like | the evaluation |
| [**trace**](trace.md) | everything observed while one task ran. Exactly one per task per attempt, including on failure | memrank |
| [**measure**](measure.md) | a named rule from traces to values, declaring what it reads and who decides: memrank's clock, a fixed rule, a judge model, or the system's own word | the evaluation, or you, afterwards |
| [**run**](run.md) | the act. It refuses *before* touching the system when the run cannot be set up | you compose it at the call |
| [**result**](result.md) | the traces and the values, each value carrying its measure's name and its decider. Never a bare number, and never a verdict | returned to you |

Two readings sit above the seven:

| Reading | What it is |
|---|---|
| [**paired**](paired.md) | `memrank.paired(a, b)` reads two results of the same evaluation side by side. It never says "better" |
| [**catalog**](catalog.md) | `memrank.catalog()` prints every system and every evaluation that ships, so you do not have to know a name to find one |

## Where to go from here

- [The README](../../README.md) -- what memrank is, and a first result.
- [Adding a system](../systems.md) -- bringing your own thing under test.
- [Adding an evaluation](../evaluations.md) -- bringing your own tasks and measures.
- [Methodology](../methodology.md) -- what a number does and does not license you to say.
- [`examples/`](../../examples/README.md) -- one folder per thing a person does.

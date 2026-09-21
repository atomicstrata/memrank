# 03 -- your own evaluation

`uv run python examples/03-your-own-evaluation/run.py`

Your questions, your context. An evaluation is tasks, the measures it ships with, and the rule
for when state is cleared -- the same kind of object `memrank.evaluation("demo")` returns. The
one here is four notes and three tasks, written in the script.

**Prints** values for the three tasks measured by `WordMatch`, then one task's trace: what was
given, what came back, in what order. A trace is where you go when a number surprises you.

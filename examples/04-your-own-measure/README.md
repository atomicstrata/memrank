# 04 -- your own measure

`uv run python examples/04-your-own-measure/run.py`

A measure is a named rule from traces to values, declaring its scope, the trace fields it reads,
and who decides. Scoring is not inside the run loop, so a measure thought of afterwards runs
over traces already stored.

**Prints** the values of a saved result, loaded back from disk the way another process would,
with `passages-recalled` added: how many passages came back for each question. Nothing reran.

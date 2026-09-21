# 01 -- a first result

`uv run python examples/01-first-result/run.py`

A system memrank ships (`WordOverlap`) on the evaluation memrank ships (`demo`), each imported
by name so your editor can follow it to its own definition. No engine, no network, no key,
about a second.

**Prints** the result: which system and which evaluation ran, every value with the measure that
produced it and who decided it, and how many traces were recorded. `word-match` says on its own
face that it is a retrieval proxy, not answer correctness.

`memrank.catalog()` prints everything memrank ships -- the systems under `memrank.systems` and
the evaluations under `memrank.evaluations` -- if you want to see what else there is.
Example 05 opens with it.

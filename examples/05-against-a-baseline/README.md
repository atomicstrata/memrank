# 05 -- against a baseline

`uv run python examples/05-against-a-baseline/run.py`

A score alone says nothing about whether the memory helped. `memrank.system("no-context")` is
told nothing and answers anyway -- the floor. `memrank.system("full-context")` is handed every
document with no retrieval -- the ceiling. `word-overlap` stands in for your system here.

**Prints** `memrank.catalog()` first -- everything memrank ships, so the names below are ones
you have already seen rather than ones you had to know -- then a paired reading against each
control: means, gap, the tasks whose value flipped, and a caution when there is too little to
characterise either. A pairing never says "better".

## Two ways to name a system, and when to use which

Both forms reach the same class, and `memrank.catalog()` prints them side by side.

- **The Python name** -- `from memrank.systems import WordOverlap`, `WordOverlap()`, and
  `from memrank.evaluations import Demo`, `Demo()`. Use it when you are writing code: your
  editor follows it to the definition, hover shows what it needs, and the keyword arguments
  are typed. Example 01 is written this way.
- **The string name** -- `memrank.system("word-overlap")`, `memrank.evaluation("demo")`. Use it
  when the name arrives as data: from a config file, from a command-line argument, from a loop
  over several systems, as here. `memrank.system("atomicmemory", base_url=...)` is also how a
  client for a running service is given its address.

The string form is what the command line and the cloud have, so it is not going anywhere. It
is only the wrong default for the first Python a person writes, because a string is where the
trail stops.

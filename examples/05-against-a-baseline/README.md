# 05 -- against a baseline

`uv run python examples/05-against-a-baseline/run.py`

A score alone says nothing about whether the memory helped. `memrank.system("no-context")` is
told nothing and answers anyway -- the floor. `memrank.system("full-context")` is handed every
document with no retrieval -- the ceiling. `word-overlap` stands in for your system here.

**Prints** a paired reading against each control: means, gap, the tasks whose value flipped, and
a caution when there is too little to characterise either. A pairing never says "better".

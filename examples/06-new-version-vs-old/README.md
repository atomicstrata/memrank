# 06 -- new version vs old

`uv run python examples/06-new-version-vs-old/run.py`

`TinyMemoryV2` is `TinyMemory` with one method changed: the words every question shares are
dropped before the overlap is counted. Both run on the three-task evaluation written in the
script, asked for their best two passages, because two is where ranking starts to matter.

**Prints** one paired reading. Read the **gap** in means; the **flips**, which tasks changed and
which way -- fixing three and breaking two is a gap near zero; and the **caution** when thin.

# 02 -- your own system

`uv run python examples/02-your-own-system/run.py`

The evaluation from 01, against a memory written in the script itself. The kind is the base
class: subclass `memrank.Memory` and implement `prepare`, `ingest`, `retrieve`, `cleanup`.
Nothing is registered and no file is written inside memrank. `declared_version` is optional,
like every declaration -- `None` is recorded as "did not state", never as zero.

**Prints** the result of that run, so the only thing that changed from 01 is the system.

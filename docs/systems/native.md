# Native -- `native`

```python
from memrank.systems import Native

system = Native(base_url="http://localhost:8099")
```

A client for any engine that speaks memrank's own contract -- so an engine memrank has never seen
can be measured without a line of it living here.

## How it works

Every other system here wraps one engine's API. This one wraps none. You run a small service --
a *translator* -- that answers memrank's contract on one side and calls your engine however you
like on the other, in whatever language your engine is written in. Memrank asks it to describe
itself, then drives the ordinary lifecycle over HTTP: prepare a group of
[tasks](../reference/task.md), hand over documents, ask for what is relevant, clean up.

Two things are inverted, deliberately. Memrank cannot configure an engine it does not know, so
the translator *states* its own configuration when it describes itself, and memrank records that
statement rather than asserting it. And a translator is an extra process and an extra hop, so it
is declared as its own transport class and its wall-clock latency is not comparable with an
engine memrank drives directly.

A translator announcing a contract version memrank does not implement is refused outright rather
than probed for compatibility.

## Why it matters

It is what makes the instrument vendor-neutral in practice rather than in principle. Adding an
engine does not need a fork, a pull request, or the maintainer's attention, and the
vendor-specific code stays in the vendor's process where they can fix it.

## What it needs

A running translator that implements the contract. Its address comes from `base_url=` or
`NATIVE_API_URL`, defaulting to `http://localhost:8099`.

## References

- [The system contract](../system-contract.md) -- the endpoints, the shapes, and the conformance
  suite a translator has to pass.
- [system](../reference/system.md) -- what a system is, and what memrank measures itself rather
  than asking for.
- [Methodology](../methodology.md) -- why a translator is its own transport class.

# paired

A **paired** reading puts two [results](result.md) of the same [evaluation](evaluation.md) side
by side and says how often chance alone produces a gap that size. It never says "better".

```python
import memrank
from memrank.evaluations import Demo
from memrank.systems import NoContext, WordOverlap

evaluation = Demo()
reading = memrank.paired(evaluation.run(system=WordOverlap()),
                         evaluation.run(system=NoContext()))

print(reading.system_a, "vs", reading.system_b, "on", reading.evaluation)
print(reading)
```

## What it is

A paired reading is a lens above the seven words, not an eighth one: it reads two results and
returns something that is not a result.

It **refuses** unless both results are of the same evaluation at the same version -- comparing
values from different questions is the mistake it exists to prevent -- and then pairs by task
id, per [measure](measure.md). What it reports:

- the mean of each side, and the gap between them;
- the tasks whose value **flipped**, named;
- how often chance alone produces a split that size: McNemar's exact test for a binary measure,
  a cluster-resampled paired bootstrap for a continuous one;
- a **caution** where too few tasks differ to characterise the gap at all.

The closing caveat -- that a gap is a gap, and which system is better depends on what you are
buying -- is printed by the reading itself rather than added by whoever formatted it, so it
travels with the values.

## Who supplies what

You supply two results of the same evaluation at the same version, and what the comparison is
*for*, which the reading does not know. Memrank supplies the refusal when the versions differ,
the pairing by task, the statistics, the flipped tasks and the caution.

## The Python names

```python
import memrank
from memrank.evaluations import Demo
from memrank.systems import NoContext, WordOverlap

evaluation = Demo()
reading = memrank.paired(evaluation.run(system=WordOverlap()),
                         evaluation.run(system=NoContext()))

print(reading.evaluation, reading.version)
print("measures compared:", sorted(m.measure for m in reading.measures))
print("only in A:", reading.only_in_a, "| only in B:", reading.only_in_b)
```

- `memrank.paired(a, b)` -- the reading. `resamples=` and `seed=` control the bootstrap and
  make it deterministic.
- `memrank.Paired` -- what comes back: `evaluation`, `version`, `system_a`, `system_b`,
  `only_in_a`, `only_in_b`, `measures`.
- `only_in_a` / `only_in_b` -- tasks one side has and the other does not, named rather than
  dropped.

## Going deeper

- [result](result.md) -- the two things it reads.
- [Methodology](../methodology.md) -- the control arms, the context-budget control, and why an
  uncontrolled comparison is not one.
- [`examples/05-against-a-baseline/`](../../examples/05-against-a-baseline/) and
  [`examples/06-new-version-vs-old/`](../../examples/06-new-version-vs-old/) -- two comparisons
  worth making.

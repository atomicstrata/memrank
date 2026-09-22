# paired

## An instance, first

You have run two systems over the same questions -- `WordOverlap`, which ranks documents by
shared words, and `NoContext`, the control that retrieves nothing at all -- and you want to
know whether the difference between them is real or could be the five questions you happened to
pick. A **paired** reading is that comparison:

```python
import memrank
from memrank.evaluations import demo
from memrank.systems import NoContext, WordOverlap

evaluation = demo()
mine = memrank.run(WordOverlap(), evaluation)
control = memrank.run(NoContext(), evaluation)

reading = memrank.paired(mine, control)
print(reading.system_a, "vs", reading.system_b, "on", reading.evaluation)
print(reading)
```

```console
WordOverlap vs NoContext on demo
demo at memrank-demo@v1+def0
  A = WordOverlap    B = NoContext

word-match (binary, 5 paired task(s))
  mean A 0.800   mean B 0.200   gap -0.600   3 discordant
  both 1  neither 1  only A 3  only B 0  McNemar exact p = 0.25
  flipped: q_job  1.0 -> 0.0
  flipped: q_animal  1.0 -> 0.0
  flipped: q_visit  1.0 -> 0.0
  caution: too few discordant tasks to characterise the gap

A gap is a gap. Nothing above says which system is better; that depends on what
you are buying, and these numbers do not know what that is.
```

## What it is

A paired reading is a lens above the seven words, not an eighth one: it reads two
[results](result.md) and returns something that is not a result.

It **refuses** unless both results are of the same [evaluation](evaluation.md) at the same
version -- comparing numbers from different questions is the mistake it exists to prevent --
and then pairs by task id, per [measure](measure.md). What it reports:

- the mean of each side, and the gap between them;
- the tasks whose value **flipped**, named;
- how often chance alone produces a split that size: McNemar's exact test for a binary measure,
  a cluster-resampled paired bootstrap for a continuous one;
- a **caution** where too few tasks differ to characterise the gap at all -- it says so instead
  of characterising it.

It never says "better", and the closing caveat is printed by the reading itself rather than
added by whoever formatted it, so it travels with the numbers.

## Who supplies what

| You supply | Memrank supplies |
|---|---|
| two results of the same evaluation at the same version | the refusal when they are not |
| nothing else | the pairing by task, the statistics, the flipped tasks, the caution |
| what the comparison is *for* -- it does not know | a gap, and no verdict about it |

## The Python names

```python
import memrank
from memrank.evaluations import demo
from memrank.systems import NoContext, WordOverlap

evaluation = demo()
reading = memrank.paired(memrank.run(WordOverlap(), evaluation),
                         memrank.run(NoContext(), evaluation))

print(reading.evaluation, reading.version)
print("measures compared:", sorted(m.measure for m in reading.measures))
print("only in A:", reading.only_in_a, "| only in B:", reading.only_in_b)
```

```console
demo memrank-demo@v1+def0
measures compared: ['word-match']
only in A: () | only in B: ()
```

- `memrank.paired(a, b)` -- the reading. `resamples=` and `seed=` control the bootstrap and
  make it deterministic.
- `memrank.Paired` -- what comes back: `evaluation`, `version`, `system_a`, `system_b`,
  `only_in_a`, `only_in_b`, `measures`.
- `only_in_a` / `only_in_b` -- tasks one side has and the other does not, named rather than
  dropped.

## Going deeper

- [`examples/05-against-a-baseline/`](../../examples/05-against-a-baseline/) and
  [`examples/06-new-version-vs-old/`](../../examples/06-new-version-vs-old/) -- two comparisons
  worth making.
- [Methodology](../methodology.md) -- the control arms, the context-budget control, and why an
  uncontrolled comparison is not one.
- [result](result.md) -- the two things it reads.

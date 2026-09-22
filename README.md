# Memrank

> Memrank is an instrument: it measures how well a memory helps answer questions about what
> it was told earlier -- on your own machine, on your own data, under a configuration you can
> read and a number you can re-run.

**Status:** v0.4, in active development. Interfaces still move between releases.

You bring the engine, and your own questions if you have them. Memrank brings everything in
between: it supplies the material, puts the questions, records what came back, and turns those
records into named numbers -- each one carrying the rule that produced it and who decided it, so
no number on the way out is anonymous.

Six things people do with it, in the order most people meet them. Each one below is the whole
flow, with the output it actually prints.

## Get a first number

**You have** Python and five minutes, and nothing else wired up. **You want** to see what
memrank hands back before deciding whether to spend an afternoon on it.

Add memrank to a project. This is a library install, and it is what the block underneath needs:

```bash
uv add memrank                  # or, into a virtualenv you already have: pip install memrank
```

No project yet? `uv init memrank-try` makes one, and you run `uv add memrank` from inside it.
[Installing memrank](docs/install.md) covers uv itself, Python versions and upgrading.

Now save this as `first_run.py` and run it with `uv run python first_run.py`:

```python
import memrank
from memrank.evaluations import demo
from memrank.systems import WordOverlap

result = memrank.run(WordOverlap(), demo())

print(result)
```

```console
system:     WordOverlap (memory), version in-process
evaluation: demo at memrank-demo@v1+def0, 5 task(s), cleared per-group

  demo-score             0.800  decided by rule    [demo_alex]
    evidence_recall (retrieval proxy; not answer correctness)
  word-match             1.000  decided by rule    [q_job]
    span match in a recalled document; a retrieval proxy, not answer correctness; matched 'marine biologist' in 'sess_1'
  word-match             1.000  decided by rule    [q_animal]
    span match in a recalled document; a retrieval proxy, not answer correctness; matched 'blue whale' in 'sess_1'
  word-match             1.000  decided by rule    [q_visit]
    span match in a recalled document; a retrieval proxy, not answer correctness; matched 'april' in 'sess_2'
  word-match             0.000  decided by rule    [q_diet]
    span match in a recalled document; a retrieval proxy, not answer correctness
  word-match             1.000  decided by rule    [q_allergy_neg]
    span match in a recalled document; a retrieval proxy, not answer correctness; matched None in None
  latency.ingest.p50     0.011  decided by memrank [whole run]
    milliseconds, memrank's own clock, over 1 sample(s)
  latency.ingest.p95     0.011  decided by memrank [whole run]
    milliseconds, memrank's own clock, over 1 sample(s)
  latency.retrieve.p50   0.011  decided by memrank [whole run]
    milliseconds, memrank's own clock, over 5 sample(s)
  latency.retrieve.p95   0.021  decided by memrank [whole run]
    milliseconds, memrank's own clock, over 5 sample(s)
  failure-rate           0.000  decided by memrank [whole run]
    0 of 5 traces carry an error

traces:     5 recorded, 0 with errors -- one per task per attempt, always
```

The four `latency` lines are memrank timing itself, so they differ on every machine and every
run. Nothing else in that output does.

Two things went into that call, and everything you just read came out of it:

- `WordOverlap()` is the thing being measured -- a [**system**](docs/reference/system.md). This
  one is about thirty lines that ship with the package: it keeps passages in a Python list and
  ranks them by how many words they share with the question. It needs no engine, no network and
  no API key, and it exists so that the first number costs you nothing. Your own memory backend
  goes in the same place, and the next flow shows how.
- `demo()` is what it was measured against -- an [**evaluation**](docs/reference/evaluation.md):
  a named, versioned bundle of questions plus the rules for turning answers into numbers. `demo`
  is five questions about a short conversation between two people, shipped with the package.
- Each question in it, with the passages to hand over first and what a right answer contains, is
  a [**task**](docs/reference/task.md). `q_diet` and `q_job` above are two of the five.
- [`memrank.run`](docs/reference/run.md) is the act: it hands the material over, puts each
  question, and records exactly one [**trace**](docs/reference/trace.md) per question -- what was
  given, what came back, how long each step took, and the error if it broke. Five questions, five
  traces, always, including the ones that fail.
- Each line of numbers is produced by a [**measure**](docs/reference/measure.md): a named rule
  that reads those traces. `word-match` is one, `latency.retrieve.p50` is another. Every measure
  says who decided -- `memrank`'s own clock, a fixed `rule`, a `model` that adjudicated, or the
  `system`'s own word -- which is the `decided by` column.
- What comes back is a [**result**](docs/reference/result.md): the traces and the numbers
  together. `result.values` is the numbers, `result.traces` is the record underneath them, and
  `print(result)` is the whole of the read -- memrank lays it out so nothing you write has to.

That is the entire vocabulary. There is no eighth word, and
[`docs/reference/`](docs/reference/README.md) has a page per word if you want one now rather
than as it turns up.

## Measure something of your own

**You have** a memory backend -- your own class over a vector store, a pile of notes, a service
your team runs. **You want** the same five questions put to it instead.

If it is already a running service and memrank ships a client for it, there is no class to
write: `AtomicMemory`, `Hindsight`, `Mem0` or `Supermemory` from `memrank.systems` go exactly
where `WordOverlap()` went, with `base_url=` (and `api_key=` for the two that authenticate), or
with nothing at all if `ATOMICMEMORY_API_URL`, `HINDSIGHT_API_URL`, `SUPERMEMORY_BASE_URL` or
`MEM0_HTTP_URL` is set.

Otherwise you write four methods. They are the four moments memrank needs, and nothing more:

```python
import memrank
from memrank import Recall


class NoteBook(memrank.Memory):
    """Whatever you are measuring, wrapped in the four calls memrank makes."""

    name, version, engine_version = "notebook", "0.1", "0.1"

    def __init__(self):
        self._notes = []

    def prepare(self, isolation_unit):
        # Called before a fresh batch of questions. Start empty, so one batch cannot
        # answer another batch's questions out of what it happens to be holding.
        self._notes = []

    def ingest(self, documents):
        # Here is the material, before anything is asked. In your own class this is the
        # write call to your store.
        self._notes.extend(documents)

    def retrieve(self, query, k, user_id, query_timestamp=None) -> Recall:
        # Here is one question: hand back at most k passages, best first. The order IS
        # what is being measured, so never pad the list out to k to fill it.
        words = set(query.lower().split())
        ranked = sorted(self._notes,
                        key=lambda d: len(words & set(d.content.lower().split())),
                        reverse=True)[:k]
        return Recall(documents=ranked)

    def cleanup(self):
        # Done with this batch. In your own class, delete whatever prepare() created.
        self._notes = []


result = memrank.run(NoteBook(), memrank.evaluation("demo"))

print(result.system.name, result.system.kind, "--", len(result.traces), "questions asked")
for value in result.values_of("word-match"):
    print(f"  {value.task_id:<14} {value.value}")
```

```console
NoteBook memory -- 5 questions asked
  q_job          1.0
  q_animal       1.0
  q_visit        1.0
  q_diet         0.0
  q_allergy_neg  1.0
```

None of those four methods reports a measurement memrank takes itself. Memrank times every
`ingest` and every `retrieve` at its own call boundary, so speed is neither your job nor
something your class could flatter. What only your code knows -- the engine version behind it,
what a provider billed, time only it can see -- it may *declare* through optional methods that
return `None` until you say otherwise, and `None` is recorded as "did not state", never as zero.

Memory is one kind of thing under test; `memrank.Model`, `memrank.Retriever` and
`memrank.Assistant` are the others, and the kind is simply the class you subclass, so it cannot
be declared wrong. A run refuses before touching your code -- with a reason and no traces -- when
a required method is missing, when a measure reads something nothing in the run produces, or when
there is material to hand over and no method to hand it to.

## Ask your own questions

**You have** your own support tickets, your own transcripts, your own documents. **You want** to
know how a memory does on those rather than on a conversation about whales.

An evaluation you write and one that ships are the same object; `memrank.evaluation("demo")`
returns exactly the kind of thing built by hand below.

```python
import memrank
from memrank import Clearing, Document, Evaluation, Expected, Task
from memrank.systems import WordOverlap

# The material the system is told, before any question is asked.
notes = (Document(id="t1", user_id="acme",
                  content="Acme moved to the enterprise plan in March."),
         Document(id="t2", user_id="acme",
                  content="Acme's outage was traced to an expired webhook secret."))

tickets = Evaluation(
    name="tickets", version="internal@2026-09",
    tasks=(
        # One question, the material it is asked against, and what a right answer contains.
        Task(id="q_plan", prompt="What plan is Acme on?", group="acme", context=notes,
             expected=Expected(answers=("enterprise",), required_spans=("enterprise",),
                               evidence_doc_ids=("t1",))),
        Task(id="q_outage", prompt="What caused Acme's outage?", group="acme", context=notes,
             expected=Expected(required_spans=("webhook secret",),
                               evidence_doc_ids=("t2",)))),
    # How answers become numbers, and when the system's memory is wiped.
    measures=(memrank.WordMatch(),),
    clearing=Clearing.PER_GROUP)

result = memrank.run(WordOverlap(), tickets)

for value in result.values_of("word-match"):
    print(f"{value.task_id:<10} {value.value}  decided by {value.decider.value}  -- {value.why}")
```

```console
q_plan     1.0  decided by rule  -- span match in a recalled document; a retrieval proxy, not answer correctness; matched 'enterprise' in 't1'
q_outage   1.0  decided by rule  -- span match in a recalled document; a retrieval proxy, not answer correctness; matched 'webhook secret' in 't2'
```

Questions that are meant to share what the system was told carry the same `group`: the material
is handed over once per group, and the memory is wiped between groups, never inside one.
`Clearing.PER_TASK` wipes it after every single question and `Clearing.AT_END` never wipes it
until the end; the result records which rule was in force.

Writing your own questions does not mean writing your own scoring rule, and writing your own
rule does not mean writing questions. They are separate on purpose, which is what the next
flow is about.

## Find out why a number is what it is

**You have** a number you do not believe -- `q_diet` scored 0.0 up there while everything else
scored 1.0. **You want** to know what actually happened before you report it or chase it.

Every number knows which question it came from, and every question has its trace:

```python
import memrank
from memrank.systems import WordOverlap

result = memrank.run(WordOverlap(), memrank.evaluation("demo"))

# values_of picks one rule's numbers out of all the rest.
low = [value for value in result.values_of("word-match") if value.value == 0.0][0]
print(low.task_id, low.value, "--", low.why)

# traces_of is the record of that one question: what was asked, what the evaluation
# was looking for, and what the system actually handed back, in the order it ranked it.
trace = result.traces_of(low.task_id)[0]
print("asked        ", trace.task.prompt)
print("looking for  ", trace.task.expected.required_spans)
print("must not say ", trace.task.expected.forbidden_spans)
for document in trace.recalled.documents:
    print("came back    ", document.id, "--", document.content)
```

```console
q_diet 0.0 -- span match in a recalled document; a retrieval proxy, not answer correctness
asked         What does Alex order for dinner?
looking for   ('vegetarian sushi',)
must not say  ('regular sushi',)
came back     sess_3 -- Alex: For dinner I always order vegetarian sushi. My colleague Sam loves regular sushi but I never eat fish.
came back     sess_1 -- Alex: Hi! I just moved to Portland for a new job as a marine biologist. My favorite animal is the blue whale.
```

So the retrieval was fine: the right passage came back first, and it contains the words the
question was looking for. The 0.0 is the same passage also containing `regular sushi`, which the
question forbids. `word-match` is a crude rule and it says so on every number it produces -- that
is the point of it carrying its reason around.

A rule that would have settled this in one line is one nobody wrote. You can write it now, and
run it over the run that already happened -- the system is never touched again, because scoring
is not inside the loop that asked the questions:

```python
from collections.abc import Sequence

import memrank
from memrank import Decider, Measure, Result, Scope, Trace, Value
from memrank.systems import WordOverlap


class EvidenceAtOne(Measure):
    """Did the passage holding the answer come back first, rather than third?"""

    name, scope, reads, decider = "evidence-at-1", Scope.TASK, ("recalled",), Decider.RULE

    def measure(self, traces: Sequence[Trace], values: Sequence[Value]) -> list[Value]:
        produced = []
        for trace in traces:
            wanted = set(trace.task.expected.evidence_doc_ids)
            ranked = trace.recalled.documents if trace.recalled else []
            top = ranked[0] if ranked else None
            doc_id = (top.metadata or {}).get("doc_id", top.id) if top is not None else None
            produced.append(Value(
                measure=self.name, decider=self.decider, task_id=trace.task_id,
                value=None if not wanted else float(doc_id in wanted),
                why=f"first back was {doc_id!r}; the answer is in {sorted(wanted)}"))
        return produced


result = memrank.run(WordOverlap(), memrank.evaluation("demo"))

# Write the whole run to a file: every question, every passage that came back, every
# number, and what produced each one.
result.save("/tmp/demo-run.json")

# Read it back -- another day, another machine, another script. Your system is asked
# nothing again; the new numbers are read off what was recorded the first time.
stored = Result.load("/tmp/demo-run.json")
measured = memrank.measure(stored, EvidenceAtOne())

print(len(stored.values), "numbers before,", len(measured.values), "after; nothing was rerun")
for value in measured.values_of("evidence-at-1"):
    print(f"  {value.task_id:<14} {value.value}  {value.why}")
```

```console
11 numbers before, 16 after; nothing was rerun
  q_job          1.0  first back was 'sess_1'; the answer is in ['sess_1']
  q_animal       1.0  first back was 'sess_1'; the answer is in ['sess_1']
  q_visit        1.0  first back was 'sess_2'; the answer is in ['sess_2']
  q_diet         1.0  first back was 'sess_3'; the answer is in ['sess_3']
  q_allergy_neg  None  first back was 'sess_2'; the answer is in []
```

Which settles it across all five: retrieval was right every time, and `q_diet`'s 0.0 was the
scoring rule, not the system. The last row is `None` rather than `0.0`, because that question
names no passage to find and the rule therefore had nothing to decide -- an admission, not a
zero. [The measure contract](docs/measures.md) is the whole of what a rule declares and what
memrank checks before letting it run.

## Check the instrument before you trust it

**You have** a score. **You want** to know whether the questions could have been answered
without a memory at all, and whether a perfect memory would even score higher than yours.

Memrank ships two arms for exactly that. `no-context` is the floor: it retrieves nothing and
answers from nothing. `full-context` is the ceiling: it is handed every passage, unranked and
uncapped, so it is the best any retrieval could do on these questions.

```python
import memrank

evaluation = memrank.evaluation("demo")

for name in ("no-context", "word-overlap", "full-context"):
    result = memrank.run(memrank.system(name), evaluation)
    scored = [value.value for value in result.values_of("word-match")
              if value.value is not None]
    print(f"{name:<14} {sum(scored) / len(scored):.3f}")
```

```console
no-context     0.200
word-overlap   0.800
full-context   0.800
```

Read that as a statement about `demo` rather than about `WordOverlap`. The floor at 0.200 says
the questions are not guessable, so the measurement is about memory. The ceiling at 0.800 says
0.800 is as high as anything goes here, and thirty lines of word counting already reach it --
`demo` is a scenario for checking that your plumbing works, not for separating good memories
from better ones. A real evaluation is one where the two arms are far apart and your system
sits somewhere between them.

[`memrank.catalog()`](docs/reference/catalog.md) prints everything installed -- every system with what it needs, every
evaluation with what it measures -- so you do not have to know a name to look one up.

## Compare two things side by side

**You have** two of something: your memory and a competitor's, this week's configuration and
last week's, with and without reranking. **You want** the difference, and to know whether it is
a difference at all.

```python
import memrank

evaluation = memrank.evaluation("demo")

mine = memrank.run(memrank.system("word-overlap"), evaluation)
theirs = memrank.run(memrank.system("no-context"), evaluation)

print(memrank.paired(mine, theirs))
```

```console
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

[`memrank.paired`](docs/reference/paired.md) refuses unless both runs are of the same evaluation
at the same version, then matches them question by question and rule by rule. It reports the two
means, the gap, every question whose number flipped, and how often chance alone produces a split
that size -- McNemar's exact test where the numbers are 0 or 1, a cluster-resampled paired
bootstrap where they are continuous. Where too few questions differ to say anything, it says
that instead of saying something.

It never says "better", and the last paragraph above is printed by the comparison itself rather
than added by whoever pasted it -- so the caveat travels with the numbers.

## What a number is, and what it is not

This is the part worth reading before quoting one.

- **No number is a bare score.** Every one carries the rule that produced it and who decided --
  `memrank`'s own clock and bookkeeping, a fixed `rule`, a `model` that adjudicated, or the
  `system`'s own word -- and most carry a reason. A number quoted without those two is a number
  whose meaning was dropped on the way out.
- **`word-match` is decided by a rule, and it is not answer correctness.** It marks whether the
  expected words appear verbatim in something the system handed back. That is retrieval, and its
  reason says so on every number it produces. Answer correctness is what `Judge` measures, and a
  model decides that one.
- **Nothing is combined unless a rule says it is.** A rule that produces several numbers names
  each under its own name (`latency.retrieve.p50`), so two numbers from one rule are never told
  apart by position, and memrank invents no overall score across rules.
- **Absent is not zero.** A system that declares no token usage records `None`. Conflating the
  two fabricates an efficiency win for every system that stays quiet. The same holds for a rule
  that could not decide: `None` with the reason, never `0.0`.
- **A failed question is a row, not a gap.** A run never stops on one: the trace carries the step
  it broke at and the message, `failure-rate` counts it, and every per-question rule records
  `None` with the reason.
- **A slice is not a measurement.** `beam:100k-smoke` and `locomo:mini` take the *first* N units,
  and the first units are not a fair sample -- measured, one evaluation's first conversation
  scores 0.318 against 0.158 for the full tier. Slices exist to debug plumbing cheaply.
- **Context budget is the decisive variable.** Every arm in a comparison is held to the same
  retrieval token budget, unless the evaluation's own protocol declares the reader uncapped (BEAM
  and LongMemEval do). Without that control, "retrieved better" and "returned more text" are the
  same number.
- **A run from a mutable checkout is not evidence.** It is recorded as a
  `development_observation` with `publishable: false`, however clean the git tree -- a commit
  identifies source, not the executable that ran.

The full contract is [docs/methodology.md](docs/methodology.md), which states what a number does
and does not license you to say.

**The command line.** Memrank ships a `memrank` command as well, and it is not core: nothing
above needs it, and it keeps an older vocabulary of its own. [The command
line](docs/misc/command-line.md) is where it lives.

## Documentation

| | |
|---|---|
| [Installing memrank](docs/install.md) | adding it to a project, a first run, upgrading, what works today |
| [Reference](docs/reference/README.md) | one page per word, each opening with a concrete instance |
| [Measures](docs/measures.md) | what a scoring rule declares, and the ones memrank ships |
| [Methodology](docs/methodology.md) | the four axes, the budget control, the control arms, evidence classes |
| [Adding a system](docs/systems.md) | a memory system in this tree, and the out-of-tree translator |
| [Adding an evaluation](docs/evaluations.md) | questions, scoring, registration |
| [The translator contract](docs/system-contract.md) | the wire contract for a system memrank drives as a process |
| [`examples/`](examples/README.md) | one folder per thing a person does: a first result, your own system, evaluation and measure, then three ways to compare |
| [Local development](docs/local-development.md) | working on memrank itself: environment, tests, checks |
| [SPEC.md](docs/SPEC.md) | the specification: what memrank measures, and the governance it commits to |

## Contributing

Adding a system does not require a fork or a pull request: write a **translator** that speaks
[the contract](docs/system-contract.md) over HTTP in any language, point memrank at it, and
run. [`examples/more/native-adapter/`](examples/more/native-adapter/README.md) is a working one
in about 150 lines of standard-library Python.

An **in-tree** system is for an engine that should be measurable by everyone who installs
memrank. It subclasses `memrank.Memory`, lives in `memrank/adapters/`, and must pass
`tests/live/conformance/test_adapter_contract.py`. See [adding a
system](docs/systems.md) and [adding an evaluation](docs/evaluations.md).

Methodology changes need a matching change to [docs/methodology.md](docs/methodology.md). A
scoring change that is not documented is not a scoring change we can accept.

## Governance

Memrank is maintained by [AtomicStrata](https://atomicstrata.ai) under a vendor-neutral charter:
anyone may submit an adapter, results are published as measured, methodology changes go through
public proposal and comment, and competitor adapters are run with the same diligence as our own.
The commitments and their enforcement are in [SPEC.md section 5](docs/SPEC.md).

**Disclosure.** AtomicStrata also ships a memory engine, AtomicMemory. It is measured by this
instrument and has placed below a no-memory-layer control arm in our own runs. The only useful
response to that conflict is to make the method checkable rather than to assert neutrality --
which is what [the methodology](docs/methodology.md) and [SPEC.md](docs/SPEC.md) are for, and why
the floor and the ceiling in *Check the instrument* are in the package rather than in a report of
ours.

## License

Apache 2.0 -- see [LICENSE](LICENSE).

## Contact

- Methodology questions and disagreements: open an issue.
- Anything else: hello@atomicstrata.ai

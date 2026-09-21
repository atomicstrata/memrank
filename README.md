# Memrank

> Memrank is an instrument: it measures how well a memory helps answer questions about what
> it was told earlier -- on your own machine, on your own data, under a configuration you can
> read and a result you can re-run.

**Status:** v0.4, in active development. Interfaces still move between releases.

You bring the engine, and your own tasks if you have them. Memrank brings everything between:
it gives the material, puts the tasks, records what happened, and applies the measures that
turn those records into named values. Every value it returns carries the measure that produced
it and who decided it, so no number on the way out is anonymous.

## Seven words, and nothing else to learn

Memrank is a Python package and `memrank.run(system, evaluation)` is its entry point. These are
the only words it uses:

| Word | What it is | Who supplies it |
|---|---|---|
| **system** | the thing under test. A **memory** is told things and later asked for what is relevant; there are also **model**, **retriever** and **assistant** kinds | you, or memrank |
| **evaluation** | a named, versioned bundle: its tasks, the measures it ships with, and the rule for when the system's state is cleared | either half, from either of you |
| **task** | one thing to put to the system: the context to give it, the prompt, and what a correct outcome looks like | the evaluation |
| **trace** | everything observed while one task ran. Exactly one per task per attempt, including on failure | memrank |
| **measure** | a named rule from traces to values, declaring what it reads and who decides: memrank's clock, a fixed rule, a judge model, or the system's own word | the evaluation, or you, afterwards |
| **run** | the act. It refuses *before* touching the system when the run cannot be set up | you compose it at the call |
| **result** | the traces and the values, each value carrying its measure's name and its decider. Never a bare number, and never a verdict | returned to you |

Two things sit above the seven: `memrank.measure(result, MyMeasure())` applies a measure you
thought of later to traces already stored, and `memrank.paired(a, b)` reads two results of the
same evaluation side by side. Neither says "better".

## Install

```bash
uv tool install memrank
memrank --version
```

If you do not have [uv](https://docs.astral.sh/uv/): `curl -LsSf https://astral.sh/uv/install.sh | sh`.

Working on memrank itself? Clone it and see [Local development](docs/local-development.md).
Full install detail, upgrading, PATH and MCP setup: **[Installing memrank](docs/install.md)**.

## Run something in one minute

`word-overlap` is a trivial in-process memory system that ships with the package, and `demo` is
a small synthetic evaluation that ships with it too. Together they need no engine, no network
and no API key:

```python
import memrank

system = memrank.system("word-overlap")
evaluation = memrank.evaluation("demo")
result = memrank.run(system, evaluation)

print(result)
```

```console
system:     WordOverlapAdapter (memory), version in-process
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
  latency.ingest.p50     0.006  decided by memrank [whole run]
    milliseconds, memrank's own clock, over 1 sample(s)
  latency.ingest.p95     0.006  decided by memrank [whole run]
    milliseconds, memrank's own clock, over 1 sample(s)
  latency.retrieve.p50   0.007  decided by memrank [whole run]
    milliseconds, memrank's own clock, over 5 sample(s)
  latency.retrieve.p95   0.014  decided by memrank [whole run]
    milliseconds, memrank's own clock, over 5 sample(s)
  failure-rate           0.000  decided by memrank [whole run]
    0 of 5 traces carry an error

traces:     5 recorded, 0 with errors -- one per task per attempt, always
```

Printing a result is the whole of the read: memrank lays it out, so nothing you write has to.
The four latency lines are memrank's own clock and differ on every machine and every run; the
rest of the output does not.

`result.values` is the whole answer, and every entry in it names its measure and its decider.
`result.traces` holds one trace per task -- what was given, what came back, what each step
timed, and the error with the step it broke at when it broke. `result.traces_of("<task id>")`
is where you dig when a value is low, and `result.values_of("<measure>")` is how you pick one
measure out of the rest.

If your system is a service that is already running and speaks a wire memrank ships a client
for, there is no class to write: name it instead -- `memrank.system("atomicmemory")`,
`"hindsight"`, `"mem0"` or `"supermemory"`, with `base_url=` (and `api_key=` for the two that
authenticate) where `"word-overlap"` goes. Each also reads its own environment variable when
the argument is left out -- `ATOMICMEMORY_API_URL`, `HINDSIGHT_API_URL`,
`SUPERMEMORY_BASE_URL`, `MEM0_HTTP_URL` -- and `memrank list-adapters` prints every name
`memrank.system` accepts.

## Bring your own memory system

A system is the thing under test, and its kind is the class you subclass, so a kind cannot be
declared wrong. A **memory** is told things, asked later for what is relevant, and cleared on
request. Those four verbs are the whole of what the kind requires; they are abstract, and
memrank refuses a run before touching anything when one is missing:

```python
import memrank
from memrank import Document, Recall


class NoteBook(memrank.Memory):
    name, version, engine_version = "notebook", "0.1", "0.1"

    def __init__(self):
        self._notes = []

    def prepare(self, isolation_unit):          # a fresh store per group of tasks
        self._notes = []

    def ingest(self, documents):                # you are told things
        self._notes.extend(documents)

    def retrieve(self, query, k, user_id, query_timestamp=None) -> Recall:
        words = set(query.lower().split())
        ranked = sorted(self._notes, key=lambda d: len(words & set(d.content.lower().split())),
                        reverse=True)[:k]
        return Recall(documents=ranked, declared={"considered": len(self._notes)})

    def cleanup(self):                          # you clear on request
        self._notes = []


result = memrank.run(NoteBook(), memrank.evaluation("demo"))
print(result.system.name, result.system.kind, result.system.version,
      len(result.traces), "traces")
```

```console
NoteBook memory 0.1 5 traces
```

Nothing in those four verbs reports a measurement memrank takes itself: memrank times every
ingest and retrieve at its own call boundary, so latency is neither your job nor something
your system could flatter. What only your system knows it may *declare* -- its version, what a
provider billed it, time only it can see, a fingerprint of what it is holding -- and those are
optional methods that return `None` until you say otherwise. `None` is recorded as "did not
state", never as zero.

`retrieve` returns a `Recall`: the passages ranked best first, and whatever your system wants
to declare about the call. The order **is** the measurement, so return at most `k` and never
pad. Failures raise; an empty list means "searched, found none".

The other kinds are `memrank.Model` (`complete`), `memrank.Retriever` (`rank`) and
`memrank.Assistant` (`respond`). A run refuses, with a stated reason and no traces, when the
system is not a kind memrank knows, when it lacks a verb its kind requires, when a measure
reads a name nothing in the run produces, or when the evaluation carries documents and the
system has no verb to be told things with.

## Bring your own evaluation

An evaluation is tasks, the measures it ships with, and a clearing rule, under a name and a
version. No scoring lives in it -- scoring lives in measures, which an evaluation only bundles.
memrank's own evaluations and yours are the same kind of object, which is why
`memrank.evaluation("demo")` returns exactly what you write by hand:

```python
import memrank
from memrank import Clearing, Document, Evaluation, Expected, Task
from memrank.adapters import WordOverlapAdapter

notes = (Document(id="t1", user_id="acme",
                  content="Acme moved to the enterprise plan in March."),
         Document(id="t2", user_id="acme",
                  content="Acme's outage was traced to an expired webhook secret."))

tickets = Evaluation(
    name="tickets", version="internal@2026-09",
    tasks=(Task(id="q_plan", prompt="What plan is Acme on?", group="acme", context=notes,
                expected=Expected(answers=("enterprise",), required_spans=("enterprise",),
                                  evidence_doc_ids=("t1",))),
           Task(id="q_outage", prompt="What caused Acme's outage?", group="acme", context=notes,
                expected=Expected(required_spans=("webhook secret",),
                                  evidence_doc_ids=("t2",)))),
    measures=(memrank.WordMatch(),),            # memrank's span proxy, decided by a rule
    clearing=Clearing.PER_GROUP)

result = memrank.run(WordOverlapAdapter(), tickets)
for value in result.values_of("word-match"):
    print(f"{value.task_id:<10} {value.value}  decided by {value.decider.value}  -- {value.why}")
```

```console
q_plan     1.0  decided by rule  -- span match in a recalled document; a retrieval proxy, not answer correctness; matched 'enterprise' in 't1'
q_outage   1.0  decided by rule  -- span match in a recalled document; a retrieval proxy, not answer correctness; matched 'webhook secret' in 't2'
```

Tasks that share state carry the same `group`: memrank gives a group's documents once and
clears between groups, never inside one. `Clearing.PER_TASK` and `Clearing.AT_END` are the
other two rules, and the result records which one was in force and whether the system could be
observed to have cleared.

Bringing your own questions does not mean writing your own measure, and bringing your own
measure does not mean writing questions. They are separate things on purpose.

## Bring your own measure, over a run that already happened

A measure declares three things before it runs: its scope (one task, or the whole run), which
trace fields and value names it reads, and who decides. Because measuring is not inside the run
loop, a measure you think of afterwards runs over the traces already stored -- the system is
never touched again:

```python
from collections.abc import Sequence

import memrank
from memrank import Decider, Measure, Result, Scope, Trace, Value
from memrank.adapters import WordOverlapAdapter


class EvidenceAtOne(Measure):
    """Did the document holding the evidence come back first?"""

    name, scope, reads, decider = "evidence-at-1", Scope.TASK, ("recalled",), Decider.RULE

    def measure(self, traces: Sequence[Trace], values: Sequence[Value]) -> list[Value]:
        produced = []
        for trace in traces:
            wanted = set(trace.task.expected.evidence_doc_ids)
            # `recalled` is the Recall the system returned: its documents, in the order it
            # ranked them. Position is the rank, so the first one is rank 1.
            ranked = trace.recalled.documents if trace.recalled else []
            top = ranked[0] if ranked else None
            doc_id = (top.metadata or {}).get("doc_id", top.id) if top is not None else None
            produced.append(Value(
                measure=self.name, decider=self.decider, task_id=trace.task_id,
                value=None if not wanted else float(doc_id in wanted),
                why=f"rank 1 was {doc_id!r}; the evidence is {sorted(wanted)}"))
        return produced


result = memrank.run(WordOverlapAdapter(), memrank.evaluation("demo"))
result.save("/tmp/demo-run.json")               # the traces persist, typed

stored = Result.load("/tmp/demo-run.json")      # a different process, days later
measured = memrank.measure(stored, EvidenceAtOne())

print(len(stored.values), "values before,", len(measured.values), "after; nothing rerun")
for value in measured.values_of("evidence-at-1")[:2]:
    print(f"{value.task_id}  {value.value}  {value.why}")
```

```console
11 values before, 16 after; nothing rerun
q_job  1.0  rank 1 was 'sess_1'; the evidence is ['sess_1']
q_animal  1.0  rank 1 was 'sess_1'; the evidence is ['sess_1']
```

A measure that reads a trace field or a value name nothing in the run produces is refused
before the run, naming what is available, rather than raising halfway through one. The measures
memrank ships are ordinary measures and nothing more: `WordMatch` is decided by a fixed rule,
`Judge` by a model, `Latency` and `FailureRate` by memrank's own clock and bookkeeping.

## Read two results side by side

A paired reading is a lens above the run, not an eighth word: it reads two results and returns
something that is not a result. It refuses unless both are of the same evaluation at the same
version, then pairs by task id, per measure:

```python
import memrank
from memrank.adapters import NoContextAdapter, WordOverlapAdapter

evaluation = memrank.evaluation("demo")
mine = WordOverlapAdapter()
control = NoContextAdapter()
result_mine = memrank.run(mine, evaluation)
result_control = memrank.run(control, evaluation)

print(memrank.paired(result_mine, result_control))
```

```console
demo at memrank-demo@v1+def0
  A = WordOverlapAdapter    B = NoContextAdapter

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

What it reports is the means, the gap, the tasks whose value flipped, and how often chance
alone produces a split that size -- McNemar's exact test for a binary measure, a
cluster-resampled paired bootstrap for a continuous one. Where too few tasks differ to
characterise the gap, it says so instead of characterising it.

It never says "better", and the last line above is printed by the reading itself rather than
added by whoever formatted it -- so the caveat travels with the numbers.

## What a value is, and what it is not

This is the part worth reading before quoting a number.

- **No number is a bare score.** Every value carries the measure that produced it and the
  decider -- `memrank`'s own clock and bookkeeping, a fixed `rule`, a `model` that adjudicated,
  or the `system`'s own word -- and most carry a `why`. A number quoted without those two is a
  number whose meaning was dropped on the way out.
- **`word-match` is a measure whose decider is a rule, and it is not answer correctness.** It
  marks whether the expected spans appear verbatim in something the system recalled. That is
  retrieval, and its `why` says so on every value it produces. Answer correctness is what
  `Judge` measures, and its decider is a model.
- **Nothing combines values unless a measure says it does.** A measure that produces several
  numbers names each under its own name (`latency.retrieve.p50`), so two values of one measure
  are never told apart by position, and memrank invents no overall score across measures.
- **Absent is not zero.** A system that declares no token usage records `None`. Conflating the
  two fabricates an efficiency win for every system that stays quiet. The same rule governs a
  measure that could not decide: it returns `None` with the reason, never `0.0`.
- **A failed task is a row, not a gap.** The run never stops on a task's failure: the trace
  carries the step it broke at and the message, `failure-rate` counts it, and every task-scope
  measure records `None` with the reason for it.
- **A slice is not a measurement.** `beam:100k-smoke` and `locomo:mini` take the *first* N
  units, and the first units are not a fair sample -- measured, one evaluation's first
  conversation scores 0.318 against 0.158 for the full tier. Slices exist to debug plumbing
  cheaply.
- **Context budget is the decisive variable.** Every arm in a comparison is held to the same
  retrieval token budget, unless the evaluation's own protocol declares the reader uncapped
  (BEAM and LongMemEval do). Without that control, "retrieved better" and "returned more text"
  are the same number.
- **A run from a mutable checkout is not evidence.** It is recorded as a
  `development_observation` with `publishable: false`, however clean the git tree -- a commit
  identifies source, not the executable that ran.

The full contract is [docs/methodology.md](docs/methodology.md), which states what a number
does and does not license you to say.

## The command line: the operator surface

Everything above is the entry path. The command line is the operator surface on top of it: a
run you want tracked, compared, placed somewhere other than this process, or run by name rather
than by object. It keeps its own older vocabulary -- *target* for a named system, *eval* for a
named evaluation -- and it still drives the previous run loop, which produces the stored
artifact the cloud reads. Reach for it when you want those things, not to get a first number.

```console
$ memrank submit word-overlap demo
run 20260826-213813__demo__7becda  (word-overlap × demo)
track: memrank watch 20260826-213813__demo__7becda

$ memrank runs ls
ID                             TARGET        EVAL  PLACE  STATE  AGE  DONE  SCORE
20260826-213813__demo__7becda  word-overlap  demo  local  done     8s  100%  0.8000
```

`submit` returns immediately with a run id; `watch <id>` blocks on it, `runs show <id>` gives
the full record -- state, where it ran, exit code, artifact location -- and `kill <id>` stops
it.

```bash
memrank targets ls               # what can be evaluated (hindsight, atomicmemory, word-overlap, ...)
memrank evals ls                 # what to evaluate against (locomo, beam, longmemeval, demo, ...)
memrank targets show hindsight   # the exact composition, and ✔/✘ per secret it needs
memrank submit --help            # every flag, grouped
```

A **target** is a named composition -- a system plus the embedder and LLM it is configured with
-- so a row can never mean two different things. Refs are `[namespace/]name[:preset]`; a bare
ref is the vendor's own configuration, and memrank's budget-matched comparison arm carries the
suffix (`hindsight` vs `hindsight:matched`). `--on` says where the system runs:

| | |
|---|---|
| `--on none` (default) | talk to a system you are already running |
| `--on local` | provision a disposable, isolated stack per run from the target manifest (needs Docker) |
| `--on cloud` | submit to the hosted memrank platform (needs `memrank auth login`; membership is not self-served yet) |

```bash
export HINDSIGHT_API_URL=http://localhost:7000
memrank submit hindsight locomo:smoke --on none
```

Which systems you can actually obtain differs per target, and two of them you cannot pull at
all. [Engine images](docs/engine-images.md) states it per target, with what to run instead.

Judged runs send evaluation content to Anthropic and need `ANTHROPIC_API_KEY`. They are on by
default for `locomo`, `longmemeval` and `beam`, whose only quality metric is the judge's;
`--no-judge` measures latency and cost without paying for quality.

## Documentation

| | |
|---|---|
| [Installing memrank](docs/install.md) | install, sign-in, MCP, what works today |
| [Local development](docs/local-development.md) | working on memrank itself: environment, tests, checks |
| [Methodology](docs/methodology.md) | the four axes, the budget control, the control arms, evidence classes |
| [Adding a system](docs/adding-adapters.md) | a memory system in this tree, and the out-of-tree translator |
| [Adding an evaluation](docs/adding-benchmarks.md) | tasks, scoring, registration |
| [The translator contract](docs/adapter-contract.md) | the wire contract for a system memrank drives as a process |
| [`examples/`](examples/README.md) | one folder per thing a person does: a first result, your own system, evaluation and measure, then three ways to compare |
| [SPEC.md](docs/SPEC.md) | the specification: what memrank measures, and the governance it commits to |

## Contributing

Adding a system does not require a fork or a pull request: write a **translator** that speaks
[the contract](docs/adapter-contract.md) over HTTP in any language, point memrank at it, and
run. [`examples/more/native-adapter/`](examples/more/native-adapter/README.md) is a working one in about
150 lines of standard-library Python.

An **in-tree** system is for an engine that should be measurable by everyone who installs
memrank. It subclasses `memrank.Memory`, lives in `memrank/adapters/`, and must pass
`tests/live/conformance/test_adapter_contract.py`. See [adding a
system](docs/adding-adapters.md) and [adding an evaluation](docs/adding-benchmarks.md).

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
which is what the audits under [`docs/`](docs/README.md) are for.

## License

Apache 2.0 -- see [LICENSE](LICENSE).

## Contact

- Methodology questions and disagreements: open an issue.
- Anything else: hello@atomicstrata.ai

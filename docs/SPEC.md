---
title: "Memrank -- Public Specification"
status: active
last_reviewed: 2026-08-26
audience: external
public_repo: https://github.com/atomicstrata/memrank
license: Apache 2.0
maintainer: AtomicStrata (vendor-neutral charter)
---

# Memrank -- Public Specification

**One line:** an open, vendor-neutral instrument for evaluating AI-agent memory engines
head-to-head on standard datasets, across quality, latency, cost and token efficiency, with
everything needed to re-run each number attached to it.

This document is the canonical statement of what memrank measures, what it refuses to claim, the
contracts a contribution must satisfy, and the governance the maintainer commits to. It is the
document to cite in a disagreement about method. Where an implementation detail is needed,
[`docs/methodology.md`](methodology.md) is authoritative and this specification defers to it.

---

## 1. Mission

The AI-agent ecosystem chooses memory engines from numbers nobody outside the vendor can check.
Each vendor publishes through its own harness, at its own retrieval budget, under its own judge,
against its own dataset snapshot. Latency, ingestion cost and token efficiency are frequently not
measured at all.

Shared harnesses do exist -- the honest statement of the gap is narrower and more uncomfortable
than "there is no comparison." **Every shared harness we could find is operated by a company that
appears in its own results**, memrank included. What memrank offers instead of a claim of
neutrality is a method that can be checked: the configuration is declared, the protocol is
documented, and the result carries what is needed to re-run it. A number that cannot be re-run is
not a result.

## 2. Scope

### 2.1 What memrank measures

For every (target, benchmark) cell:

| Axis | Metric | Source |
|---|---|---|
| Quality | The benchmark's composite, under that benchmark's declared scoring | Per-benchmark scorer |
| Per-category quality | Sub-scores per benchmark category (e.g. BEAM's abilities) | Per-benchmark scorer |
| Judged quality | LLM-judged sufficiency and answer correctness, where the benchmark requires it | `memrank/judging/` |
| Ingest latency | p50, p95, p99 milliseconds per ingest call | memrank instrumentation |
| Retrieve latency | p50, p95, p99 milliseconds per retrieve call | memrank instrumentation |
| Tokens | Mean and p95 tokens per query and per ingest | memrank instrumentation |
| Cost | Mean USD per query, priced from the declared model | `memrank/metrics/cost.py` |
| Provenance | Config, dataset version, model, seed, instrument version, evidence class | Reproducibility receipt |

**No number is recorded without a receipt** (section 6).

### 2.2 What is under test

The unit of measurement is a **target**: a named composition of an engine *and* the embedder and
LLM it is configured with, resolved from a manifest. An engine under two configurations is two
targets and two rows, told apart by `config_hash`. This is not bookkeeping -- a memory engine's
result is dominated by the models it is wired to, so a row naming only the engine names two
different systems at two different times.

Targets are defined for `atomicmemory`, `mem0`, `hindsight` and `supermemory`, plus the control
arms `no-context`, `fixed-context`, `full-context` and `word-overlap`. Not every engine image is
obtainable, and the ones that are not are named as such: see
[engine images](engine-images.md). Benchmarks ship for `locomo`,
`beam`, `longmemeval`, `relation_graph` and the synthetic `demo`.

### 2.3 Control arms are part of the measurement

Three, not one, and a run that omits them is not a comparison:

- `no-context` retrieves nothing -- does the reader already know the answer?
- `fixed-context` reads the corpus unranked, token-matched to the system under test -- does ranked
  retrieval beat reading the first N tokens?
- `full-context` reads everything uncapped -- is memory needed at all when the corpus fits?

Their known limits are recorded rather than hidden: `fixed-context` reads from the start, so a
corpus whose answers cluster late disadvantages it, and `no-context` is only meaningful judged.

### 2.4 Out of scope

- Engines with no isolation primitive. Scoring requires that nothing ingested for one unit is
  visible to another; an engine that cannot guarantee that cannot be measured here.
- Closed engines with no documented API, because a result nobody else can reproduce is not one
  this instrument will publish.
- Latency of hosted-only services where network round-trip dominates the measurement. memrank
  measures local-deploy and self-host paths.

## 3. What a score means

This section is normative. A consumer of memrank output that ignores it will misreport.

**`composite` is not answer correctness.** It is whatever the benchmark declares. LoCoMo,
LongMemEval and `demo` compute a deterministic substring-recall proxy; `relation_graph` computes a
structural graph score; BEAM's gold answers are prose, so substring recall is structurally near
zero for it and is not a quality signal at all.

**Structurally invalid metrics are withheld, not caveated.** Each benchmark declares
`substring_recall_supported` and `composite_rankable`. Where the composite is not rankable without
a judge, the rankable surfaces refuse to show one and report `withheld (judge required)`. The
contract for consumers: **`composite` is a valid quality score only when
`substring_recall_supported` is true; otherwise rank from a judged run.**

**The context budget is declared and symmetric.** The default holds every arm to the same
retrieval token budget, because without it "retrieved better" and "returned more text" are the
same number. A benchmark whose own protocol hands the reader everything retrieval returned may
declare `context_policy = "uncapped"`, and two do -- BEAM and LongMemEval -- because a capped run of
those is not those benchmarks. What is enforced is that the policy applies to every arm alike and
travels in the receipt, so a capped and an uncapped run cannot be mistaken for each other later.

**Absent is not zero.** An engine reporting no token usage records `null`. `0.0` is the claim that
it spent nothing, and conflating the two fabricates an efficiency win for every engine that stays
quiet.

**A slice is not a measurement.** `beam:100k-smoke`, `locomo:mini` and their kin take the *first*
N units, which is not a fair sample: measured on a full judged BEAM 100k tier, conversation 1
scores 0.318 against 0.158 for the tier -- a smoke number flatters every engine by roughly 2x.
Slices exist to debug ingest, retrieval, judging and dispatch cheaply. A measurement claim comes
from a full tier.

**A methodology change is a documentation change.** A change to scoring, dataset version, or
latency protocol that does not carry a matching change to `docs/methodology.md` is not a change
this project accepts (section 7.3).

## 4. Adapter contract

An adapter subclasses `MemoryAdapter` (`memrank/core.py`). The full contract, including the
metadata and engine-description surfaces, is [`docs/adapter-contract.md`](adapter-contract.md);
this is its shape.

```python
class MemoryAdapter(ABC):
    name: str             # registry name, short and stable -- result files use it
    version: str          # adapter implementation version
    engine_version: str   # the wrapped engine's version

    def prepare(self, isolation_unit: str) -> None: ...
    def ingest(self, documents: list[Document]) -> None: ...
    def retrieve(self, query: str, k: int, user_id: str,
                 query_timestamp: datetime | str | None = None,
                 ) -> tuple[list[Document], dict[str, Any]]: ...
    def cleanup(self) -> None: ...
    def latency_metrics(self) -> dict[str, float]: ...
    def token_metrics(self) -> dict[str, float | None]: ...
```

An adapter **must**:

- Guarantee isolation. Nothing ingested under one `isolation_unit` may be visible under another.
- Return documents **ranked best-first** from `retrieve`, and return fewer than `k` rather than
  padding.
- Emit the required latency keys (`ingest_p50_ms`, `ingest_p95_ms`, `ingest_p99_ms`,
  `retrieve_p50_ms`, `retrieve_p95_ms`, `retrieve_p99_ms`) and token keys
  (`tokens_per_query_mean`, `tokens_per_query_p95`, `tokens_per_ingest_mean`,
  `tokens_per_ingest_p95`), using memrank's collectors rather than a private metric shape.
- Report `null` for a bucket the engine did not measure, never `0.0`.
- **Fail loudly.** Raise on error rather than returning an empty result -- an empty list is a valid
  answer meaning "nothing matched", so a disguised failure scores exactly like the no-memory
  control arm and reads as a real one. No silent fallback or degraded mode.
- Pass `tests/live/conformance/test_adapter_contract.py`.

An adapter **may** be written in any language and live outside this repository. A **translator**
speaks the same contract over HTTP; memrank launches it, drives it, and never imports it.
[`examples/native-adapter/`](../examples/native-adapter/README.md) is a working one in about 150 lines
of standard-library Python.

## 5. Benchmark contract

A benchmark subclasses `Benchmark` (`memrank/core.py`):

```python
class Benchmark(ABC):
    name: str
    dataset_version: str              # the data
    VERSION: int                      # the load/score definition -- bump on any breaking change
    substring_recall_supported: bool  # is the deterministic proxy meaningful here?
    composite_rankable: bool          # may `composite` be displayed and ranked without a judge?
    quality_metric: str               # what the composite column is actually called
    context_policy: str               # "matched" (default) | "uncapped"
    is_synthetic: bool                # may its content be sent to a judge without egress consent?
    requires_graph: bool              # does scoring need an adapter graph snapshot?

    def load(self) -> list[BenchmarkUnit]: ...
    def score(self, unit, responses) -> dict[str, Any]: ...   # at minimum a `composite` float
    def judge_shape(self) -> JudgeShape: ...
    def report_template(self) -> str: ...
```

A benchmark **must**:

- Run the dataset's own scoring protocol, and document every divergence from it with a rationale
  and an impact estimate.
- Declare its own judgeability through `judge_shape()`. A category the judge gate has never heard
  of must raise, never silently shrink the denominator -- that failure ran undetected in this
  harness for months and cost 60.8% of one benchmark's questions (section 7.4).
- Declare its metric honestly through the flags above rather than letting a caller infer them.
- Bump `VERSION` on any breaking change to how it loads or scores, so version-against-version
  comparison can refuse instead of silently comparing two definitions.

Judged runs are optional, require `ANTHROPIC_API_KEY`, enforce a call cap, and gate egress on the
benchmark's own `is_synthetic` declaration rather than on a flag the caller passes.

## 6. Reproducibility

Every run emits a receipt (`memrank/provenance/receipt.py`) recording:

- memrank version and commit, and the adapter, engine and dataset versions
- the resolved configuration and its `config_hash`, plus `config_hash_version`
- the answer and judge models, by provider and name
- the seed, the start and finish times, the duration
- the host and environment fingerprint -- **hashed, never plaintext**, and never a secret value
- the evidence class (section 6.1)

If any of these differ between two runs, they are two rows, not one number measured twice.

### 6.1 Evidence classes

Not every run is evidence, and memrank says which is which rather than leaving it to be assumed:

| Class | What produced it | Publishable |
|---|---|---|
| `reproducible_evidence` | An immutable, resolvable executable artifact | yes |
| `development_observation` | A mutable local checkout | no |
| `endpoint_observation` | An already-running HTTP engine with no resolved executable identity | no |

**A clean git tree does not promote a development observation.** A commit identifies source, not
the executable that ran or the toolchain that built it. Development observations keep their scores
and are useful for comparison; they are ineligible for publication, and a run from a dirty tree
does not leave the machine.

## 7. Governance -- the vendor-neutral charter

memrank is maintained by **AtomicStrata**, which also ships a memory engine. That is a structural
conflict of interest and the charter exists to make it checkable rather than to deny it.

### 7.1 Open contribution

Anyone may submit an adapter or a benchmark by pull request. There is no approval gate beyond
review for correctness and conformance to section 4 and section 5. An engine can also be measured with no pull
request at all, through an out-of-tree translator.

### 7.2 Verbatim publication

Results are published as measured. AtomicStrata does not curate, omit, or asterisk results
unfavourable to its own engine. Where a result is anomalous, the methodology and the raw output
are published beside it.

### 7.3 Methodology changes are public

A change to scoring, dataset version, or the latency-measurement protocol requires a public
proposal with a comment period before it merges, and a matching change to the documentation.
Affected results are re-run and re-published; superseded numbers stay accessible with the
methodology version they were produced under.

### 7.4 The conflict is checked by reproduction, not asserted away

The mitigation is that every measurement is reproducible by anyone with a clone and the relevant
API keys. Two consequences the maintainer accepts:

- If a third party reports they cannot reproduce a published memrank number, AtomicStrata
  investigates and either fixes the discrepancy or publishes the gap.
- Findings against our own harness and our own engine are stated rather than buried. The record
  so far includes a LoCoMo path that silently scored 39.2% of the benchmark under labels wrong on
  three of four names, a published BEAM headline that turned out to be the high draw of a
  distribution, and a competitor scoring above our own engine when run properly in our own
  harness. All three were found by auditing ourselves against the benchmarks' own protocols.

### 7.5 Long-term governance

Sole maintainership by AtomicStrata is the starting position, not the intended end state. A public
steering committee with seats for third-party memory-engine maintainers is the next step, and
independent stewardship after that if adoption justifies it. Neither is claimed as done.

## 8. Hosting and licensing

- **Repository:** https://github.com/atomicstrata/memrank
- **License:** Apache 2.0 -- chosen for the patent grant and enterprise compatibility.
- **Install:** `uv tool install git+https://github.com/atomicstrata/memrank`. Not yet on PyPI.
- **Results:** run output is written under `results/` on the machine that ran it. There is no
  standing public leaderboard, and this specification does not authorise one; publication is
  selective and evidence-led.

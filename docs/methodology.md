# Methodology

Memrank measures four axes for every (adapter, benchmark) cell:

1. **Quality** -- composite score per the benchmark's published methodology
2. **Latency** -- p50/p95/p99 in milliseconds for `ingest()` and `retrieve()`
3. **Tokens** -- mean and p95 tokens per query / per ingest call
4. **Cost** -- derived from token usage and per-model pricing tables

This document describes how each axis is captured.

## Quality

Each benchmark implements its own `score()`. The v0.1 scorers are
**retrieval-recall@k** proxies: a question is "correct" if any retrieved
document carries the gold evidence id (or substring-matches it). This is
deliberately conservative -- it surfaces retrieval correctness without
needing an LLM judge, which keeps the v0.1 launch reproducible without
API keys.

Full LLM-judge scoring (rubric-item scoring for BEAM, judge-LLM accuracy
for LoCoMo / LongMemEval) is wired through a swappable `judge` callable
slated for v0.2.

**Metric applicability (`substring_recall_supported`).** Some benchmarks
(e.g. BEAM) have prose gold answers, so the substring proxy is structurally
invalid -- every benchmark declares `substring_recall_supported`. The
**published, rankable surfaces withhold the score automatically** when it's
False: the comparison table shows `n/a*`, `memrank submit`'s terminal + summary
show `n/a (judge required)` (summary `composite` is `null`), and `report`
withholds the composite and the per-ability/per-category tables.

The **detailed/diagnostic JSON tiers** (per-cell `{adapter}__{benchmark}.json`
and each compare row) intentionally keep the raw `composite` for inspection --
but always paired with `substring_recall_supported: false` (and the compare
artifact's `metadata.quality_metric: "withheld (judge required)"`). **Contract
for consumers: `composite` is a valid quality score only when
`substring_recall_supported` is true; otherwise rank from a judged run.**

**A published row requires a complete record, not a score.** The leaderboard admits
any run whose provenance and quality declarations are complete, and then reports
whatever quality it has: the judged score, a self-contained composite, or `withheld`.
It does not require a `composite`, which the three external benchmarks stopped
defining -- requiring one silently dropped every judged run of them between
2026-08-13 and 2026-08-25. A run with no quality number still publishes its latency,
cost and token measurements, which are real measurements regardless.

**One engine under two configurations is two rows on one board.** Row identity is the
adapter, the transport, *and* the engine's configuration -- the extractor LLM, embedder,
context budget and retrieval settings it ran with. So two arms of one engine that differ only
in their extractor -- a deterministic built-in versus a hosted model -- rank against each other
rather than one replacing the
other. Engine *version* is deliberately excluded: a rebuild of one configuration is a
newer run of the same thing under test and replaces its row. Both rows currently publish
under the adapter's name, and are told apart by `config_hash` in their provenance.

**Slice evaluations are plumbing, not measurements.** A `smoke`/`mini` slice
(`beam:100k-smoke`, `locomo:mini`) exists to debug ingest, retrieval, judging and
cloud dispatch cheaply -- it selects the *first* N units of the dataset, and the
first units are not a fair sample. Measured on the first full judged BEAM 100k
tier (run `20260813-184519__beam__100k__c37986`): conversation 1 scores 0.318,
the first five average 0.217, the full 20-conversation tier 0.158 -- a smoke
number flatters every engine by ~2x. So **a slice number is never quoted as a
score; measurement claims come from full tiers.** Two structural guards make
this more than a convention: the leaderboard's `board_key` segregates rows by
tier and slice, so slice numbers cannot blend into tier comparisons; and the
bias is positional and therefore identical across engines, so same-slice
*rankings* stay directionally useful for debugging even though their absolute
values are not. (Decision recorded closing M6 of
the BEAM protocol-fidelity plan.)

## Latency

The runner wraps every adapter `ingest()` and `retrieve()` call with the
`LatencyCollector.track` context manager. Wall-clock time (perf_counter)
is recorded into per-bucket samples; `as_metrics()` computes p50/p95/p99
via linear interpolation on the sorted distribution.

Adapters MAY record additional internal-only timings (e.g., AtomicMemory's
extraction phase) by calling `LatencyCollector.record` directly. These
appear in the per-cell JSON but are not part of the headline.

**Transport matters.** An in-process SDK adapter incurs no network or
serialization overhead; an HTTP adapter does. Latency is therefore only
directly comparable *within* a transport class. Every row records its
`transport` (`http` / `sdk` / `in-process` / `translator`); read latency alongside it and do
not rank an SDK engine against an HTTP engine on raw latency without saying so.

`translator` is the class for an engine reached through a vendor-written program implementing
[the adapter contract](adapter-contract.md) -- the route by which memrank evaluates an engine it has
never seen. A translator is an extra process and an extra hop, so its measured latency includes
overhead a directly-driven engine never pays. Naming it as its own class is what stops a translator
row being ranked against a direct one; quality metrics are unaffected and compare across everything.

Translators MAY report `engine_ms` per call -- their own claim about time spent inside the engine,
excluding the translator. When present it is recorded beside the wall-clock figure as
`ingest_engine_p50_ms` / `retrieve_engine_p50_ms` (and p95), so a reader can see how much of the
measurement was harness rather than engine. It is a *reported* number, not a measured one: memrank
cannot verify it, and it is never the headline.

## Tokens

Adapters call `TokenCollector.record(label, total_tokens)` after each LLM
call. Buckets `query` and `ingest` map to the four required keys in
`token_metrics()`.

**Absent is not zero.** An adapter whose engine surfaces no usage data records nothing, and the
bucket reports `null` -- not `0.0`. The distinction is the whole point: zero is a claim that the
engine consumed no tokens, while null admits nobody counted. Of the engines measured so far only
some report usage at all, so conflating the two would fabricate an efficiency win for every engine
that simply stays quiet. `compare._engine_tokens` renders an unmeasured cell as `n/a`; a genuine
measured zero renders as zero.

## Retrieval token budget -- the fairness control

`--token-budget` (default 5000) caps **two** things: the `$/query` estimate, and the context text
actually handed to the reader on a judged run. The second is the one that matters methodologically.

Without a shared cap, "better recall" and "returned more text" are indistinguishable -- an engine
could win simply by injecting a larger prompt. Holding every target to the same budget means a row
reflects *what a system chose to retrieve*, not *how much*. This is the field problem
memrank exists to answer: vendors self-publish at a different retrieval token budget per row, and
no disinterested party has re-run them under one fixed judge and matched budgets.

Truncation is hard: the concatenated context is cut at the budget, mid-sentence if necessary. Each
judged query records `context_tokens_sent` and `context_truncated`, so a context-starved run is
visible in the artifact rather than silent.

**One benchmark-scoped exception.** A benchmark whose own protocol hands the reader everything
retrieval returned may declare it (`Benchmark.context_policy = "uncapped"`); **BEAM and
LongMemEval both do.** BEAM, because every published BEAM harness -- including BEAM's own baselines
-- runs uncapped, and a capped run of it is not that benchmark. LongMemEval, because its harness
truncates only at the model window and never at a fairness budget: measured, the 5,000-token
default bit on 8/8 queries and the evidence reached the reader on **0 of 5** scoreable questions
while retrieval itself scored recall_all@10 = 1.0, so a judged run under that cap would have
measured the truncation rather than the memory. The promotion applies to every target
symmetrically, so rows within the benchmark stay comparable; what is given up is
budget-normalization against other benchmarks' rows
(a standing decision recorded with the benchmark).

## Baseline arms

Three controls belong beside every engine. A row without them does not test the hypothesis --
*external memory makes the decisive difference when the knowledge base exceeds the model's context
window, and is worth its tokens against a naive baseline that just reads what it can.*

| Target | Retrieves | Budget | Question it answers |
|---|---|---|---|
| `no-context` | nothing | n/a | Does the reader already know the answer? |
| `fixed-context` | the corpus, unranked, ingest order | **matched** | Does ranked retrieval beat reading the first N tokens? |
| `full-context` | the corpus, uncapped | uncapped | Is memory needed at all when everything fits? |

`full-context` is not the only uncapped target. Vendor-configuration targets are uncapped too, by
definition -- they reproduce a vendor's own depth rather than this cap -- and they never enter the
leaderboard.
Today those are `mem0` and `hindsight` -- every BARE vendor ref, because since 2026-08-19 a bare
ref means the configuration that vendor ships. memrank's comparison arm carries a suffix:
`hindsight:matched` is the ranked hindsight row, and mem0 has no ranked row at all, since both of
its matched variants moved to the research lane. A target's `context_budget`, not its name, is what
says which it is.

`fixed-context` is the arm that belongs on every row, and it is the *token-matched* one by design: same context
size as the engine under test, so the only variable is selection. `full-context` is deliberately rare
-- a benchmark whose knowledge base fits inside a current context window cannot hold headline status,
which is why LoCoMo (16k-26k tokens) is runnable but labelled non-discriminative.

Two honest limits. **Ingest order is not neutral**: `fixed-context` reads from the start, so a corpus whose
answers cluster late is disadvantaged in a way ranked retrieval is not. And **`no-context` is only
meaningful judged** -- unjudged it is scored on retrieval alone, and since it retrieves nothing it can
only score on *negative* queries (the ones a system should decline), which says nothing about memory.
The runner emits a notice when that happens.

`word-overlap` is a separate thing: naive token-overlap retrieval, a dumb-*memory* floor rather than a
no-retrieval or in-prompt control.

### What each arm is called in the literature

So a reader can map these rows onto other people's tables. The arms were `none`, `baseline` and
`icl` until 2026-08-19; two were renamed again on 2026-08-20.

**Two of these names are ours, not the field's**, and the table says which. Where our name differs
from the published one, the citation identifies the CONDITION -- it is not the source of the name.

| Ours | Published counterpart |
|---|---|
| `no-context` | **Our name, chosen for clarity.** The condition is well established: open-domain QA calls it "closed-book" ([Roberts et al., EMNLP 2020](https://aclanthology.org/2020.emnlp-main.437/)), used verbatim as an arm name by [LOFT](https://aclanthology.org/2025.findings-naacl.374.pdf); agent-memory work calls it "no-memory" ([MemDelta](https://arxiv.org/html/2606.29914)'s lower bound is `S0: No Memory`). No paper uses "no-context" as a defined condition name. We prefer it because "closed-book" is an exam metaphor that is opaque to a reader who does not already know it. |
| `word-overlap` | Attested as an arm name: LoCoMo-style baseline sets list "BM25 retrieval" and "word-overlap retrieval" as **separate** arms, and ours is the second. **Not BM25** -- the score is an unweighted set intersection, no IDF, no term frequency, no length normalisation. [BEIR](https://arxiv.org/abs/2104.08663)'s term for the family above this one is "lexical", which is the level, not the instance. |
| `fixed-context` | Closest to LoCoMo's "Base" and MemGPT's "fixed-context baselines". The budget-matching practice itself is argued for in [Laitenberger, Manning & Liu, EMNLP 2025](https://arxiv.org/abs/2506.03989). **Caveat:** MemGPT's term means bounded by the *model's context window*; ours is bounded by the *retrieval token budget*. |
| `full-context` | Standard as-is in agent-memory work -- [Mem0](https://arxiv.org/abs/2504.19413) and [Zep](https://arxiv.org/html/2501.13956v1) both use the phrase. Core NLP calls the same condition "long-context (LC)". |

It was `icl` until 2026-08-19, which was simply wrong: in-context learning means few-shot
*demonstrations* that induce a task ([Brown et al. 2020](https://arxiv.org/pdf/2005.14165);
[Dong et al., ACL 2024](https://arxiv.org/abs/2301.00234)), not injected knowledge. No memory
benchmark surveyed runs a few-shot control at all, so nothing was lost by dropping the name.

`word-overlap` was briefly `lexical` (2026-08-19 to 2026-08-20). Two problems: it named BEIR's
family rather than the instance, and this repo already uses "lexical" for its ordinary meaning --
real engines describe their own retrieval as "lexical and graph" walks. One word cannot be both an arm
name and a property several engines have.

### Two arms we do not have, and why

Recorded so their absence reads as a decision rather than an oversight.

**Oracle / gold-evidence retrieval** -- the ceiling that separates "retrieval is hard" from "reading
is hard". [LongMemEval](https://arxiv.org/abs/2410.10813) ships it as a dataset variant and builds
its headline claim on it: models decline 30-60% reading full history versus oracle evidence. We do
not have it because it needs per-benchmark gold-evidence labels, which not every benchmark here
carries.

**Random retrieval** -- [MemDelta](https://arxiv.org/html/2606.29914)'s control, "random chunks...
controls for 'having text' vs. 'relevant text'". Nothing we ship separates a memory system's
ranking from the mere presence of context. Cheap to add; not yet added.

## Cost

v0.1 does not bake in a cost table. The receipt records the LLM provider
and model name; downstream tools can join token usage with per-model
pricing to compute $/query. v0.2 will integrate LiteLLM's
`x-litellm-response-cost` header for direct cost capture.

## Reproducibility receipt

Every run writes a `Receipt` (see `memrank/provenance/receipt.py`) capturing:

- Memrank version + git SHA
- Adapter name + version + engine version
- Benchmark name + dataset version (HuggingFace id or file SHA)
- Seed
- Wall-clock timestamps + duration
- Host fingerprint (hostname, platform, Python version)
- Env-var fingerprints (sha256 of values, never plaintext)
- Evidence class and publication eligibility, derived from how the engine actually executed

### Development observations versus reproducible evidence

`memrank submit TARGET EVAL` starts a source-bound named target from the checkout declared in its
central target file. It is the engine-development loop: each run gets a fresh native process, but it
does not run an immutable executable artifact. Its receipt therefore records the source commit, dirty
flag, an opaque hash of tracked and untracked changes, native platform, and launcher identity as
`development_observation` with `publishable: false`. The machine-local checkout path is excluded from
the receipt and synchronized record.

Clean development observations retain their scores and may synchronize into a private organization
for comparison. Dirty-tree observations stay local. Public leaderboard ingestion excludes both. A
clean Git tree does not promote one to reproducible evidence: a commit identifies source, not the
compiled executable or its toolchain.

Likewise, `--on none` against an already-running HTTP engine is an `endpoint_observation` unless the
engine exposes a resolved executable identity. This mode remains useful for rapid diagnostics, but
its long-lived state and unpinned process make it ineligible for publication.

Artifact-backed local and cloud runs remain the evaluator path. Their image digest identifies the
executable artifact; publication still requires the dataset, configuration, models, platform, and
methodology pins described elsewhere in this document.

The vendor-neutral charter requires every published number to ship with
its receipt. If a third party cannot reproduce a Memrank-published number
within the receipt's noise band, AtomicStrata investigates within 7 days.

## Determinism

Adapters MUST be deterministic given the same seed, or document their
non-determinism explicitly. The runner re-seeds `random` per cell. Stoch-
astic engines (e.g., LLM-extraction with non-zero temperature) should
either pin temperature to 0 or run multiple seeds and report the spread.

# The systems that ship

A [system](../reference/system.md) is the thing under test. Memrank ships eleven of them, so you
can take a number before you have wired anything up, and so every system's row has controls beside
it. One page each.

| System | Key | What it is | What it needs |
|---|---|---|---|
| [TFIDF](tfidf.md) | `tfidf` | keyword search weighted by how rare each word is: the classic lexical baseline, in plain Python | nothing |
| [BM25](bm25.md) | `bm25` | Okapi BM25, the lexical retriever the field ranks against, in plain Python | nothing |
| [WordOverlap](word-overlap.md) | `word-overlap` | keyword retrieval in about thirty lines: the floor a real memory system has to beat | nothing |
| [NoContext](no-context.md) | `no-context` | a control that retrieves nothing, so the reader has to answer from what it already knows | nothing |
| [FixedContext](fixed-context.md) | `fixed-context` | a control that hands over the corpus unranked, cut off at the same token budget the system beside it was held to | nothing |
| [FullContext](full-context.md) | `full-context` | a control that hands over the whole corpus with no cap: the ceiling retrieval is aiming at | nothing |
| [AtomicMemory](atomicmemory.md) | `atomicmemory` | AtomicStrata's own memory engine, driven over its HTTP API | a running engine |
| [Hindsight](hindsight.md) | `hindsight` | Vectorize.io's open-source agent memory, driven over its HTTP API | a running engine |
| [Supermemory](supermemory.md) | `supermemory` | Supermemory AI's memory API, driven over HTTP against the self-hosted server | a running engine |
| [Mem0](mem0.md) | `mem0` | mem0's open-source memory layer, as a library in your own process or over HTTP | the SDK, or a running engine |
| [Native](native.md) | `native` | a client for any engine that speaks memrank's own contract | a running translator |

`memrank.catalog()` prints the same list at runtime, and `tfidf`, `bm25`, `word-overlap` and the
three controls are the six that need nothing at all.

## The standard every page follows

The real name with its string key, and under it the one block that loads it; one line saying
what it is; how it works, in simple terms; why it matters; what it needs; references. Nothing
beyond what makes the concept clear.

The words a page leans on -- system, [evaluation](../reference/evaluation.md),
[task](../reference/task.md), [trace](../reference/trace.md),
[measure](../reference/measure.md), [run](../reference/run.md),
[result](../reference/result.md) -- are each defined once in
[the reference](../reference/README.md) and linked from here rather than explained again.

A page for a system that needs a running service shows how to construct it and stops there. No
page prints a result: what a number licenses you to say is
[methodology](../methodology.md)'s subject, not a system's.

## Using one

Pick a system, pick an [evaluation](../evaluations/README.md), and hand the one to the other.

```python
from memrank.evaluations import Demo
from memrank.systems import TFIDF

result = Demo().run(system=TFIDF())
```

## Where to go from here

- [system](../reference/system.md) -- what a system is, and the four kinds.
- [Adding a system](../systems.md) -- bringing your own thing under test.
- [The evaluations that ship](../evaluations/README.md) -- what to run one against.
- [Methodology](../methodology.md) -- the controls, the token budget, and what a value licenses.

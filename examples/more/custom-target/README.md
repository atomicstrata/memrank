<a id="a-target-memrank-does-not-ship"></a>
# Register a custom target

Use this example to make a custom implementation available to the
[command line](../../../docs/misc/command-line.md). For direct Python evaluation, pass a
[`Memory`](../../02-your-own-system/README.md) instance to `evaluation.run(system=...)`.

The example `Recency` implementation returns the `k` most recently ingested documents and ignores
the query. It demonstrates integration mechanics and runs offline without a service or API key.

<a id="the-three-doors"></a>
## Integration options

| Option | You write | You get | Shown in |
|---|---|---|---|
| **Instance** | a `Memory` subclass | a score, from a script | [`run.py`](run.py) |
| **Registration** | the same class, plus one `register_adapter` call | a catalog ref: `memrank submit`, receipts, sweeps | [`recency_plugin.py`](recency_plugin.py) |
| **Translator** | a program serving five HTTP endpoints, in any language | the same, without writing Python at all | [`../native-adapter/`](../native-adapter/README.md) |

The first two use the same local implementation. Pick the third when your engine is not Python,
or when you would rather memrank never imported your code.

## Door 1 -- an instance, no setup

```bash
python examples/more/custom-target/run.py
```

The run takes any `Memory` instance, so nothing has to be configured, registered or named. The script prints:

```
composite: 0.800  (recency × demo)
engine ref:  None <- None by design: no ref was given, so none is invented
```

Without a catalog ref, this run has no variant digest or build provenance. Use it as a local
check, not as a reproducible published comparison.

## Door 2 -- registration, so the CLI knows it

Three settings, once:

```bash
export PYTHONPATH=$PWD/examples/more/custom-target
memrank config set adapters.plugins recency_plugin
memrank config set targets.path $PWD/examples/more/custom-target/targets
```

`adapters.plugins` names a module to import; importing [`recency_plugin.py`](recency_plugin.py)
runs its `register_adapter(...)` call. `targets.path` is where memrank looks for descriptors
besides its own. `PYTHONPATH` is the one that is not a memrank setting, so it does not persist --
put it in your shell profile.

The target is now available in the catalog:

```bash
memrank targets ls | grep recency
memrank submit recency demo --on local
memrank runs show <id>
```

Pass `--on local` explicitly: `defaults.on` may be `cloud`, and the hosted platform cannot load an implementation that exists only on your machine.

### What registration actually asks for

`AdapterRegistration` takes the class and its configuration records, with required
fields -- so a registration that forgets one is a `TypeError`
at the call rather than a `KeyError` at planning time, or, for `provenance`, nothing at all.

An in-process implementation uses
`AdapterRegistration.in_process(...)`, which requires its credential requirements and provenance. An engine memrank has to *start* -- a
container, or a checkout it launches -- states more, because those rows are what start it. See
[`../../../docs/systems.md`](../../../docs/systems.md).

## The demo: a corpus too small to tell two engines apart

Run both arms against the same benchmark:

```bash
memrank submit recency,word-overlap demo --on local
```

Both score **0.800**, and that is not a bug in either engine. The `demo` scenario holds two
sessions, so at the default `k=10` *every* document is retrieved -- an engine that ranks perfectly
and one that ignores the question entirely return the same set, and no metric can separate them.

Reducing the retrieval limit changes the comparison:

```bash
memrank submit recency,word-overlap demo --on local --k 1
```

| k | `recency` | `word-overlap` |
|---|---|---|
| 1 | 0.200 | 0.800 |
| 2 | 0.400 | 0.800 |
| 3 | 0.800 | 0.800 |
| 10 | 0.800 | 0.800 |

A small corpus with a large retrieval limit can hide ranking differences. Choose a corpus size
and retrieval limit that test the behavior you care about; this example does not establish
performance on a larger workload.

## Writing your own

Copy [`recency_plugin.py`](recency_plugin.py) -- a `Memory` subclass called `Recency` -- and
replace the four method bodies.

| Method | Responsibility | Important constraint |
|---|---|---|
| `prepare` | drop everything for this unit | leaked state does not raise -- it inflates every score after the first |
| `ingest` | store the documents | -- |
| `retrieve` | return `k` documents, **ranked** | `recall@k` reads the order; an unranked list scores worse than a bad ranking |
| `cleanup` | release whatever the unit held | -- |
| `token_metrics` *(optional)* | the four required keys, where the engine is told what it spent | `None` is not `0.0` -- absent is the absence of a measurement |

Latency is not in the table because it is not asked of an engine: memrank times every ingest and
retrieve at its own call boundary. A translator that can see time spent inside its engine declares it through `declared_latency()`, as samples, under its own bucket name.

Then swap the descriptor in [`targets/`](targets/) for one naming your adapter, and point
`adapters.plugins` at your module. Nothing in memrank changes.

## What registration confers, and what it should not

Registration decides where your code lives. It should not decide what may be claimed about a
measurement -- the evidence class is meant to derive from how the *artifact* was bound, not from who
wrote the adapter.

Look at what this run actually records, though:

```json
"evidence": {"class": "reproducible_evidence", "publishable": true}
```

**That is wrong, and it is a known gap rather than a property of this example.** The engine is
twenty lines found on `sys.path`, with no version and no resolvable origin; nothing about it is
reproducible by anyone else. It is marked publishable because the evidence rule reads a `type` the
registration itself supplied -- `provenance.type: "application"`, which is the honest description of
an in-process engine -- and because a receipt with no dynamic pin defaults to the *strongest* claim
rather than the weakest.

Two defects cause this: missing evidence assessment defaults to the strongest claim (a receipt with no evidence
assessment defaults to publishable), and identity is asserted by the adapter rather than derived
from what executed. These defects also affect externally registered adapters.

Until they are: **do not read `publishable: true` on a plugin-backed run as a fact about the
engine.** A run of an engine that lives on one laptop is a development observation whatever the
receipt says.

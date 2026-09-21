# The memrank system contract, v1

This is the wire contract between memrank and a **translator** -- a program you write that
memrank drives as the system under test, and which forwards to your memory system however it
likes.

Write one and memrank can measure a system it has never seen, in any language, with no fork and
no pull request. memrank never imports your code, never resolves a version of it, and never
needs to know what language it is in. The contract is a process, not a package.

**One note on names.** This file is still called `adapter-contract.md`, the JSON field that
names your translator is still `adapter`, and the command line still calls a named system a
*target*. Those are wire and command-line facts and they have not moved; *system* is the word
the Python surface uses for the same thing. Renaming the file and the field is a later change.

Companion documents: [adding a system](adding-adapters.md) (when to write a translator versus a
class in this tree) and [methodology.md](methodology.md) (what each measured axis means, and the
comparability rules a translator is subject to).

---

## 1. What a translator is, and why the shapes are fixed

memrank talks to a system as an HTTP service. A translator is an HTTP service too, so memrank
cannot tell the difference -- it provisions it, waits for readiness, drives the four lifecycle
operations, and tears it down using exactly the machinery that runs a system memrank ships.

What a translator does *inside* is entirely yours: call an SDK, open a socket, spawn a
subprocess, render documents into whatever shape your system wants, page through results,
retry. That is the part that genuinely cannot be configuration, and it belongs to you.

What is **not** yours is the shape of what comes back. memrank is a comparator: a measure
computes recall@k against ground truth, and a reader puts two systems' values side by side.
That only means something if every system answers in the same shape. So the request and
response bodies below are fixed, and a field that is absent is an error rather than a default.

This is deliberately unlike a self-describing protocol such as MCP, where a server announces its
own schemas. MCP can afford that because a language model consumes its output and can interpret
anything. Nothing downstream of memrank can interpret anything: it computes.

## 2. Transport and lifecycle

A translator serves HTTP on a port memrank tells it to bind, and implements five endpoints under
`/memrank/v1/`. memrank drives them in this order, once per **unit** -- the stretch of tasks
that share state, which the Python surface calls a group:

```
GET  /memrank/v1/describe        once, at startup -- also the readiness probe
POST /memrank/v1/prepare         per unit
POST /memrank/v1/ingest          per unit, possibly several times
POST /memrank/v1/retrieve        per task in the unit
POST /memrank/v1/cleanup         per unit
```

All request and response bodies are `application/json`, UTF-8.

**Readiness.** memrank polls `GET /memrank/v1/describe` until it answers with a status below 500,
then starts the run. Do not answer before your system can actually serve traffic: "ready" means
"can answer the task memrank is about to put", not "the port is open". A translator that reports
ready too early turns a start-up failure into a measurement.

## 3. The `Document` shape

`Document` is memrank's canonical unit of content, used in both directions. It mirrors
`memrank.core.Document`:

```json
{
  "id": "conv-42-turn-7",
  "content": "The full text payload.",
  "user_id": "u_1234",
  "timestamp": "2026-03-11T09:15:00Z",
  "context": "optional free-form scene/entity context",
  "messages": [
    {"role": "user", "content": "..."},
    {"role": "assistant", "content": "..."}
  ],
  "metadata": {"doc_id": "conv-42-turn-7"}
}
```

| Field | Type | Notes |
|---|---|---|
| `id` | string | Required. Stable identifier. |
| `content` | string | Required. The canonical text payload. |
| `user_id` | string \| null | The isolation scope for this document. |
| `timestamp` | string \| null | ISO-8601. **When the content happened**, not when it was ingested. |
| `context` | string \| null | Optional free-form context. |
| `messages` | array \| null | Present when the source has multi-turn structure. |
| `metadata` | object | Always present, possibly empty. |

**On `timestamp`.** If your system supports temporal reasoning, pass this through. A system that
ignores it and stamps ingestion time instead dates every memory to the moment of the run, which
silently destroys every temporal task in the evaluation.

**On `messages` versus `content`.** Both describe the same material. `content` is the canonical
text; `messages` is the structured form when one exists. Use whichever your engine wants -- if it
takes a message list, use `messages`; if it takes free text, use `content`. Rendering one into the
other is your job, and is exactly the kind of system-specific transformation this contract exists
to let you own.

## 4. The endpoints

### `GET /memrank/v1/describe`

Identity and capabilities. Called once at startup, and used as the readiness probe.

```json
{
  "contract_version": "v1",
  "adapter": {"name": "myengine-translator", "version": "0.1.0"},
  "engine": {"name": "myengine", "version": "1.4.2"},
  "components": {
    "llm": {"provider": "anthropic", "model": "claude-sonnet-4-5"},
    "embedder": {"provider": "voyage", "model": "voyage-4-large", "dims": 1024}
  },
  "capabilities": {
    "graph_snapshot": false,
    "context_budget": "matched"
  }
}
```

| Field | Required | Notes |
|---|---|---|
| `contract_version` | yes | Must be `"v1"`. memrank refuses a version it does not implement. |
| `adapter.name` / `.version` | yes | Your translator's own identity, recorded in the receipt. |
| `engine.name` / `.version` | yes | The system under test, under the wire's own older field name. Use `"unknown"` only if you genuinely cannot determine it. |
| `components.llm` | yes | `{provider, model}`, or `null` if the system uses no LLM. |
| `components.embedder` | yes | `{provider, model, dims}`, or `null` if the system has no embedder. |
| `capabilities.graph_snapshot` | yes | Whether `retrieve` returns `raw.graph_snapshot`. |
| `capabilities.context_budget` | yes | `"matched"` for every real engine. See section 6. |

**`components` is the authority, and this is the important part.** For a system memrank ships,
memrank injects component configuration through env vars it knows by name and the manifest merely
*asserts* what was configured. It cannot do that for yours -- it does not know which variables your
process reads. So the direction inverts: **you** configure your system inside your own launch
command, and you **report** the result here. memrank records what you report and marks the run
`verified: "engine"`, which is a stronger provenance claim than most shipped systems can make.

A `null` component means "this system has no such part" -- a positive statement. Do not use `null`
to mean "I did not check": report the real value or fail to start.

### `POST /memrank/v1/prepare`

Begin a fresh unit. **Nothing ingested under a previous `isolation_unit` may be visible
to this one.** How you achieve that is yours -- a namespace, a fresh collection, a tenant id, a
wiped directory.

```json
// request
{"isolation_unit": "locomo-conv-17"}

// response
{}
```

Isolation is not a nicety. If state leaks between units, every value after the first is measuring a
system that has already seen the answers.

### `POST /memrank/v1/ingest`

Load documents into the current unit. May be called more than once per unit.

```json
// request
{"documents": [ {Document}, ... ]}

// response
{"usage": {"total_tokens": 4210}, "engine_ms": 8123.4}
```

| Field | Required | Notes |
|---|---|---|
| `usage.total_tokens` | no | Omit the whole `usage` object if you cannot measure it. See section 5. |
| `engine_ms` | no | Milliseconds your system spent, excluding your own overhead. See section 7. |

### `POST /memrank/v1/retrieve`

Answer one task's prompt against the current unit.

```json
// request
{
  "query": "Where did we agree to meet?",
  "k": 10,
  "user_id": "u_1234",
  "query_timestamp": "2026-03-14T17:02:00Z"
}

// response
{
  "documents": [ {Document}, ... ],
  "raw": { ... },
  "usage": {"total_tokens": 812},
  "engine_ms": 143.2
}
```

| Field | Required | Notes |
|---|---|---|
| `documents` | yes | **Ranked, best first.** The order IS the measurement: it is the rank, and memrank never re-sorts. |
| `raw` | yes | Your system's untouched response. It lands on the trace as what the system declared, and is never read as a measurement. Any JSON object. |
| `usage` | no | As above. |
| `engine_ms` | no | As above. |

`query_timestamp` may be `null`. When present it is the moment the task is being put, which
matters for a system that reasons about time.

**On `k`.** It is a request for the top *k*, and most systems have a matching parameter. If yours
does not model result counts at all -- some pack a token budget instead -- return what it returns and
say so in your README. Do not pad the list to reach `k`, and do not invent scores. memrank caps
every target at the same `--token-budget` regardless, which is the fairness control that makes the
comparison legitimate.

Put a relevance figure, if you have one, in each returned document's `metadata.score` -- report
what your system computed, never invent one.

### `POST /memrank/v1/cleanup`

End the current unit and release its state.

```json
// request
{}

// response
{}
```

Called even when a unit fails -- a failed task is a trace with a reason, and the run does not stop
on it. Make it safe to call twice, and safe to call before any `prepare`.

## 5. Token usage: absent is not zero

If your system reports token consumption, pass it through as `usage.total_tokens`. If it does not,
**omit the `usage` object entirely.**

Do not send `{"usage": {"total_tokens": 0}}`. Zero is a claim that your system consumed no tokens.
Absence is an admission that nobody counted. memrank keeps these distinct all the way out: a value
nobody measured is `None`, and a measured zero is zero.

## 6. Context budget

`capabilities.context_budget` must be `"matched"` for any real memory system. It means the retrieved
context you return will be capped at the shared `--token-budget` that every system is held to -- the
project's central fairness control, so a system cannot win by returning more text.

The other two values exist only for memrank's own baseline arms and are not available to a
translator: `"uncapped"` for the full-context control, `"none"` for the no-memory control.

## 7. Latency, and why a translator is its own transport class

memrank measures wall-clock time around each call it makes to you, at its own call boundary. That
measurement necessarily includes your translator's own overhead -- an extra process and an extra
network hop that a directly-driven system does not pay.

Rather than pretend this is comparable, memrank declares translator-backed targets as
`transport: translator`, and [methodology.md](methodology.md) already rules that latency compares
only within a transport class. So a translator is compared against other translators, and never
silently ranked against a system memrank drives directly. Quality measures are unaffected and
compare across everything.

Report `engine_ms` when you can. It lands on the trace as something the system declared, beside
memrank's own wall-clock figure, so a reader can see how much of the measured time was yours -- and
it is the number to quote when you want to talk about the system rather than the instrument.

## 8. Errors

Return a non-2xx status with a JSON body:

```json
{"error": "myengine rejected the batch: document 12 exceeds the 100k character limit"}
```

memrank records the failure on that task's trace, with the step and your message, and carries on.
**Never swallow an error and return an empty result.** An empty `documents` list is a legitimate
answer meaning "nothing matched", and a system that returns it on failure measures exactly like the
no-memory control arm -- which reads as a real, publishable finding rather than a broken
integration. This has happened before to a system memrank ships and went unnoticed across every run
until the numbers were audited.

## 9. Declaring a target

*Target* is the command line's word for a named system. Put the descriptor next to the translator
it launches, in a folder you own:

```
~/evals/
├── myengine.yaml
└── translators/
    └── myengine.py
```

```yaml
# ~/evals/myengine.yaml
schema_version: 1
name: myengine:dev
kind: stack
interface:
  adapter: native          # the built-in client for this contract
  transport: translator
binding:
  kind: source             # root defaults to "." -- this descriptor's own directory
launch:
  command: "python translators/myengine.py --port {port}"
  requires: [translators/myengine.py]
network:
  port: 8099
  readiness: {path: /memrank/v1/describe}
```

Tell memrank where to look, once:

```bash
memrank config set targets.path ~/evals        # or MEMRANK_TARGETS_PATH, or several, os.pathsep-separated
memrank targets ls                             # myengine:dev, with the directory it came from
memrank targets verify myengine:dev            # check your translator against this contract
memrank submit myengine:dev demo
```

**There is no absolute path in the descriptor**, which is the point: the folder can be copied,
shared, or committed, and a colleague needs only their own `targets.path` line. `binding.root`
defaults to the directory the descriptor was read from, and a relative value is resolved against
it, so `launch.command` runs from the folder root.

**The folder can be anything.** Its own repo, an uncommitted scratch directory, or a `bench/`
subfolder inside the engine's repo -- memrank records which it got rather than requiring a shape. If
there is a git repository it records the commit, dirty flag and working-tree delta (from a
subfolder, that is the *containing* repo's commit -- the right answer for that layout). If there is
not, it records `memrank:workspace_unversioned` and no commit, rather than an empty one. Both are
`development_observation`.

One caveat for the `bench/`-inside-the-engine layout: checking out an old engine revision takes the
translator with it, so it cannot evaluate revisions that predate the integration. A separate folder
does not have that problem.

`{port}` expands to `network.port`. The command is split into argv and executed directly in
`binding.root` -- there is no implicit shell, so use `sh -lc '...'` explicitly if you need one.
`requires` is optional and names files that must exist, giving an early, clear error on a wrong
directory.

Do **not** declare a `components:` block on a native target. memrank cannot deliver component
configuration to a system whose environment it does not know, so declaring one is refused; your
launch command configures the system and `describe` reports it.

### Credentials your translator needs

Name them, and memrank delivers them into your process's environment:

```yaml
secrets: [MYENGINE_TOKEN]                    # your translator reads MYENGINE_TOKEN

secrets:                                     # or a rename, if the two differ
  MYENGINE_TOKEN: AUTH_BEARER

secrets: [MYENGINE_USER, MYENGINE_PASSWORD]  # whatever shape your auth takes
```

Each is resolved through memrank's one chokepoint -- process environment, then org secrets, then the
encrypted wallet -- so `memrank secrets set MYENGINE_TOKEN` is enough and the value never appears in
your shell history, a config file, or the run record. A declared secret that resolves nowhere is
refused at preflight, naming every missing one at once, rather than failing inside your translator
on the first call.

memrank interprets none of these. It does not know or care whether your system wants a bearer
token, a username and password, or three fields it has never heard of.

### Comparing against the catalog

A translator-backed target can sweep alongside anything else:

```bash
memrank submit myengine:dev,mem0,hindsight demo
```

Each target is provisioned and torn down before the next begins. Quality compares across all of
them; latency compares only within a transport class, so your `translator` row is never silently
ranked against a directly-driven `http` system (section 7). Evidence is per row -- yours is a
`development_observation` while the catalog rows keep whatever they had.

## 10. Evidence class

A source-bound target runs locally and is recorded as `development_observation` with
`publishable: false`. That is not a judgement about your system -- it is that memrank launched code
from a mutable working tree, so the run identifies a checkout rather than a reproducible artifact.
Runs like this never sync to the org universe when the tree is dirty, and never reach the public
leaderboard.

Publishable evidence requires a pinned, reproducible artifact. That path is not open to translators
yet; see [adding a system](adding-adapters.md) for the in-tree route in the meantime.

## 11. Conformance

`memrank targets verify <ref>` launches your target and asserts this document: the `describe` shape
and contract version, that a second `prepare` does not see the first unit's documents, that
`retrieve` returns ranked documents, and that usage is either absent or a number. Run it before you
trust any value your translator produces.

A reference implementation -- about a hundred lines, standard library only -- is in
[`examples/native-adapter/`](../examples/more/native-adapter/). It wraps an in-memory dictionary rather
than a real engine, so it is a template to copy, not a system worth measuring.

# The memrank adapter contract, v1

This is the wire contract between memrank and a **translator** -- a program you write that memrank
drives like any other engine, and which forwards to your memory system however it likes.

Write one and memrank can evaluate an engine it has never seen, in any language, with no fork and
no pull request. memrank never imports your code, never resolves a version of it, and never needs
to know what language it is in. The contract is a process, not a package.

Companion documents: [adding-adapters.md](adding-adapters.md) (when to write a translator versus an
in-tree adapter) and [methodology.md](methodology.md) (what each measured axis means, and the
comparability rules a translator is subject to).

---

## 1. What a translator is, and why the shapes are fixed

memrank talks to an engine as an HTTP service. A translator is an HTTP service too, so memrank
cannot tell the difference -- it provisions it, waits for readiness, drives the four lifecycle
operations, and tears it down using exactly the machinery that runs a built-in engine.

What a translator does *inside* is entirely yours: call an SDK, open a socket, spawn a subprocess,
render documents into whatever shape your engine wants, page through results, retry. That is the
part of an adapter that genuinely cannot be configuration, and it belongs to you.

What is **not** yours is the shape of what comes back. memrank is a comparator: a scorer computes
recall@k against ground truth, and a leaderboard puts two engines' numbers side by side. That only
means something if every engine answers in the same shape. So the request and response bodies below
are fixed, and a field that is absent is an error rather than a default.

This is deliberately unlike a self-describing protocol such as MCP, where a server announces its own
schemas. MCP can afford that because a language model consumes its output and can interpret
anything. Nothing downstream of memrank can interpret anything: it computes.

## 2. Transport and lifecycle

A translator serves HTTP on a port memrank tells it to bind, and implements five endpoints under
`/memrank/v1/`. memrank drives them in this order, once per benchmark unit:

```
GET  /memrank/v1/describe        once, at startup -- also the readiness probe
POST /memrank/v1/prepare         per unit
POST /memrank/v1/ingest          per unit, possibly several times
POST /memrank/v1/retrieve        per query in the unit
POST /memrank/v1/cleanup         per unit
```

All request and response bodies are `application/json`, UTF-8.

**Readiness.** memrank polls `GET /memrank/v1/describe` until it answers with a status below 500,
then starts the run. Do not answer before your engine can actually serve traffic: "ready" means
"can answer the question memrank is about to ask", not "the port is open". A translator that reports
ready too early turns an engine start-up failure into a benchmark result.

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

**On `timestamp`.** If your engine supports temporal reasoning, pass this through. Engines that
ignore it and stamp ingestion time instead date every memory to the moment of the benchmark run,
which silently destroys any temporal question in the eval.

**On `messages` versus `content`.** Both describe the same material. `content` is the canonical
text; `messages` is the structured form when one exists. Use whichever your engine wants -- if it
takes a message list, use `messages`; if it takes free text, use `content`. Rendering one into the
other is your job, and is exactly the kind of engine-specific transformation this contract exists
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
| `engine.name` / `.version` | yes | The system under test. Use `"unknown"` only if you genuinely cannot determine it. |
| `components.llm` | yes | `{provider, model}`, or `null` if the engine uses no LLM. |
| `components.embedder` | yes | `{provider, model, dims}`, or `null` if the engine has no embedder. |
| `capabilities.graph_snapshot` | yes | Whether `retrieve` returns `raw.graph_snapshot`. |
| `capabilities.context_budget` | yes | `"matched"` for every real engine. See section 6. |

**`components` is the authority, and this is the important part.** For a built-in engine, memrank
injects component configuration through env vars it knows by name and the manifest merely *asserts*
what was configured. It cannot do that for your engine -- it does not know which variables your
process reads. So the direction inverts: **you** configure your engine inside your own launch
command, and you **report** the result here. memrank records what you report and marks the run
`verified: "engine"`, which is a stronger provenance claim than most built-in engines can make.

A `null` component means "this engine has no such part" -- a positive statement. Do not use `null`
to mean "I did not check": report the real value or fail to start.

### `POST /memrank/v1/prepare`

Begin a fresh benchmark unit. **Nothing ingested under a previous `isolation_unit` may be visible
to this one.** How you achieve that is yours -- a namespace, a fresh collection, a tenant id, a
wiped directory.

```json
// request
{"isolation_unit": "locomo-conv-17"}

// response
{}
```

Isolation is not a nicety. If state leaks between units, every score after the first is measuring an
engine that has already seen the answers.

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
| `engine_ms` | no | Milliseconds your engine spent, excluding your own overhead. See section 7. |

### `POST /memrank/v1/retrieve`

Answer one query against the current unit.

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
| `documents` | yes | **Ranked, best first.** This ordering is what recall@k measures. |
| `raw` | yes | Your engine's untouched response, stored in the receipt for forensics. Any JSON object. |
| `usage` | no | As above. |
| `engine_ms` | no | As above. |

`query_timestamp` may be `null`. When present it is the moment the question is being asked, which
matters for engines that reason about time.

**On `k`.** It is a request for the top *k*, and most engines have a matching parameter. If yours
does not model result counts at all -- some pack a token budget instead -- return what it returns and
say so in your README. Do not pad the list to reach `k`, and do not invent scores. memrank caps
every target at the same `--token-budget` regardless, which is the fairness control that makes the
comparison legitimate.

Put a relevance score, if you have one, in each returned document's `metadata.score`.

### `POST /memrank/v1/cleanup`

End the current unit and release its state.

```json
// request
{}

// response
{}
```

Called even when a unit fails. Make it safe to call twice, and safe to call before any `prepare`.

## 5. Token usage: absent is not zero

If your engine reports token consumption, pass it through as `usage.total_tokens`. If it does not,
**omit the `usage` object entirely.**

Do not send `{"usage": {"total_tokens": 0}}`. Zero is a claim that your engine consumed no tokens.
Absence is an admission that nobody counted. memrank keeps these distinct all the way to the
leaderboard, where an unmeasured cell renders as `n/a` and a measured zero renders as zero.

## 6. Context budget

`capabilities.context_budget` must be `"matched"` for any real memory system. It means the retrieved
context you return will be capped at the shared `--token-budget` that every target is held to -- the
project's central fairness control, so a row cannot win by returning more text.

The other two values exist only for memrank's own baseline arms and are not available to a
translator: `"uncapped"` for the full-context control, `"none"` for the no-memory control.

## 7. Latency, and why a translator is its own transport class

memrank measures wall-clock time around each call it makes to you. That measurement necessarily
includes your translator's own overhead -- an extra process and an extra network hop that a
directly-driven engine does not pay.

Rather than pretend this is comparable, memrank declares translator-backed targets as
`transport: translator`, and [methodology.md](methodology.md) already rules that latency compares
only within a transport class. So a translator row is compared against other translator rows, and
never silently ranked against an engine memrank drives directly. Quality metrics are unaffected and
compare across everything.

Report `engine_ms` when you can. It is recorded alongside the wall-clock figure so a reader can see
how much of the measured time was yours, and it is the number to quote when you want to talk about
the engine rather than the harness.

## 8. Errors

Return a non-2xx status with a JSON body:

```json
{"error": "myengine rejected the batch: document 12 exceeds the 100k character limit"}
```

memrank fails the run and surfaces your message. **Never swallow an error and return an empty
result.** An empty `documents` list is a legitimate answer meaning "nothing matched", and an engine
that returns it on failure scores exactly like the no-memory control arm -- which reads as a real,
publishable finding rather than a broken integration. This has happened before to a built-in engine
and went unnoticed across every run until the numbers were audited.

## 9. Declaring a target

Put the descriptor next to the translator it launches, in a folder you own:

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
configuration to an engine whose environment it does not know, so declaring one is refused; your
launch command configures the engine and `describe` reports it.

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

memrank interprets none of these. It does not know or care whether your engine wants a bearer
token, a username and password, or three fields it has never heard of.

### Comparing against the catalog

A translator-backed target can sweep alongside anything else:

```bash
memrank submit myengine:dev,mem0,hindsight demo
```

Each target is provisioned and torn down before the next begins. Quality compares across all of
them; latency compares only within a transport class, so your `translator` row is never silently
ranked against a directly-driven `http` engine (section 7). Evidence is per row -- yours is a
`development_observation` while the catalog rows keep whatever they had.

## 10. Evidence class

A source-bound target runs locally and is recorded as `development_observation` with
`publishable: false`. That is not a judgement about your engine -- it is that memrank launched code
from a mutable working tree, so the run identifies a checkout rather than a reproducible artifact.
Runs like this never sync to the org universe when the tree is dirty, and never reach the public
leaderboard.

Publishable evidence requires a pinned, reproducible artifact. That path is not open to translators
yet; see [adding-adapters.md](adding-adapters.md) for the in-tree adapter route in the meantime.

## 11. Conformance

`memrank targets verify <ref>` launches your target and asserts this document: the `describe` shape
and contract version, that a second `prepare` does not see the first unit's documents, that
`retrieve` returns ranked documents, and that usage is either absent or a number. Run it before you
trust any number your translator produces.

A reference implementation -- about a hundred lines, standard library only -- is in
[`examples/native-adapter/`](../examples/native-adapter/). It wraps an in-memory dictionary rather
than a real engine, so it is a template to copy, not a system to benchmark.

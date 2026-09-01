# Adding an adapter

An adapter wraps a memory engine so Memrank can benchmark it like any other.
This guide walks through the smallest possible adapter and the conformance
contract every adapter must satisfy.

## Which route: a translator, or an in-tree adapter?

There are two ways to make an engine benchmarkable, and the right one depends on who you are.

| | **Write a translator** | **Write an in-tree adapter** |
|---|---|---|
| What you write | a program serving [the adapter contract](adapter-contract.md), in any language | a Python `MemoryAdapter` subclass, in this repo |
| Where it lives | your repository | `memrank/adapters/` |
| Needs a PR? | no | yes, plus entries in ~8 tables and 6 test lists |
| Works today on | `--on local`, from a source checkout | every placement, including cloud |
| Evidence class | `development_observation`, `publishable: false` | artifact-backed, publishable |
| Verify with | `memrank targets verify <ref>` | `pytest tests/live/conformance/test_adapter_contract.py` |

**Start with a translator** if you want to evaluate your own engine, iterate on it, or compare it
against the catalog privately. It needs nothing from us and no release of memrank -- read
[adapter-contract.md](adapter-contract.md) and copy
[`examples/native-adapter/`](../examples/native-adapter/).

**Write an in-tree adapter** when an engine should appear on the public leaderboard. Publishable
evidence requires a pinned, reproducible artifact, which a source-launched translator is not. The
rest of this document is that route.

**Register an adapter from outside the tree** when you want the in-tree driving model -- your own
Python `MemoryAdapter`, your own target descriptors, the full `memrank submit` lifecycle -- without
the class living here. Copy [`examples/custom-target/`](../examples/custom-target/README.md), which
wires a twenty-line engine in all three ways and runs offline; the mechanics are in
[Registering an adapter from outside](#registering-an-adapter-from-outside) below.

## 1. Subclass `MemoryAdapter`

```python
from memrank.core import Document, MemoryAdapter
from memrank.instrumentation import LatencyCollector, TokenCollector


class MyAdapter(MemoryAdapter):
    name = "myengine"           # short, lowercase, alphanumeric
    version = "0.1.0"           # adapter version
    engine_version = "1.2.3"    # the engine you're wrapping

    def __init__(self):
        self.latency = LatencyCollector()
        self.tokens = TokenCollector()

    def prepare(self, isolation_unit: str) -> None: ...
    def ingest(self, documents: list[Document]) -> None: ...
    def retrieve(self, query, k, user_id, query_timestamp=None): ...
    def cleanup(self) -> None: ...
    def latency_metrics(self): return self.latency.as_metrics()
    def token_metrics(self):   return self.tokens.as_metrics()
```

## Transport & dependency neutrality

The `MemoryAdapter` subclass *is* the neutral boundary -- neutrality does **not**
mean "everything over HTTP". Some engines expose an HTTP API; others ship only
as an in-process library/SDK. Both are first-class:

- **memrank core depends on nothing vendor-specific.** It only knows the
  `MemoryAdapter` interface.
- **The adapter owns its transport.** Wrap an HTTP API *or* a vendor SDK --
  whatever the engine provides. An SDK-only engine is a valid, expected case.
- **Vendor SDKs are optional extras.** Declare them in `pyproject.toml`
  (`memrank[<engine>]`), import them lazily inside the adapter, and fail loud
  with an install hint if missing -- never make core import a vendor package.
- **Label the transport honestly.** Set `transport` to the real surface
  (`"http"` / `"sdk"` / `"in-process"`). If your adapter supports more than one,
  set it per instance in `__init__` -- latency is only comparable within a
  transport class (see `docs/methodology.md`), so a wrong label misleads readers.
- **Record the engine's internal config** (the LLM/embedder it uses) where you
  can, so "what was actually compared" is explicit rather than implied.

## 2. Use the instrumentation collectors

Wrap each network call so Memrank can report ingest/retrieve latency:

```python
with self.latency.track("ingest"):
    response = client.post(...)
```

After each LLM round-trip, record token counts:

```python
self.tokens.record_call("query", input_tokens=usage.in_, output_tokens=usage.out)
```

Adapters that internally measure latency differently (e.g., reporting only
the engine's processing time, not network RTT) may call `record` directly
with the value they want surfaced.

## 3. Register the adapter

Add the class to `memrank/adapters/__init__.py`:

```python
from memrank.adapters.myengine import MyAdapter
REGISTRY["myengine"] = MyAdapter
```

## 4. Make it a target (stack engines)

An adapter alone only supports `--adapter myengine` against a backend you stood
up yourself. For `memrank submit myengine ... --on local|cloud` to launch the
engine, every chokepoint below needs an entry -- each one fails loudly (or is
covered by an enumeration test) when missing, so work through the list until
the static suites pass. `hindsight` is the worked example to mirror: its image is the vendor's
own (`ghcr.io/vectorize-io/hindsight`, anonymous pull), so every file below is one you can read
and run without credentials.

| Chokepoint | File | What to add |
| --- | --- | --- |
| Target manifest | `memrank/targets/builtin/myengine.yaml` | name/kind/adapter/transport, `engine: {artifact, port}`, declared `components`, `compose`, `service` |
| Compose graph | `memrank/targets/builtin/myengine.compose.yaml` | the engine's containers, image pinned by public reference |
| Presets (optional) | `memrank/targets/builtin/myengine-<preset>.yaml` | `from: myengine` + the component overrides (see `hindsight-matched.yaml`) |
| Engine env tables | `memrank/targets/engine_env.py` | one entry in each of `ENGINE_ENV`, `BASE_URL_ENV`, `ENGINE_SETTINGS`, `ENGINE_COMMAND`, `READINESS`, `PROVENANCE_FIELDS` (+ `PAIRED_TOKENS`/`SECRET_ENV` when applicable). Empty dict / `None` are positive statements; absence is an error. |
| Launch requirements | `memrank/secrets/requirements.py` | `REQUIREMENTS["myengine"]` with canonical providers; extend `PROVIDER_KEY_ENV` if the engine speaks its own provider vocabulary |
| Provenance | `memrank/provenance/engine.py` | `PROVENANCE["myengine"]` (purl identity, manufacturer/supplier, pedigree). `source_repo` is for a repository a reader of the receipt can actually fetch; a source that is not public sets `source_repo: None` plus `source_visibility: "private"` and a public `source_name`, and the commit is pinned by a locationless `pkg:generic/<name>@<commit>` purl instead of by a name nobody can resolve. |
| Enumerating tests | `tests/targets/test_catalog.py` (`EXPECTED`), `tests/live/conformance/test_adapter_contract.py` (`_backend_url`), `tests/placement/test_taskdef_render.py`, `tests/placement/test_local_placement.py`, `tests/provenance/test_engine_provenance.py`, `tests/secrets/test_requirements.py` | add the new name to each pinned list |

A component knob the engine exposes but the manifest leaves unstated fails the
render (`component_env`): declare every knob explicitly, even "the built-in
default" -- an engine whose deterministic fallback extractor is the default still
has to say so, or the receipt cannot report what ran.

### Credentials: let the target say, don't extend the table

`REQUIREMENTS` derives an engine's credentials from its component *providers* -- right for a vendor
(`llm: {provider: anthropic}` means `ANTHROPIC_API_KEY`), and only that. It cannot express a
credential that is not one key per vendor.

A target states its own instead:

```yaml
# names the engine reads directly
secrets: [LLM_API_KEY, EMBEDDING_API_KEY]

# a rename: what memrank resolves on the left, what the engine reads on the right
secrets:
  ANTHROPIC_API_KEY: HINDSIGHT_API_LLM_API_KEY

# anything at all -- memrank never interprets these
secrets: [MYENGINE_USER, MYENGINE_PASSWORD, MYENGINE_TENANT]
```

Each name is resolved through the one credential chokepoint -- process environment, then org
secrets, then the encrypted wallet -- and injected under the variable the target names. memrank
learns nothing about what any of them mean, which is the point: an engine authenticating with a
user and a password, a client id and a tenant, or a token under a name nobody anticipated needs no
change to memrank at all.

Declared secrets are **added to** what the providers imply, so a target can use both. Reach for
`PROVIDER_KEY_ENV` only when adding a genuine vendor that many engines will name.

### Named native development target

Keep engine repositories independent of Memrank. To evaluate an unpublished checkout, place one
complete, manually authored target in `${MEMRANK_CONFIG_DIR:-~/.config/memrank}/targets/`:

```yaml
schema_version: 1
name: myengine:dev
kind: stack
interface:
  adapter: myengine
  transport: http
binding:
  kind: source
  root: /absolute/path/to/myengine
launch:
  command: "cargo run -p myengine-server -- --bind 127.0.0.1:{port}"
  requires: [Cargo.toml]
network:
  port: 8080
  readiness: {path: /health}
components:
  llm: {provider: regex}
```

The command is split into argv and executed directly; Memrank does not add an implicit shell. Use an
explicit `sh -lc '...'` only when shell behavior is genuinely required. `{port}` expands to the
target's declared `network.port`. The optional `requires` paths provide an early wrong-checkout
error.

The developer then runs:

```bash
memrank submit myengine:dev demo
```

Endpoint operations still belong in the named adapter. The target owns launch and readiness, and
the engine repository needs no Memrank descriptor, Dockerfile, or publishing workflow. There is no
target-creation command: author and review the central YAML directly.

This form requires an adapter that already knows the engine's wire protocol -- it is how a *fork* of
a known engine is evaluated. For an engine Memrank has never seen, use `adapter: native` and point
`launch.command` at a translator instead; see [adapter-contract.md](adapter-contract.md) section 9.

## 5. Run the conformance suite

```bash
pytest tests/live/conformance/test_adapter_contract.py -k myengine
```

Static checks (class attributes, abstract method coverage, metric key
shape) run unconditionally. Live smoke tests skip cleanly if your engine
is not reachable.

## 6. Write your own tests

The conformance suite proves your adapter satisfies the contract. Anything you
assert about *your* adapter's own behavior goes in `tests/adapters/`, one file per
adapter, named `test_<name>_adapter.py` alongside the ones already there.

`tests/adapters/` is for behavior that needs no live backend -- request shapes,
partitioning, config resolution, what the adapter does with a refusal. Anything
that skips when your engine is not running belongs in `tests/live/` instead, which
is the one directory in the tree organized by what a test *needs* rather than what
it is about. [`tests/README.md`](../tests/README.md) states the rule for every
directory, and it is worth reading once before you add a file.

## 7. Submit a PR

Per the vendor-neutral charter, AtomicStrata commits to reviewing valid
adapter PRs within 7 days. Include in your PR:

- adapter source under `memrank/adapters/<name>.py`
- registry entry
- tests under `tests/adapters/`
- documentation for any new env vars
- a brief note on how to stand up the backend locally

## Registering an adapter from outside

A third route sits between the two above: keep the Python `MemoryAdapter` and the full lifecycle,
but let the class live in your own repository. `memrank/plugins.py` exposes `register_adapter`,
which takes the adapter class **and every table row that drives it** as one object:

```python
from memrank.plugins import AdapterRegistration, register_adapter
from memrank.secrets.requirements import EngineRequirements
from memrank.targets.engine_env import Readiness

register_adapter(AdapterRegistration(
    adapter=MyAdapter,
    engine_env={("llm", "provider"): "MYENGINE_EXTRACTOR"},
    base_url_env="MYENGINE_API_URL",
    readiness=Readiness("curl -fsS http://localhost:{port}{path} || exit 1", "/health", 60),
    engine_command=None,
    requirements=EngineRequirements("myengine", providers={"llm": "openai"}),
    provenance={...},
))
```

Point memrank at the module that makes that call, and put it on the interpreter's import path:

```bash
memrank config set adapters.plugins myengine_memrank
export PYTHONPATH=/abs/path/to/your/plugins
```

The first seven fields have no defaults on purpose. Each is read where absence is either a loud
failure far from its cause or -- for `provenance` -- a silent one: without that row
`build_provenance` returns `{}`, and the receipt loses not only the engine's purl but the workspace
pins (commit, dirty flag, working-tree delta) a source-bound target exists to record.

**What this route does not confer.** A module found on `sys.path` has no version and no resolvable
origin, so registering through it earns no reproducibility claim of its own. The run's evidence
class still derives from how its *artifact* was bound, exactly as for a built-in -- which for a
source-bound target means `development_observation`, `publishable: false`. Registration decides
where the code lives, never what may be claimed about the measurement.

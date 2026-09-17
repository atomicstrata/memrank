# Adding an adapter

An adapter is your engine, wrapped in six methods so Memrank can drive it like any other. Memrank
supplies everything around it: the run loop, isolation between units, latency and token
instrumentation, cost accounting, scoring, judging where you ask for one, and the receipt that
records what actually ran.

You do not have to put your adapter inside this package to run it, and you do not have to give it a
name. Pass the instance.

## 1. Run your own engine: pass the instance

`memrank.run` takes a `MemoryAdapter` instance wherever it takes a target ref, so an engine that
exists only in your codebase runs the same loop, and returns the same `EvalResult`, as the shipped
targets:

```python
import memrank
from memrank import Document, MemoryAdapter
from memrank.instrumentation import LatencyCollector, TokenCollector


class MyAdapter(MemoryAdapter):
    name = "myengine"           # a label on the result, not an address
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


result = memrank.run(MyAdapter(), "demo", repeats=1)
print(result.composite, result.adapter)
```

Those six methods are the whole third-party contract; [adapter-contract.md](adapter-contract.md)
states each one in full. Nothing here touches the registry, the command line, a configuration
setting or a file inside `memrank/` -- and the second argument is an eval the same way: a catalog
ref, or a `Benchmark` instance of your own (see [adding a benchmark](adding-benchmarks.md)).

The runnable version of exactly this, offline and in about a second, is
[`examples/custom-engine.py`](../examples/custom-engine.py):

```bash
python examples/custom-engine.py
```

**What the instance route does not reach.** An engine passed as an object has no catalog ref, so
there is no address, no variant digest and no provenance for the build. `memrank submit`, cloud
placement and `workers > 1` all need a ref, and the run's evidence class is
`development_observation`, `publishable: false`. Reaching those means giving the engine a name,
which is [Making it runnable by name](#making-it-runnable-by-name-sharing-the-cli-and-the-cloud).

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

A bucket you never sampled reports `None`, meaning "not reported" -- never zero, which would claim
you measured it.

## Transport and dependency neutrality

The `MemoryAdapter` subclass *is* the neutral boundary -- neutrality does **not**
mean "everything over HTTP". Some engines expose an HTTP API; others ship only
as an in-process library/SDK. Both are first-class:

- **memrank core depends on nothing vendor-specific.** It only knows the
  `MemoryAdapter` interface.
- **The adapter owns its transport.** Wrap an HTTP API *or* a vendor SDK --
  whatever the engine provides. An SDK-only engine is a valid, expected case.
- **Vendor SDKs are optional extras.** For an in-tree adapter, declare them in `pyproject.toml`
  (`memrank[<engine>]`); either way, import them lazily inside the adapter and fail loud
  with an install hint if missing -- never make core import a vendor package.
- **Label the transport honestly.** Set `transport` to the real surface
  (`"http"` / `"sdk"` / `"in-process"`). If your adapter supports more than one,
  set it per instance in `__init__` -- latency is only comparable within a
  transport class (see `docs/methodology.md`), so a wrong label misleads readers.
- **Record the engine's internal config** (the LLM/embedder it uses) where you
  can, so "what was actually compared" is explicit rather than implied.

## Making it runnable by name: sharing, the CLI and the cloud

Everything above runs from Python and stays in your own repository. Do the rest of this document
when the engine should be runnable **by name** -- from the command line, at `workers > 1`, in the
cloud, or by other people. Registration decides where the code lives and what may address it; it
never changes what the six methods do, and it never changes what may be claimed about a measurement.

There are three ways to take that step, and the right one depends on who you are.

| | **Register from outside** | **Write an in-tree adapter** | **Write a translator** |
|---|---|---|---|
| What you write | the same class, plus one `register_adapter` call | a Python `MemoryAdapter` subclass, in this repo | a program serving [the adapter contract](adapter-contract.md), in any language |
| Where it lives | your repository | `memrank/adapters/` | your repository |
| Needs a PR? | no | yes, plus entries in ~8 tables and 6 test lists | no |
| Works today on | `--on local`, sweeps and `workers > 1`, on a machine you configured; not the cloud, which carries only the manifests inside the package | every placement, including cloud | `--on local`, from a source checkout |
| Evidence class | derives from how the artifact was bound | artifact-backed, publishable | `development_observation`, `publishable: false` |
| Verify with | `memrank targets verify <ref>` | `pytest tests/live/conformance/test_adapter_contract.py` | `memrank targets verify <ref>` |

[`examples/custom-target/`](../examples/custom-target/README.md) wires a twenty-line engine all
three ways and runs offline; it is the fastest way to see what each one buys.

**Write an in-tree adapter** when an engine should appear on the public leaderboard. Publishable
evidence requires a pinned, reproducible artifact, which a source-launched engine is not. Sections
[3](#3-register-the-adapter-in-tree) to [6](#6-submit-a-pr) are that route.

**Write a translator** when your engine is not Python, or when you would rather memrank never
imported your code -- read [adapter-contract.md](adapter-contract.md) and copy
[`examples/native-adapter/`](../examples/native-adapter/).

**Register from outside** when you want the in-tree driving model -- your own Python
`MemoryAdapter`, your own target descriptors, the full `memrank submit` lifecycle -- without the
class living here. The mechanics are in
[Registering an adapter from outside](#registering-an-adapter-from-outside) below.

### 3. Register the adapter (in-tree)

Add the class to `memrank/adapters/__init__.py`:

```python
from memrank.adapters.myengine import MyAdapter
REGISTRY["myengine"] = MyAdapter
```

### 4. Make it a target (stack engines)

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

#### Credentials: let the target say, don't extend the table

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

#### Named native development target

Keep engine repositories independent of Memrank. To evaluate an unpublished checkout *by name*,
place one complete, manually authored target in
`${MEMRANK_CONFIG_DIR:-~/.config/memrank}/targets/`:

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

### 5. Run the conformance suite

```bash
pytest tests/live/conformance/test_adapter_contract.py -k myengine
```

Static checks (class attributes, abstract method coverage, metric key
shape) run unconditionally. Live smoke tests skip cleanly if your engine
is not reachable.

The conformance suite is what a shared adapter is held to. For an engine you only pass as an
instance, `memrank targets verify` and your own tests are the equivalent -- the most consequential
check either one runs is that state does not leak between isolation units.

#### Write tests beside the others

The conformance suite proves your adapter satisfies the contract. Anything you
assert about *your* adapter's own behavior goes in `tests/adapters/`, one file per
adapter, named `test_<name>_adapter.py` alongside the ones already there.

`tests/adapters/` is for behavior that needs no live backend -- request shapes,
partitioning, config resolution, what the adapter does with a refusal. Anything
that skips when your engine is not running belongs in `tests/live/` instead, which
is the one directory in the tree organized by what a test *needs* rather than what
it is about. [`tests/README.md`](../tests/README.md) states the rule for every
directory, and it is worth reading once before you add a file.

### 6. Submit a PR

Per the vendor-neutral charter, AtomicStrata commits to reviewing valid
adapter PRs within 7 days. Include in your PR:

- adapter source under `memrank/adapters/<name>.py`
- registry entry
- tests under `tests/adapters/`
- documentation for any new env vars
- a brief note on how to stand up the backend locally

### Registering an adapter from outside

Keep the Python `MemoryAdapter` and the full lifecycle, but let the class live in your own
repository. `memrank/plugins.py` exposes `register_adapter`, which takes the adapter class **and
every table row that drives it** as one object:

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

Descriptors for the engine go in a directory of your own, named on the `targets.path` setting:

```bash
memrank config set targets.path /abs/path/to/your/targets
```

Both settings persist, and both are read on every command: a module named in `adapters.plugins` that
is not importable fails every command until the path is restored or the setting is cleared
(`memrank config set adapters.plugins ""`). That is the price of a name, and it is why the instance
route asks for neither.

An in-process engine has nothing to launch and nothing to reach, so it uses
`AdapterRegistration.in_process(...)` instead, which asks only what launching it costs in
credentials and what the receipt should say about it.

The first seven fields of `AdapterRegistration` have no defaults on purpose. Each is read where
absence is either a loud failure far from its cause or -- for `provenance` -- a silent one: without
that row `build_provenance` returns `{}`, and the receipt loses not only the engine's purl but the
workspace pins (commit, dirty flag, working-tree delta) a source-bound target exists to record.

**What this route does not confer.** A module found on `sys.path` has no version and no resolvable
origin, so registering through it earns no reproducibility claim of its own. The run's evidence
class still derives from how its *artifact* was bound, exactly as for a built-in -- which for a
source-bound target means `development_observation`, `publishable: false`. Registration decides
where the code lives, never what may be claimed about the measurement.

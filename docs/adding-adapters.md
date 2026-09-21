# Adding a system

A **system** is the thing under test. Its kind is the class you subclass, so a kind cannot be
declared wrong: a **memory** is told things, asked later for what is relevant, and cleared on
request. Memrank supplies everything around it -- the run loop, isolation between groups of
tasks, latency and token instrumentation, cost accounting, the measures that turn what was
observed into named values, and the receipt that records what actually ran.

You do not have to put your system inside this package to run it, and you do not have to give
it a name. Pass the instance.

**One note on names.** The memory kind's class is still spelled `MemoryAdapter` in the source,
and `memrank.Memory` is the same class object under the name the seven words use -- either
spelling gives one type, and every adapter already written is a `Memory`. The command line
keeps its own older vocabulary too: *target* for a named system, *adapter* for the class that
drives it. Renaming the classes is a later change; nothing below depends on which spelling you
read.

## 1. Run your own system: pass the instance

`memrank.run(system, evaluation)` takes the instance, so a system that exists only in your
codebase runs the same loop as the ones memrank ships:

```python
import memrank
from memrank import Document, Recall


class MyMemory(memrank.Memory):
    name = "myengine"           # a label on the result, not an address
    version = "0.1.0"           # your class's own version
    engine_version = "1.2.3"    # the engine you are wrapping

    def prepare(self, isolation_unit: str) -> None: ...
    def ingest(self, documents: list[Document]) -> None: ...
    def retrieve(self, query, k, user_id, query_timestamp=None) -> Recall: ...
    def cleanup(self) -> None: ...


result = memrank.run(MyMemory(), memrank.evaluation("demo"))
print(result.values_of("demo-score")[0].value, result.system.name, result.system.kind)
```

Those four verbs are the whole third-party contract, and they are abstract: a run refuses
before touching anything when one is missing, with a stated reason rather than a `TypeError`
from somewhere inside. [adapter-contract.md](adapter-contract.md) states each one in full.

`retrieve` returns a `Recall`: the documents in the order your system ranked them -- the order
**is** the measurement, so return at most `k` and never pad -- and `declared`, whatever your
system wants to say about the call, recorded untouched. Both halves land on the trace.

Nothing in those four verbs reports a measurement memrank takes itself: memrank times every
ingest and retrieve at its own call boundary, so latency is neither your job nor something
your system could flatter.

**The one exception is token usage**, because only a system can be told what a provider billed
it. A system that knows declares it by recording into a `TokenCollector` and returning
`self.tokens.as_metrics()` from an optional `token_metrics()`:

```python
from memrank.instrumentation import TokenCollector

class MyMemory(memrank.Memory):
    def __init__(self):
        self.tokens = TokenCollector()          # `self.tokens` by that name: a run at
                                                # --workers N sums the collectors it built
    def token_metrics(self):
        return self.tokens.as_metrics()
```

Declaring nothing is fine and is the common case: the result then reports `None` for each
token bucket, which says nobody counted rather than claiming the system spent zero.

There is a second, narrower declaration: `declared_latency()`, for time only your system can
see inside the hop memrank measured around it -- a translator's `engine_ms`. Return SAMPLES
per bucket, in milliseconds, and memrank pools them across workers and renders
`<bucket>_p50_ms` / `<bucket>_p95_ms` itself. A bucket that would render one of memrank's own
six keys is refused: a system does not report the number the reader reads.

Nothing here touches the registry, the command line, a configuration setting or a file inside
`memrank/` -- and the second argument is an evaluation the same way: `memrank.evaluation("demo")`,
or an `Evaluation` of your own (see [adding an evaluation](adding-benchmarks.md)).

The runnable version of exactly this, offline and in about a second, is
[`examples/02-your-own-system/`](../examples/02-your-own-system/README.md):

```bash
uv run python examples/02-your-own-system/run.py
```

**What the instance route does not reach.** A system passed as an object has no catalog ref, so
there is no address, no variant digest and no provenance for the build. `memrank submit`, cloud
placement and `workers > 1` all need a ref, and the run's evidence class is
`development_observation`, `publishable: false`. Reaching those means giving the system a name,
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

A system that internally measures latency differently (e.g. reporting only its own processing
time, not network RTT) may call `record` directly with the value it wants surfaced.

A bucket you never sampled reports `None`, meaning "not reported" -- never zero, which would
claim you measured it.

## Transport and dependency neutrality

The `memrank.Memory` subclass *is* the neutral boundary -- neutrality does **not**
mean "everything over HTTP". Some engines expose an HTTP API; others ship only
as an in-process library/SDK. Both are first-class:

- **memrank core depends on nothing vendor-specific.** It only knows the memory kind's four
  verbs.
- **The system owns its transport.** Wrap an HTTP API *or* a vendor SDK --
  whatever the engine provides. An SDK-only engine is a valid, expected case.
- **Vendor SDKs are optional extras.** For an in-tree system, declare them in `pyproject.toml`
  (`memrank[<engine>]`); either way, import them lazily inside the class and fail loud
  with an install hint if missing -- never make core import a vendor package.
- **Label the transport honestly.** Set `transport` to the real surface
  (`"http"` / `"sdk"` / `"in-process"`). If your system supports more than one,
  set it per instance in `__init__` -- latency is only comparable within a
  transport class (see `docs/methodology.md`), so a wrong label misleads readers.
- **Record the engine's internal config** (the LLM/embedder it uses) where you
  can, so "what was actually compared" is explicit rather than implied.

## Making it runnable by name: sharing, the CLI and the cloud

Everything above runs from Python and stays in your own repository. Do the rest of this document
when the system should be runnable **by name** -- from the command line, at `workers > 1`, in the
cloud, or by other people. This is where the command line's own vocabulary starts: a **target** is
its word for a named system. Registration decides where the code lives and what may address it; it
never changes what the four verbs do, and it never changes what may be claimed about a measurement.

There are three ways to take that step, and the right one depends on who you are.

| | **Register from outside** | **Write an in-tree adapter** | **Write a translator** |
|---|---|---|---|
| What you write | the same class, plus one `register_adapter` call | a Python `memrank.Memory` subclass, in this repo | a program serving [the translator contract](adapter-contract.md), in any language |
| Where it lives | your repository | `memrank/adapters/` | your repository |
| Needs a PR? | no | yes, plus entries in ~8 tables and 6 test lists | no |
| Works today on | `--on local`, sweeps and `workers > 1`, on a machine you configured; not the cloud, which carries only the manifests inside the package | every placement, including cloud | `--on local`, from a source checkout |
| Evidence class | derives from how the artifact was bound | artifact-backed, publishable | `development_observation`, `publishable: false` |
| Verify with | `memrank targets verify <ref>` | `pytest tests/live/conformance/test_adapter_contract.py` | `memrank targets verify <ref>` |

[`examples/more/custom-target/`](../examples/more/custom-target/README.md) wires a twenty-line engine all
three ways and runs offline; it is the fastest way to see what each one buys.

**Write an in-tree system** when an engine should appear on the public leaderboard. Publishable
evidence requires a pinned, reproducible artifact, which a source-launched engine is not. Sections
[3](#3-register-the-adapter-in-tree) to [6](#6-submit-a-pr) are that route.

**Write a translator** when your engine is not Python, or when you would rather memrank never
imported your code -- read [the translator contract](adapter-contract.md) and copy
[`examples/native-adapter/`](../examples/more/native-adapter/).

**Register from outside** when you want the in-tree driving model -- your own Python
`memrank.Memory`, your own target descriptors, the full `memrank submit` lifecycle -- without the
class living here. The mechanics are in
[Registering an adapter from outside](#registering-an-adapter-from-outside) below.

### 3. Register the system (in-tree)

Add the class to `memrank/adapters/__init__.py`, which is still the registry's file name:

```python
from memrank.adapters.myengine import MyAdapter
REGISTRY["myengine"] = MyAdapter
```

### 4. Make it a target (stack engines)

A registered class alone only supports `--adapter myengine` against a backend you stood
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

The conformance suite is what a shared system is held to. For a system you only pass as an
instance, `memrank targets verify` and your own tests are the equivalent -- the most consequential
check either one runs is that state does not leak between groups of tasks.

#### Write tests beside the others

The conformance suite proves your system satisfies the contract. Anything you
assert about *your* system's own behavior goes in `tests/adapters/`, one file per
system, named `test_<name>_adapter.py` alongside the ones already there.

`tests/adapters/` is for behavior that needs no live backend -- request shapes,
partitioning, config resolution, what the system does with a refusal. Anything
that skips when your engine is not running belongs in `tests/live/` instead, which
is the one directory in the tree organized by what a test *needs* rather than what
it is about. [`tests/README.md`](../tests/README.md) states the rule for every
directory, and it is worth reading once before you add a file.

### 6. Submit a PR

Per the vendor-neutral charter, AtomicStrata commits to reviewing valid
PRs within 7 days. Include in your PR:

- the class under `memrank/adapters/<name>.py`
- registry entry
- tests under `tests/adapters/`
- documentation for any new env vars
- a brief note on how to stand up the backend locally

### Registering a system from outside

Keep the Python `memrank.Memory` and the full lifecycle, but let the class live in your own
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

An in-process system has nothing to launch and nothing to reach, so it uses
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

# Installing memrank

Two minutes. You end with `memrank` on your PATH -- no `uv run`, no virtualenv to activate.

## 1. Get `uv`

```bash
curl -LsSf https://astral.sh/uv/install.sh | sh     # macOS / Linux
```

Already have it? `uv --version` needs to be 0.5 or newer.

memrank needs Python 3.10 or newer; uv installs one for you if the machine has none.

## 2. Install memrank

```bash
uv tool install memrank
```

Check it landed:

```bash
memrank --help
memrank --version      # the version, and where this install came from
```

<details>
<summary><code>memrank: command not found</code></summary>

uv installs tools into `~/.local/bin`. Add it to your PATH, or let uv do it:

```bash
uv tool update-shell    # then restart your shell
```
</details>

<details>
<summary>Upgrading later</summary>

For a published install, the upgrade is the ordinary one:

```bash
uv tool upgrade memrank     # or: pip install --upgrade memrank
```

For a source install it is the install command again, `--force --refresh` included -- see
below for why. Which one applies to *your* install is not something you have to remember:
every memrank message that asks you to upgrade reads your own install metadata and names the
path that fits it -- including an editable install, where the answer is to update the tree it
tracks rather than to reinstall anything.
</details>

<details>
<summary>Installing from source (contributors)</summary>

The repository is public, so this needs no GitHub credential:

```bash
uv tool install --force --refresh git+https://github.com/atomicstrata/memrank
```

`--force` reinstalls over what is already there; `--refresh` is what makes it actually pick up
a moved branch. Not `uv tool upgrade memrank` -- for a *git* install uv resolves the branch
against its cache and will tell you there is nothing to upgrade while the branch has moved
([astral-sh/uv#4317](https://github.com/astral-sh/uv/issues/4317),
[#9146](https://github.com/astral-sh/uv/issues/9146)). That caveat is about git installs only;
a published install upgrades normally.

To work on memrank itself, take a checkout instead:

```bash
git clone https://github.com/atomicstrata/memrank
cd memrank
uv tool install --editable .     # `memrank` tracks your working tree
```

Code edits apply immediately; changing *dependencies* needs a re-install. For the test suite
and the rest of the development loop, see [local development](local-development.md).

`memrank --version` prints where the install came from -- for a git install, the commit -- which
is the thing to quote when something looks wrong.
</details>

## 3. Run an evaluation

Nothing below needs a running engine, a network, or an API key -- `demo` is a synthetic benchmark
that ships with memrank, and `word-overlap` is a trivial in-process retriever:

```bash
memrank submit word-overlap demo               # prints a run id immediately, runs in the background
memrank watch <id>                             # attach until it ends (exit code = outcome)
memrank runs ls                                # submitted -> running -> done
memrank runs show <id>                         # state, where it ran, artifact location
```

That's the whole loop. `submit` always returns immediately with the run id(s); `watch` blocks on
them, `runs ls` glances at them, `kill <id>` stops one.

## Finding your way around

```bash
memrank targets ls               # what can be evaluated  (hindsight, atomicmemory, word-overlap, ...)
memrank evals ls                 # what to evaluate against  (locomo, beam, longmemeval, demo)
memrank targets show hindsight   # the exact composition, and ✔/✘ per secret it needs
memrank runs ls --live      # what's still going
memrank submit --help       # every flag, grouped
```

`memrank targets show <ref>` marks ✔/✘ per secret **before** anything is spent, so a missing key
surfaces as a refusal rather than a half-finished run. Store one with
`memrank secrets set <NAME>`; `memrank secrets ls` shows what the local wallet holds.

## Where a run happens

`--on` selects the placement. The default is `defaults.on` (`memrank config ls`), which is `none`
on a fresh install.

| | |
|---|---|
| `--on none` | an engine you are already running, at its configured URL |
| `--on local` | a disposable, isolated stack provisioned per run from the target manifest -- needs Docker |
| `--on cloud` | submitted to the hosted memrank platform -- needs a signed-in session (below) |

```bash
export HINDSIGHT_API_URL=http://localhost:7000
memrank submit hindsight locomo:smoke --on none
```

The variable above points at an engine you started. Whether you can obtain that engine's image
at all differs per target -- [engine images](engine-images.md) says which, and what to run for the
two you cannot pull.

Engine URL defaults, each overridable by its environment variable:

| Engine | Variable | Default |
|---|---|---|
| AtomicMemory | `ATOMICMEMORY_API_URL` | `http://localhost:3070` |
| Mem0 (HTTP) | `MEM0_HTTP_URL` | `http://localhost:8888` |
| Hindsight | `HINDSIGHT_API_URL` | `http://localhost:7000` |
| Supermemory | `SUPERMEMORY_BASE_URL` | `http://localhost:6767` |

Judged runs send benchmark content to Anthropic and need `ANTHROPIC_API_KEY`. They are on by
default for `locomo`, `longmemeval` and `beam`, whose only quality metric is the judge's, and off
where the benchmark scores itself. `--no-judge` measures latency and cost without paying for
quality.

## Optional: the hosted platform

Everything above works logged out, against your own machine, and accumulates locally. Signing in
is needed only to submit runs to AtomicStrata's hosted platform and to share a run record with an
organisation.

```bash
memrank auth login
memrank auth status     # who you are, which orgs, when the session expires
memrank config ls       # every setting, its value, and where that value came from
```

A browser opens; approve with GitHub. Login also configures the machine -- it writes your default
org and points submissions at the platform, which is why nothing afterwards needs `--on` or
`--org`. Only the *first* login writes those defaults, so a later sign-in never overrides one you
chose since (change it with `memrank config set defaults.org <slug>`).

> **"no default org"?** Membership is not self-served yet. Hosted runs are, for now, limited to
> accounts AtomicStrata has provisioned; local placements are not.

Hosted runs are held to your org's limits -- a quota on how many you may have started and still
running, and, for a run composed in the browser rather than submitted from the CLI, that org's
run-shape ceilings; a submission over either is refused naming the limit it crossed.

<details>
<summary>Signing in over SSH, or anywhere with no browser</summary>

Nothing extra to do -- `auth login` notices there is no browser and prints a URL instead:

```console
$ memrank auth login
No browser here. Open this on any device to sign in:

      https://memrank.dev/signin?flow=Xk7pQ2...&client=cli

  ✓ signed in -- token expires 2026-09-12T...
```

Open it anywhere -- your laptop, your phone -- and approve with GitHub. The terminal is polling and
picks it up within a few seconds; the link is good for ten minutes.

Force this path with `--no-browser` when a browser exists but cannot actually open, such as an
`ssh -X` display that will not come up.

`MEMRANK_TOKEN` still overrides everything and is what CI should use -- but for a person on a
remote box, the flow above is the answer, and it does not put a 30-day credential in a shell
history or a second machine's dotfiles.
</details>

<details>
<summary>Where the session token is stored</summary>

`~/.memrank/credentials`, mode `0600` -- the model `aws`, `gcloud` and `kubectl` use.

Not the OS keychain by default, deliberately. memrank runs as a Python entry point, so the macOS
dialog names *python* rather than memrank, and it returns after every reinstall because the
permission binds to the interpreter. A prompt people learn to click through protects nothing.

Prefer the keychain anyway? `memrank config set auth.keyring true`, then `memrank auth login`
again. `MEMRANK_TOKEN` overrides both, and is what CI should use.
</details>

## Connecting an AI agent

Install the optional MCP server with `uv tool install 'memrank[mcp]'`, then configure the agent to
launch `memrank-mcp`. Run `memrank-mcp --help` for the tool workflow and configuration.

From the source install, the same extra is named against the URL:

```bash
uv tool install --force --refresh 'memrank[mcp] @ git+https://github.com/atomicstrata/memrank'
```

## Known limitations

- **A finished cloud run shows no SCORE** -- `runs ls` prints `—` and `runs show` says
  `results: (none recorded yet)`. The run did succeed and its artifact was written; nothing pulls
  it back into the record yet.
- **`memrank watch` of a cloud run** downloads artifacts straight from object storage on success,
  which needs credentials most people will not have. Follow cloud runs with `runs ls` instead.
- **Engine-backed cloud targets** (`mem0`, `atomicmemory`, `hindsight`, `supermemory`) are not
  serving yet. The same targets work under `--on none` and `--on local`.

Local placements -- the ones this page leads with -- are not affected by any of the above.

## Telling us something broke

`memrank --version` and the run id from `runs ls` make a report actionable. The version line says
where the install came from as well as what it is -- a released version identifies itself, and a
git install adds the commit, so two people reporting "0.2.0" are distinguishable. Paste the whole
error text: messages are written to name the fix, and one that doesn't is itself worth reporting.

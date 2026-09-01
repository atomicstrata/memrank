# Installing memrank

Two minutes. You end with `memrank` on your PATH -- no `uv run`, no virtualenv to activate.

## 1. Get `uv`

```bash
curl -LsSf https://astral.sh/uv/install.sh | sh     # macOS / Linux
```

Already have it? `uv --version` needs to be 0.5 or newer.

memrank needs Python 3.10 or newer; uv installs one for you if the machine has none.

## 2. Install memrank

memrank is not published to PyPI yet, so the install is from git:

```bash
uv tool install --force --refresh git+https://github.com/atomicstrata/memrank
```

Check it landed:

```bash
memrank --help
memrank --version      # 0.2.0 or newer, and the commit it was built from
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

The same command. It is the install command precisely so there is only one to remember:

```bash
uv tool install --force --refresh git+https://github.com/atomicstrata/memrank
```

`--force` reinstalls over what is already there; `--refresh` is what makes it actually pick up a
moved branch. Not `uv tool upgrade memrank` -- uv resolves a git *branch* against its cache and
will tell you there is nothing to upgrade while the branch has moved
([astral-sh/uv#4317](https://github.com/astral-sh/uv/issues/4317),
[#9146](https://github.com/astral-sh/uv/issues/9146)).

`memrank --version` prints the commit you are on, which is the thing to quote when something
looks wrong.
</details>

<details>
<summary>Working on memrank itself</summary>

```bash
git clone https://github.com/atomicstrata/memrank
cd memrank
uv tool install --editable .     # `memrank` tracks your working tree
```

Code edits apply immediately; changing *dependencies* needs a re-install. For the test suite and
the rest of the development loop, see [local development](local-development.md).
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
memrank targets ls          # what can be evaluated  (mem0, atomicmemory, word-overlap, ...)
memrank evals ls            # what to evaluate against  (locomo, beam, longmemeval, demo)
memrank targets show mem0   # the exact composition, and ✔/✘ per secret it needs
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
export MEM0_HTTP_URL=http://localhost:8888
memrank submit mem0 locomo:smoke --on none
```

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

`memrank --version` and the run id from `runs ls` make a report actionable -- the version line
carries the commit, so "0.2.0" from two people is two different builds and we can tell which.
Paste the whole error text: messages are written to name the fix, and one that doesn't is itself
worth reporting.

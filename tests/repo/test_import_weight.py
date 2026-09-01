# Copyright 2026 AtomicStrata
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or
# implied. See the License for the specific language governing
# permissions and limitations under the License.
"""The CLI must not import the API service's stack.

`pip install memrank` gets the command; fastapi, uvicorn, psycopg and the Fernet backend live
in the `api` extra because only the service needs them. Nothing stops a future top-level import
from putting one back on the CLI's path -- at which point the extra still *resolves* (a developer
install has everything) and the breakage appears only in a user's `ModuleNotFoundError`.

So this is checked in a subprocess against a real import, not by reading pyproject: the question
is what the module graph actually pulls in.
"""
from __future__ import annotations

import subprocess
import sys
from pathlib import Path

# `tomllib` is stdlib only from 3.11, and `pyproject.toml` declares `requires-python = ">=3.10"`.
# Without this shim both of the tests that hold the public/private boundary raise at IMPORT on the
# declared floor -- a collection error in exactly the two files that are supposed to fail loudly.
try:
    import tomllib
except ModuleNotFoundError:  # pragma: no cover - only on 3.10
    import tomli as tomllib

#: Everything the CLI reaches for on the way to running a command.
CLI_MODULES = (
    "memrank.runner",
    "memrank.cli.auth",
    "memrank.cli.config",
    "memrank.cli.runs",
    "memrank.cli.evals",
    "memrank.cli.targets",
    "memrank.cli.secrets",
    "memrank.settings",
    "memrank.accounts.credentials",
    "memrank.placement.run_api_client",
)

#: Never published. Kept in step with `publish.toml`'s `internal` prefixes under `memrank/`.
INTERNAL_PACKAGES = ("memrank.api", "memrank.arena", "memrank.events", "memrank.leaderboard",
                     "memrank.analysis", "memrank.ops")


def _published_anyway() -> set[str]:
    """The `[exceptions] public` entries, read from the manifest rather than copied.

    A module under an internal prefix that publish.toml nevertheless publishes is not a leak, and
    the two lists must not be able to drift: `tests/repo/test_public_boundary.py` checks the manifest
    statically, this checks it against a real import, and they have to agree on the same file.
    """
    root = Path(__file__).resolve().parents[2]
    manifest = tomllib.loads((root / "publish.toml").read_text(encoding="utf-8"))
    return {p[: -len(".py")].replace("/", ".").removesuffix(".__init__")
            for p in manifest["exceptions"].get("public", []) if p.endswith(".py")}

#: Declared in the `api` extra. A CLI that imports one of these is a CLI a user cannot install.
SERVICE_ONLY = ("fastapi", "uvicorn", "psycopg", "psycopg_pool", "pydantic_settings",
                "cryptography", "redis", "websockets")


def _imported_by(modules: tuple[str, ...]) -> set[str]:
    """Every module name in sys.modules after importing `modules`, in a fresh process.

    Full dotted names, not just top-level packages: the boundary check below is about
    `memrank.api` versus `memrank.cli`, and a top-level projection cannot tell those apart.
    Top-level distribution names are still present in the set, so `SERVICE_ONLY` matches.
    """
    script = (
        "import sys\n"
        f"for name in {list(modules)!r}:\n"
        "    __import__(name)\n"
        "print(' '.join(sorted(sys.modules)))\n"
    )
    done = subprocess.run([sys.executable, "-c", script], capture_output=True, text=True)
    assert done.returncode == 0, done.stderr
    return set(done.stdout.split())


def test_the_cli_does_not_import_the_api_stack():
    loaded = _imported_by(CLI_MODULES)
    leaked = sorted(set(SERVICE_ONLY) & loaded)
    assert leaked == [], (
        f"the CLI imports {leaked}, which live in the `api` extra -- a user who ran "
        f"`pip install memrank` would get ModuleNotFoundError. Import it lazily, inside the "
        f"function that needs it.")


def test_the_cli_does_not_import_an_internal_package():
    """The public closure stays closed.

    `publish.toml` says these packages never ship. The CLI reaching one is not a packaging
    inconvenience like the check above -- it is a public tree that cannot import its own entry
    point, and it would be found by the first outsider to `pip install memrank` rather than
    here. Documented in localdocs/plans/2026-08-25-repo-boundary-execution-plan.md; enforced here.
    """
    loaded = _imported_by(CLI_MODULES)
    published = _published_anyway()
    leaked = sorted(m for m in loaded if m not in published
                    and any(m == pkg or m.startswith(f"{pkg}.") for pkg in INTERNAL_PACKAGES))
    assert leaked == [], (
        f"the CLI imports {leaked}, which `publish.toml` classifies internal -- the public tree "
        f"would not contain them. Import it lazily, or move the code the CLI needs out.")

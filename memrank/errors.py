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
"""The root of every error a user is meant to read -- the type the CLI boundary trusts.

Before this existed, whether a mistake reached the terminal as one actionable line or as a
Rich traceback depended on whether that particular call site remembered to wrap itself. It
usually did; ``style.error(...) + typer.Exit(1)`` appears two dozen times. But a defense
applied per surface is leaky by construction, and the surface that got missed was
``_split_overrides`` -- which runs a few lines before the ``except ManifestError`` that would
have caught it -- so a stray shell token spilled a stack trace.

``MemrankError`` closes that by inverting the default. Raising it is a promise that
``str(exc)`` is a complete, actionable sentence, and ``runner.main`` prints exactly that with
no traceback. Anything still deriving from bare ``Exception`` is thereby declaring itself an
internal bug, which is the distinction the codebase previously had no way to express.

The promise is enforced, not merely documented: ``tests/cli/test_cli_errors.py`` walks every
exception class defined under ``memrank/`` and fails when a new one skips this base.
"""
from __future__ import annotations

import os
from typing import Any


class MemrankError(Exception):
    """An error the operator can act on: bad input, bad config, a refused request.

    Subclass this for anything a user could plausibly cause and could plausibly fix. The
    message is the whole user interface -- write it as a sentence that names what was wrong
    and, where there is one, the move that fixes it. It is printed verbatim.
    """


class MissingOptionalDependency(MemrankError):
    """An optional extra this command needs is not installed."""


def optional_import(module: str, extra: str | None) -> Any:
    """Import ``module``, or fail with the install command for ``extra``.

    The one place a missing optional package is turned into an error. Every lazy import used to
    do this itself, and the four that existed disagreed: three raised ``RuntimeError`` and one
    raised ``ImportError``, so the CLI boundary called all of them internal bugs. A missing
    package is the single most user-fixable failure there is, and it was the one telling people
    to file a traceback.

    ``tests/cli/test_cli_errors.py`` walks every ``except ImportError`` handler under ``memrank/`` and
    fails when one raises something other than a :class:`MemrankError`. That check exists because
    the sibling test -- every exception CLASS subclasses ``MemrankError`` -- structurally cannot see
    this: nothing new is being defined, a builtin is being raised.

    Args:
        module: Import path, e.g. ``"anthropic"``.
        extra: The extra that provides it, e.g. ``"judge"``. ``None`` for a BASE dependency, where
            a failed import means the install is broken rather than incomplete -- telling someone
            to add an extra they already have would send them the wrong way.

    Returns:
        The imported module.

    Raises:
        MissingOptionalDependency: Naming the package and the command that fixes it.
    """
    from importlib import import_module

    try:
        return import_module(module)
    except ImportError as exc:
        # BOTH install shapes, because this function cannot tell which one the reader used, and
        # naming only the contributor's sent an outside user to `uv sync` from a directory with no
        # pyproject.toml -- a second dead end on top of the missing package.
        fix = (f"which is part of the {extra!r} extra. From a checkout: uv sync --extra {extra}. "
               f"From a tool install: uv tool install --force --with {module} <the git URL you "
               f"installed from>"
               if extra else
               "which is a base dependency, so this install is incomplete rather than missing an "
               "extra. From a checkout: uv sync. From a tool install, reinstall it: "
               "uv tool install --force --refresh <the git URL you installed from>")
        raise MissingOptionalDependency(
            f"this command needs the {module!r} package, {fix}") from exc


def wants_traceback() -> bool:
    """Whether an unexpected exception should surface its stack instead of one line.

    Read at call time, not import, for the same reason ``style.wants_color`` is: tests and
    wrapper scripts set it per invocation.

    There is deliberately no value that enables local variables. ``submit`` decrypts org
    credentials into a frame one line before the crash that prompted this module, and a
    traceback that renders locals would print them to the terminal -- on a laptop, which is
    exactly where those credentials are. The stack is what debugging needs; the bindings are
    only a leak.
    """
    return bool(os.environ.get("MEMRANK_DEBUG"))

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
"""Where this install came from -- and, when it is too old, where a newer one comes from.

``memrank version`` printing ``0.2.0`` and nothing else is useless the moment there is a
second user: the version in ``pyproject.toml`` moves rarely and the install branch moves
daily, so two people on different commits report the same string and a bug report cannot be
tied to code. This is the same failure :func:`memrank._installed_version` was written to
prevent, one level up -- there the version disagreed with the install, here the version
cannot distinguish two installs.

PEP 610 answers it without any build machinery: pip and uv both write ``direct_url.json``
beside the installed metadata, recording the URL a distribution was installed from and, for a
VCS install, the *resolved* commit. Standard metadata is deliberate -- uv's own
``uv-receipt.toml`` is private to uv and records the ref that was *requested* (``@dev``),
which is precisely the thing that cannot identify a build.

A distribution installed from a plain wheel or sdist has no ``direct_url.json`` at all; that
is a fact about the install, not an error, and it reads back as "no origin to report".
"""

from __future__ import annotations

import json
from typing import Any

from memrank import __version__

#: The one command that installs memrank and updates an existing install alike. Named here
#: rather than only in docs/install.md because errors that say "upgrade the CLI" have to say
#: HOW, and a second copy of this string is a second thing to forget when the ref moves.
#:
#: ``--force`` so it works whether or not memrank is already installed; ``--refresh`` because
#: uv resolves a git *branch* against its cache and will otherwise report nothing to upgrade
#: while ``dev`` has moved (astral-sh/uv#4317, #9146, #14684).
UPGRADE_COMMAND = (
    "uv tool install --force --refresh git+https://github.com/atomicstrata/memrank@dev"
)

#: PEP 610 names the file; the spec fixes it, so it is not configurable.
_DIRECT_URL = "direct_url.json"

#: Enough of a commit to identify it in a bug report, short enough to read in a version line.
_SHORT_COMMIT = 7


def _direct_url(distribution: str) -> dict[str, Any] | None:
    """The distribution's PEP 610 record, or ``None`` when it has none.

    Absent for a wheel/sdist install and for a source checkout that was never installed --
    both ordinary. A malformed record is *not* ordinary and raises: corrupt install metadata
    is worth a loud failure, not a quietly emptier version line.
    """
    from importlib.metadata import Distribution, PackageNotFoundError

    try:
        raw = Distribution.from_name(distribution).read_text(_DIRECT_URL)
    except PackageNotFoundError:
        return None
    return None if raw is None else json.loads(raw)


def describe_origin(distribution: str = "memrank") -> str | None:
    """One phrase naming where ``distribution`` was installed from, or ``None``.

    Three shapes, because PEP 610 records three: a VCS install carries ``vcs_info`` and is
    reported by resolved commit; an editable install carries ``dir_info.editable`` and is
    reported as the working tree it tracks, since its code is whatever is on disk right now;
    anything else is reported by URL.
    """
    record = _direct_url(distribution)
    if record is None:
        return None
    url = record.get("url", "")
    vcs = record.get("vcs_info")
    if vcs:
        return _vcs_origin(url, vcs)
    if record.get("dir_info", {}).get("editable"):
        return f"editable, {url}"
    return url or None


def _vcs_origin(url: str, vcs: dict[str, Any]) -> str:
    """``git+<url>@<ref>, commit <sha>`` -- the ref for orientation, the commit for truth."""
    ref = vcs.get("requested_revision")
    location = f"{vcs['vcs']}+{url}@{ref}" if ref else f"{vcs['vcs']}+{url}"
    commit = vcs.get("commit_id", "")
    return f"{location}, commit {commit[:_SHORT_COMMIT]}" if commit else location


def version_line() -> str:
    """What ``memrank version`` and ``memrank --version`` both print, so they cannot differ."""
    origin = describe_origin()
    return f"{__version__}  ({origin})" if origin else __version__

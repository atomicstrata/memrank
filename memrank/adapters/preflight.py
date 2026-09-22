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
"""Per-adapter preflight health check.

Probes the adapter with a throwaway retrieve before a benchmark run so an
unreachable backend fails loud (naming engine + URL) instead of producing a
misleading partial table. No silent fallback.
"""

from __future__ import annotations

from memrank.core import Memory
from memrank.errors import MemrankError

_PROBE_ISOLATION = "__memrank_preflight__"


class PreflightError(MemrankError):
    """Raised when an adapter is not ready to be benchmarked."""


#: Where an in-process adapter says its engine lives. Not a URL, because there is nothing to
#: connect to and quoting a placeholder address would send the reader looking for a server.
_NO_ADDRESS = "<in-process>"


def _remedies(adapter: Memory) -> str:
    """What to do about an engine that is not answering, in this installation's own terms.

    Two remedies, named at the moment of failure: point memrank at the engine that IS running, or
    have memrank start one. "No engine is running" is a fact about the machine, and the reader
    should not have to already know how memrank is told where to look.

    Every path named here exists in an installed copy. The message this replaced sent the reader
    to a shell script in the maintainers' own checkout -- which the person who most needs this
    message, an outsider whose engine memrank cannot reach, does not have (ATO-2125).
    """
    env = getattr(adapter, "base_url_env", None)
    settings = (f"the {env} environment variable or the adapter's `base_url` argument"
                if env else "the adapter's `base_url` argument")
    return (f"memrank sent that request and nothing answered. Point it somewhere else with "
            f"{settings}, or have memrank start a disposable engine of its own by re-running "
            f"with `--on local`.")


def preflight(adapter: Memory) -> None:
    """Probe ``adapter`` with a trivial retrieve; raise PreflightError on failure."""
    url = getattr(adapter, "base_url", _NO_ADDRESS)
    try:
        adapter.prepare(_PROBE_ISOLATION)
        adapter.retrieve("preflight", 1, _PROBE_ISOLATION, None)
    except Exception as exc:
        raise PreflightError(
            f"engine {adapter.name!r} is not answering at {url}: {exc}\n  {_remedies(adapter)}"
        ) from exc
    finally:
        # Cleanup talks to the same engine (AtomicMemory's resets its isolation source over
        # HTTP), so on an unreachable backend it raises too -- and a raise from `finally`
        # REPLACES the diagnosis with a second copy of the same connection error, which is how
        # this gate came to report a bare traceback instead of the engine's name. Tidying up is
        # never more important than the reason we are here.
        try:
            adapter.cleanup()
        except Exception:  # noqa: BLE001 - the probe's verdict outranks its housekeeping
            pass

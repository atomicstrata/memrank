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
"""Loading an org's BYOK credentials into a run.

The bridge between "who am I" and "what does this run spend". Every failure here is loud: a
run that started with a *partial* set of an org's credentials would fail deep inside an
engine with an unrelated-looking error, or -- worse -- complete against a fallback key and
publish a number attributed to the wrong configuration.
"""
from __future__ import annotations

from memrank.errors import MemrankError


class OrgSecretsError(MemrankError):
    """Raised when an org's credentials cannot be loaded. Never swallowed."""


def load_org_secrets(http, org: str) -> dict[str, str]:
    """Fetch ``org``'s credentials as ``{ENV_VAR: value}``.

    Args:
        http: An authenticated ``httpx.Client``-shaped object bound to the API.
        org: The org slug the run was launched for.

    Returns:
        The org's credentials. May be empty if the org has none stored -- that is a real
        answer, not an error, and the engine's own preflight will say which key is missing.

    Raises:
        OrgSecretsError: If the caller is not signed in, or is not a member of ``org``. Both
            are refusals to guess: continuing would silently spend somebody else's key.
    """
    response = http.get(f"/orgs/{org}/secrets/resolved")
    if response.status_code == 401:
        raise OrgSecretsError("not signed in -- run `memrank auth login`")
    if response.status_code == 403:
        raise OrgSecretsError(f"you are not a member of org {org!r}")
    if response.status_code != 200:
        raise OrgSecretsError(
            f"could not load credentials for {org!r}: {response.status_code} {response.text}")
    return response.json()

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
"""The CLI's HTTP client for the run-submission API.

``--on cloud`` no longer touches AWS from the laptop: submission, status, and listing go
through the memrank API, which holds the launch identity. Same shape as
``accounts.run_secrets`` -- an injected ``httpx.Client``-like object, status codes mapped
to typed errors, nothing swallowed.
"""
from __future__ import annotations

from collections.abc import Callable
from pathlib import Path
from typing import Any

from memrank.errors import MemrankError


class RunApiError(MemrankError):
    """The API refused or failed a run operation. ``code`` is machine-dispatchable --
    the CLI's auto-build loop triggers on ``image_missing`` and nothing else."""

    def __init__(self, message: str, *, code: str = "") -> None:
        super().__init__(message)
        self.code = code


def _refusal(response) -> RunApiError:
    """Map one non-2xx response to a typed error, keeping the server's code."""
    if response.status_code == 401:
        return RunApiError("not signed in -- run `memrank auth login`")
    if response.status_code == 403:
        return RunApiError("you are not a member of this org")
    detail = response.json().get("detail", {}) if _is_json(response) else {}
    code = detail.get("code", "") if isinstance(detail, dict) else ""
    message = detail.get("message", response.text) if isinstance(detail, dict) else response.text
    return RunApiError(f"{message} ({response.status_code})", code=code)


def _is_json(response) -> bool:
    return response.headers.get("content-type", "").startswith("application/json")


def submit_run(http, org: str, payload: dict[str, Any]) -> dict[str, Any]:
    """Submit one target's cloud run; returns the created run record (id, ARNs, artifact)."""
    response = http.post(f"/orgs/{org}/runs", json=payload)
    if response.status_code != 201:
        raise _refusal(response)
    return response.json()


def sync_run(http, org: str, run_id: str, payload: dict[str, Any]) -> dict[str, Any]:
    """Reconcile one finished local run into the org's universe; returns the stored record.

    PUT rather than POST: the id already exists (this machine minted it when the run was
    born), and re-syncing a run is a repair rather than a second run.
    """
    response = http.put(f"/orgs/{org}/runs/{run_id}", json=payload)
    if response.status_code != 200:
        raise _refusal(response)
    return response.json()


def kill_run(http, org: str, run_id: str) -> dict[str, Any]:
    """Stop one cloud run's task; returns the run's current (pre-stop) record.

    POST to a verb, not DELETE: the record must survive the kill. The API's stop is
    asynchronous -- the terminal state lands on the org record's next read.
    """
    response = http.post(f"/orgs/{org}/runs/{run_id}/kill")
    if response.status_code != 200:
        raise _refusal(response)
    return response.json()


def get_run(http, org: str, run_id: str) -> dict[str, Any]:
    """One run's record with freshly-merged live state."""
    response = http.get(f"/orgs/{org}/runs/{run_id}")
    if response.status_code != 200:
        raise _refusal(response)
    return response.json()


def run_logs(http, org: str, run_id: str, *, container: str | None = None,
             next_token: str | None = None) -> dict[str, Any]:
    """One page of a cloud run's container output.

    The API reads CloudWatch on the caller's behalf, which is the point: a member sees their own
    run's output with no AWS account. Returns ``{events, next_token, container, complete}`` --
    ``complete`` says the run reached a terminal state, so a follower knows to stop asking rather
    than inferring it from an empty page, which a running task produces all the time.
    """
    params = {k: v for k, v in (("container", container), ("next_token", next_token)) if v}
    response = http.get(f"/orgs/{org}/runs/{run_id}/logs", params=params)
    if response.status_code != 200:
        raise _refusal(response)
    return response.json()


def list_artifacts(http, org: str, run_id: str) -> list[dict[str, Any]]:
    """What a finished cloud run produced, as ``[{name, size}]``.

    Through the API, so reading your own results needs no AWS account -- the asymmetry the direct
    S3 fetch admitted to and this removes.
    """
    response = http.get(f"/orgs/{org}/runs/{run_id}/artifacts")
    if response.status_code != 200:
        raise _refusal(response)
    return response.json()["files"]


def fetch_artifact(http, org: str, run_id: str, name: str) -> bytes:
    """One artifact's bytes, whole in memory. Prefer :func:`download_artifact` for real runs --
    a locomo cell measured 83 MB, which is a size worth streaming rather than buffering."""
    response = http.get(f"/orgs/{org}/runs/{run_id}/artifacts/{name}")
    if response.status_code != 200:
        raise _refusal(response)
    return response.content


def stream_run_events(http, org: str, run_id: str,
                      on_event: Callable[[str, dict[str, Any]], bool]) -> None:
    """Read one run's server-sent events until ``on_event`` answers False or the stream ends.

    The live counterpart of polling ``progress.json``. ``on_event`` receives ``(event_type,
    payload)`` and returns whether to keep reading, so the caller owns when to stop -- a watch
    that has seen the run finish should not have to close a socket from underneath its own
    iterator to say so.

    Parsed here rather than by the caller because SSE framing is a transport detail: a blank line
    ends a frame, ``event:`` names the type, ``data:`` carries the payload, and a line starting
    ``:`` is a keepalive comment that exists only to hold the connection open.

    Raises:
        RunApiError: If the stream cannot be opened. Notably a 503 with ``events_not_configured``
            from a deployment that wires no transport -- which the caller is expected to catch and
            answer by polling, not by failing.
    """
    import json as _json

    with http.stream("GET", f"/orgs/{org}/runs/{run_id}/events",
                     headers={"Accept": "text/event-stream"}, timeout=None) as response:
        if response.status_code != 200:
            response.read()
            raise _refusal(response)
        kind = ""
        for line in response.iter_lines():
            if not line:
                continue                        # frame boundary; each frame here carries one event
            if line.startswith(":"):
                continue                        # keepalive comment
            field, _, value = line.partition(":")
            value = value.lstrip()
            if field == "event":
                kind = value
            elif field == "data":
                try:
                    payload = _json.loads(value)
                except ValueError:
                    continue                    # a frame this build cannot read is not fatal
                if not on_event(kind, payload):
                    return


def download_artifact(http, org: str, run_id: str, name: str, dest: Path,
                      on_chunk: Callable[[int], None] | None = None) -> Path:
    """Stream one artifact to ``dest``, reporting bytes as they land.

    Streamed rather than buffered because these are not small: a full locomo cell carries its
    per-query transcript and ingested corpus and measured 83 MB. Read whole into memory it is a
    minute of a command that has printed nothing, which reads as a hang -- and a caller that
    cannot report progress cannot help that.

    Written to a neighbouring ``.part`` and renamed, so an interrupted download never leaves a
    truncated artifact that :func:`memrank.runs.registry.cell_metrics` would later have to skip.
    """
    partial = dest.with_suffix(dest.suffix + ".part")
    with http.stream("GET", f"/orgs/{org}/runs/{run_id}/artifacts/{name}") as response:
        if response.status_code in _REDIRECTS:
            response.read()
            return _download_direct(response.headers["location"], partial, dest, on_chunk)
        if response.status_code != 200:
            response.read()
            raise _refusal(response)
        with partial.open("wb") as handle:
            for chunk in response.iter_bytes():
                handle.write(chunk)
                if on_chunk is not None:
                    on_chunk(len(chunk))
    partial.replace(dest)
    return dest


#: Statuses the artifact route uses to hand a caller straight to storage for a large file.
_REDIRECTS = (301, 302, 307, 308)

#: How many times a dropped direct download resumes before giving up. Three because the failure
#: this exists for was a single mid-transfer close at 216 MB of 327 MB, not a persistent refusal.
_RESUME_ATTEMPTS = 3


def _download_direct(url: str, partial: Path, dest: Path,
                     on_chunk: Callable[[int], None] | None) -> Path:
    """Follow a presigned URL to storage, resuming with ``Range`` if the transfer drops.

    A SEPARATE client, deliberately: the redirect points at S3, and forwarding this API's
    ``Authorization`` header there fails with "only one auth mechanism allowed" -- the presigned
    URL carries its own. ``httpx.Client`` also does not re-send our base_url's headers to another
    host, but constructing a bare client says so rather than relying on that.

    Resume is what the redirect buys. Proxied through the API a dropped transfer had to start over
    (and did not survive the retry either); against storage, ``Range`` continues from the bytes
    already on disk.
    """
    import httpx

    for attempt in range(_RESUME_ATTEMPTS):
        have = partial.stat().st_size if partial.exists() else 0
        headers = {"Range": f"bytes={have}-"} if have else {}
        try:
            with httpx.Client(timeout=_DOWNLOAD_TIMEOUT, follow_redirects=True) as direct:
                with direct.stream("GET", url, headers=headers) as response:
                    if response.status_code not in (200, 206):
                        response.read()
                        raise RunApiError(
                            f"storage refused the download ({response.status_code})")
                    # 200 to a ranged request means the server ignored it and restarted the body;
                    # appending would corrupt the file, so start the file over instead.
                    resuming = bool(have) and response.status_code == 206
                    mode = "ab" if resuming else "wb"
                    # A restart re-sends bytes the meter has already counted. Tell it to rewind,
                    # or a resumed 271 MB download reports more than the file's size.
                    if on_chunk is not None and not resuming and have:
                        on_chunk(-have)
                    with partial.open(mode) as handle:
                        for chunk in response.iter_bytes():
                            handle.write(chunk)
                            if on_chunk is not None:
                                on_chunk(len(chunk))
            partial.replace(dest)
            return dest
        except httpx.HTTPError:
            if attempt == _RESUME_ATTEMPTS - 1:
                raise
    raise RunApiError("download did not complete")


#: Generous because these are hundreds of megabytes over a home connection, and the read timeout
#: applies between chunks rather than to the whole transfer.
_DOWNLOAD_TIMEOUT = 300


def list_runs(http, org: str, *, mine: bool = True, limit: int,
              before: str | None = None) -> dict[str, Any]:
    """An org's runs, or just the caller's.

    Returns the whole envelope rather than only the rows: ``scope`` says which filter the
    server actually applied, and a deployment that predates the parameter omits it. The
    caller needs that to know whether it may describe the rows as its own.
    """
    params = {"mine": mine, "limit": limit, **({"before": before} if before else {})}
    response = http.get(f"/orgs/{org}/runs", params=params)
    if response.status_code != 200:
        raise _refusal(response)
    return response.json()


def authenticated_client():
    """An httpx client bound to the configured API and carrying the stored token.

    Lives beside the calls it serves because both the submission path and the listing path
    need it, and the listing path (``runs_cli``) cannot import ``runner`` -- ``runner`` imports
    it. Raises rather than guessing at an unauthenticated request.
    """
    import httpx

    from memrank import config
    from memrank.accounts.credentials import CredentialError, CredentialStore

    try:
        token = CredentialStore().load()
    except CredentialError as exc:
        # Its own code, so callers can tell "you are not signed in" from "this machine could
        # not read your session" -- the second is a local permission problem and reporting it as
        # the first sends the user to re-authenticate for no reason.
        raise RunApiError(str(exc), code="credential_store") from exc
    if token is None:
        raise RunApiError("not signed in -- run `memrank auth login`", code="no_session")
    return httpx.Client(base_url=config.memrank_api_url(), timeout=60,
                        headers={"Authorization": f"Bearer {token}"})

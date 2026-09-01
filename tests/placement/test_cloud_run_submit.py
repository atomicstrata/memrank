"""`memrank submit <ref> <bench> --on cloud --org <slug>` -- submission THROUGH THE API.

The laptop holds no AWS identity: the CLI checks the image contract against its own
checkout, POSTs each target to the memrank API, and records the server-minted run locally
so `memrank ps` sees it. The behaviors guarded here are the ones that would each be
discovered the expensive way: no submission without an org, no local work a submission has
no engine for, no waiting unless asked, and a run record `ps` reads as running, not stale.
"""
from __future__ import annotations

import time

import pytest
from typer.testing import CliRunner

from memrank.orchestration import cloud as cloud_mod
from memrank.orchestration import sweep as sweep_mod
from memrank.placement import run_api_client
from memrank.runner import app
from memrank.runs import status as run_status

runner = CliRunner()


class _FakeHttp:
    def __enter__(self):
        return self

    def __exit__(self, *exc):
        return False


@pytest.fixture
def api(tmp_path, monkeypatch):
    """A submittable environment with the API stubbed. Records every POST."""
    monkeypatch.setenv("MEMRANK_RUNS_DIR", str(tmp_path / "runs"))
    captured: dict = {"submits": [], "polls": 0, "states": ["stopped-success"]}
    monkeypatch.setattr(cloud_mod, "_api_client", lambda: _FakeHttp())

    def _submit(http, org, payload):
        captured["submits"].append((org, payload))
        n = len(captured["submits"])
        rid = f"20260801-12000{n}__{payload['benchmark']}__r{n}"
        return {"id": rid, "state": "submitted", "taskdef_arn": "arn:td",
                "task_arn": f"arn:aws:ecs:us-east-1:1:task/bench/{n}deadbeef",
                "cluster": "bench", "region": "us-east-1", "log_group": "/ecs/bench",
                "artifact": {"bucket": "bkt", "prefix": f"cloud-runs/{rid}"}}

    def _get(http, org, run_id):
        state = captured["states"][min(captured["polls"], len(captured["states"]) - 1)]
        captured["polls"] += 1
        failed = state == "stopped-failed"
        return {"id": run_id, "state": state, "exit_code": 1 if failed else 0,
                "stopped_reason": "Essential exited" if failed else ""}

    monkeypatch.setattr(run_api_client, "submit_run", _submit)
    monkeypatch.setattr(run_api_client, "get_run", _get)
    monkeypatch.setattr(time, "sleep", lambda s: None)
    captured["runs_root"] = tmp_path / "runs"
    return captured


def _run(*args):
    return runner.invoke(app, ["submit", *args])


def test_submitting_returns_immediately_and_reports_the_task(api):
    result = _run("word-overlap", "demo", "--on", "cloud", "--org", "acme")
    assert result.exit_code == 0, result.output
    assert "submitted" in result.output
    assert "deadbeef" in result.output
    assert api["polls"] == 0                        # returned without waiting


def test_cloud_without_an_org_is_refused(api):
    """Runs are recorded against an org; submitting without one has no owner to bill."""
    result = _run("word-overlap", "demo", "--on", "cloud")
    assert result.exit_code != 0
    assert "--org" in result.output
    assert api["submits"] == []


def test_the_run_appears_in_ps_as_running_not_stale(api):
    """The regression that made this milestone necessary: classify() gated on a local pid."""
    assert _run("word-overlap", "demo", "--on", "cloud", "--org", "acme").exit_code == 0
    runs = run_status.active_runs(api["runs_root"])
    assert len(runs) == 1
    assert runs[0]["status"] == "running"
    assert runs[0]["placement"] == "cloud"
    assert runs[0]["pid"] is None
    assert runs[0]["task_arn"].endswith("deadbeef")


def test_the_local_record_carries_the_servers_run_id(api):
    """One name across the local dir, the S3 prefix, and the org's runs row."""
    assert _run("word-overlap", "demo", "--on", "cloud", "--org", "acme").exit_code == 0
    assert [d.name for d in api["runs_root"].iterdir()] == ["20260801-120001__demo__r1"]


def test_the_payload_argv_is_the_remote_rebuild_not_this_processes(api):
    _run("word-overlap", "demo", "--on", "cloud", "--org", "acme")
    org, payload = api["submits"][0]
    assert org == "acme"
    assert payload["argv"][:3] == ["submit", "word-overlap", "demo"]
    assert "--on" not in payload["argv"] and "--org" not in payload["argv"]
    assert payload["experiment_id"]
    assert payload["experiment_spec"]["eval_ref"] == "demo"


def test_a_sweep_posts_one_run_per_target_each_with_its_own_record(api):
    result = _run("no-context,fixed-context,full-context", "demo", "--on", "cloud", "--org", "acme")
    assert result.exit_code == 0, result.output
    assert [p["target_ref"] for _, p in api["submits"]] == ["no-context", "fixed-context", "full-context"]
    assert len(list(api["runs_root"].iterdir())) == 3
    arns = {r["task_arn"] for r in run_status.active_runs(api["runs_root"])}
    assert len(arns) == 3


def _watch(monkeypatch, run_id):
    """`memrank watch <id>` with the API client resolution stubbed to the fixture's."""
    from memrank.cli import watch as watch_cli

    monkeypatch.setattr(watch_cli, "_cloud_client", lambda: (_FakeHttp(), "acme"))
    return runner.invoke(app, ["watch", run_id])


def test_a_watched_run_fetches_artifacts_and_mirrors_to_mlflow(api, monkeypatch):
    """watch inherits --wait's promise: a finished cloud run looks like a local one; MLflow
    is part of "looks like"."""
    from memrank.cli import watch as watch_cli

    api["states"] = ["running", "stopped-success"]
    # Fetched through the API rather than from S3: reading your own results needs no AWS account.
    monkeypatch.setattr(watch_cli.run_api_client, "list_artifacts",
                        lambda http, org, rid: [{"name": "summary__demo.json", "size": 2}])
    monkeypatch.setattr(watch_cli.run_api_client, "download_artifact",
                        lambda http, org, rid, name, dest, *a, **kw: dest.write_bytes(b"{}"))
    mirrored: list = []
    monkeypatch.setattr(sweep_mod, "_mirror_to_mlflow", mirrored.append)

    assert _run("word-overlap", "demo", "--on", "cloud", "--org", "acme").exit_code == 0
    result = _watch(monkeypatch, "20260801-120001__demo__r1")
    assert result.exit_code == 0, result.output
    assert len(mirrored) == 1
    record = run_status.active_runs(api["runs_root"])[0]
    assert record["status"] == "done"
    assert record["pid"] is None


def test_a_failed_cloud_run_does_not_mirror(api, monkeypatch):
    """Nothing was fetched, so there is nothing truthful to mirror."""
    api["states"] = ["stopped-failed"]
    mirrored: list = []
    monkeypatch.setattr(sweep_mod, "_mirror_to_mlflow", mirrored.append)

    assert _run("word-overlap", "demo", "--on", "cloud", "--org", "acme").exit_code == 0
    result = _watch(monkeypatch, "20260801-120001__demo__r1")
    assert result.exit_code == 1
    assert mirrored == []


def test_watch_giving_up_is_not_the_same_as_failing(api, monkeypatch):
    """The task keeps running and still uploads on success; exit 2 says so distinctly."""
    from memrank.cli import watch as watch_cli

    api["states"] = ["running"]
    monkeypatch.setattr(watch_cli, "WATCH_TIMEOUT_S", 0.0)

    assert _run("word-overlap", "demo", "--on", "cloud", "--org", "acme").exit_code == 0
    result = _watch(monkeypatch, "20260801-120001__demo__r1")
    assert result.exit_code == 2
    assert "still running" in result.output


def test_a_bare_submission_names_no_image_and_carries_its_contract(api, monkeypatch):
    """EVERY submission runs the platform's pinned harness: the payload names no image, and
    compatibility rides on the contract number the server checks against its own lineage.

    This used to be the default among three modes. It is now the only one -- naming a build
    assumed a checkout, a Docker daemon and ECR rights, and swapped only the image while the API
    went on rendering the task command from its own."""
    from memrank.placement.cloud_submit import REMOTE_CLI_CONTRACT

    result = _run("word-overlap", "demo", "--on", "cloud", "--org", "acme")

    assert result.exit_code == 0, result.output
    _, payload = api["submits"][0]
    assert "image_tag" not in payload
    assert payload["cli_contract"] == REMOTE_CLI_CONTRACT


def test_the_payload_carries_parsed_facts_not_the_raw_ref(api):
    """The server mints run ids and rows from the positional facts, and a raw ref there put a
    `:` into a string that becomes a shell token and an S3 key -- refused as an unsafe run id on
    2026-08-13, after the eval-refs migration started sending `beam:100k-smoke` as `benchmark`.
    The argv keeps the canonical ref; the facts travel parsed beside it."""
    result = _run("word-overlap", "beam:100k-smoke", "--on", "cloud", "--org", "acme")

    assert result.exit_code == 0, result.output
    _, payload = api["submits"][0]
    assert payload["benchmark"] == "beam"
    assert payload["tier"] == "100k" and payload["slice"] == "smoke"
    assert payload["argv"][:3] == ["submit", "word-overlap", "beam:100k-smoke"]
    assert ":" not in payload["benchmark"]


def test_a_bare_ref_submits_its_canonical_spelling(api):
    """`beam` runs, but what it RAN is `beam:100k` -- the argv must say so, and the facts must
    carry the default tier the bare form resolves to."""
    result = _run("word-overlap", "beam", "--on", "cloud", "--org", "acme")

    assert result.exit_code == 0, result.output
    _, payload = api["submits"][0]
    assert payload["benchmark"] == "beam" and payload["tier"] == "100k"
    assert payload["argv"][2] == "beam:100k"


@pytest.mark.parametrize("flag", ["--image-tag", "--no-auto-push", "--allow-unverified-image"])
def test_the_harness_developer_door_is_closed(api, flag):
    """Choosing a harness build is not a caller's decision, and was never fully possible anyway.

    `--image-tag head` swapped the harness image but not the task command, which the API renders
    from ITS OWN build -- so a branch-built harness ran inside the deployed command shape. It also
    assumed a memrank checkout, a Docker daemon and ECR push rights, none of which a user of the
    instrument has. Unmerged changes reach the cloud through `dev`, CI and staging.

    Asserted per flag rather than as one string search, so re-adding any single one fails here.
    """
    result = _run("word-overlap", "demo", "--on", "cloud", "--org", "acme", flag, "head")

    assert result.exit_code != 0, f"{flag} was accepted"
    assert "No such option" in result.output or "no such option" in result.output.lower()
    assert not api["submits"], "a rejected flag must not reach the API"


def test_wait_no_longer_exists(api):
    """Waiting is a verb now (`memrank watch`), not a modifier -- the flag is gone."""
    result = _run("word-overlap", "demo", "--wait")
    assert result.exit_code != 0
    assert "no such option" in result.output.lower()


def test_the_legacy_adapter_form_is_retired(api):
    """It was already refused for cloud, because a task definition is generated from a
    manifest and this form names no manifest. It is now refused everywhere, and says so."""
    result = _run("--adapter", "word-overlap", "--benchmark", "demo", "--on", "cloud",
                  "--org", "acme")
    assert result.exit_code != 0
    assert "retired" in result.output and "<target> <eval>" in result.output


def test_not_signed_in_is_a_clear_refusal(tmp_path, monkeypatch):
    """Deliberately without the `api` fixture: the REAL _api_client runs, finds no stored
    token, and must refuse with the command to run next."""
    from memrank.accounts import credentials

    monkeypatch.setenv("MEMRANK_RUNS_DIR", str(tmp_path / "runs"))
    monkeypatch.setattr(credentials.CredentialStore, "load", lambda self: None)

    result = _run("word-overlap", "demo", "--on", "cloud", "--org", "acme")
    assert result.exit_code != 0
    # `memrank auth login` may be split across lines by the error box's wrapping.
    assert "login" in result.output

# --- routing from configuration, not from flags ---------------------------------------------- #

@pytest.fixture
def configured(api, monkeypatch, tmp_path):
    """A machine that has logged in: cloud placement and an org, both from settings."""
    from memrank import settings

    monkeypatch.setenv("MEMRANK_CONFIG_DIR", str(tmp_path / "cfg"))
    for spec in settings.SETTINGS:
        monkeypatch.delenv(spec.env, raising=False)
    settings.put("defaults.on", "cloud")
    settings.put("defaults.org", "acme")
    return api


def test_a_configured_machine_submits_with_no_routing_flags(configured):
    """The phase's whole point: `submit <target> <eval>` and nothing else."""
    result = _run("word-overlap", "demo")

    assert result.exit_code == 0, result.output
    org, payload = configured["submits"][0]
    assert org == "acme"
    assert payload["target_ref"] == "word-overlap"


def test_an_explicit_flag_still_beats_the_configured_default(configured):
    """Configuration is a default, not a policy; the flag on the line wins."""
    result = _run("word-overlap", "demo", "--on", "none",
                  "--output-dir", str(configured["runs_root"].parent / "out"))

    assert result.exit_code == 0, result.output
    assert configured["submits"] == []          # ran locally, nothing submitted


def test_a_configured_org_never_reaches_a_local_runs_credentials(api, monkeypatch, tmp_path):
    """`--org` on a LOCAL run pulls the org's decrypted keys onto this machine. If the
    configured default reached that path, signing in would silently change what every local
    run spends -- routing configuration deciding what a run costs."""
    from memrank import runner as runner_module
    from memrank import settings

    monkeypatch.setenv("MEMRANK_CONFIG_DIR", str(tmp_path / "cfg"))
    for spec in settings.SETTINGS:
        monkeypatch.delenv(spec.env, raising=False)
    settings.put("defaults.org", "acme")        # logged in, but placement left local
    pulled: list = []
    monkeypatch.setattr(runner_module, "_load_org_credentials", pulled.append)

    result = _run("word-overlap", "demo",
                  "--output-dir", str(tmp_path / "out"))

    assert result.exit_code == 0, result.output
    assert pulled == []

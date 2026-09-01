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
"""Markdown links, checked rather than trusted.

`tests/repo/test_public_boundary.py` proves the CODE boundary holds: no public module imports an
internal one. This is the same question asked of prose, and it has the same two failure modes.

1. A link that resolves to nothing. Documentation that points at a file which moved is worse than
   documentation that says nothing -- it costs a reader the trip.
2. **A PUBLIC document linking an INTERNAL one.** That link resolves perfectly here and is dead in
   the published tree, because the file it names is never copied there. Nothing in this repository
   can notice on its own: the target is right there on disk.

Both are pinned rather than merely counted. The two sets below are ratchets, asserted in BOTH
directions -- a new offender fails, and so does an entry that has been fixed and not removed. That
is what stops a list of known problems from quietly becoming a list of tolerated ones.
"""
from __future__ import annotations

import re
import urllib.parse
from pathlib import Path

import pytest

from tests.repo.test_public_boundary import (  # noqa: F401
    INTERNAL,
    PUBLIC,
    _classify,
    manifest,
    tracked,
)

ROOT = Path(__file__).resolve().parents[2]

#: Inline `[text](target)` only. Reference-style definitions in this repository are all external
#: URLs, and an HTML `<a href>` appears nowhere in the tracked markdown.
LINK = re.compile(r"\[[^\]]*\]\(\s*([^)\s]+)")

#: Links that already resolve to nothing, recorded so the rot stops here. Overwhelmingly stale
#: module paths in dated design docs written before the runner split, plus four `{R}/` template
#: variables that were never expanded. Every one now lives in an internal document -- the single
#: PUBLIC dangling link, `docs/methodology.md` -> `PRD_Memrank_v2.md`, was de-linked rather than
#: pinned, because a public document must not ship a promise it cannot keep. Paths are
#: `localdocs/...` since Phase 4. This set may only shrink.
KNOWN_BROKEN_LINKS = {
    "deploy/README.md|../memrank/receipt.py#L96",
    "deploy/README.md|../memrank/storage_client.py#L155",
    "localdocs/PRD_Memrank.md|{R}/2026-08-03-eval-landscape/README.md",
    "localdocs/PRD_Memrank.md|{R}/2026-08-03-eval-landscape/inventory.md",
    "localdocs/PRD_Memrank.md|{R}/2026-08-04-demand-signal-sources/signals.md",
    "localdocs/PRD_Memrank.md|{R}/2026-08-04-eval-business-models/segments.md",
    "localdocs/experimental-prds/PRD_Memrank_v1.md|../tech-debt.md",
    "localdocs/experimental-prds/PRD_Memrank_v1.md|2026-08-02-audit-interface-divergence.md",
    "localdocs/experimental-prds/PRD_Memrank_v1.md|interface-model.md",
    "localdocs/experimental-prds/PRD_Memrank_v2.md|../SPEC.md",
    "localdocs/experimental-prds/PRD_Memrank_v2.md|PRD_%20AtomicBench.md",
    "localdocs/experimental-prds/PRD_Memrank_v2.md|research/2026-07-20-lmarena-evaluation-methodology.md",
    "localdocs/experimental-prds/PRD_Memrank_v2.md|research/2026-07-21-memory-field-labs-and-open-problems.md",
    "localdocs/experimental-prds/PRD_Memrank_v4.md|PRD_%20AtomicBench.md",
    "localdocs/experimental-prds/PRD_Memrank_v4.md|product-direction-2026-07-28.md",
    "localdocs/experimental-prds/PRD_Memrank_v4.md|research/2026-08-03-eval-landscape/README.md",
    "localdocs/experimental-prds/PRD_Memrank_v4.md|research/agentic-ai-summit-2026.md",
    "localdocs/experimental-prds/PRD_Memrank_v5.md|research/2026-08-03-eval-landscape/README.md",
    "localdocs/experimental-prds/PRD_Memrank_v5.md|research/2026-08-04-eval-business-models/README.md",
    "localdocs/experimental-prds/PRD_Memrank_v5.md|research/2026-08-04-recursive-self-improvement/README.md",
    "localdocs/experimental-prds/PRD_Memrank_v5.md|research/2026-08-04-small-models-local-memory/README.md",
    "localdocs/experimental-prds/PRD_Memrank_v5.md|research/agentic-ai-summit-2026.md",
    "localdocs/infrastructure/2026-07-21-audit-infrastructure-expectations.md|../../db/migrations/0003_arena_serving.sql",
    "localdocs/infrastructure/2026-07-21-audit-infrastructure-expectations.md|../../memrank/leaderboard_bundle.py",
    "localdocs/infrastructure/2026-07-21-audit-infrastructure-expectations.md|../../memrank/leaderboard_store.py",
    "localdocs/infrastructure/2026-07-21-audit-infrastructure-expectations.md|../../web/_headers",
    "localdocs/research/2026-07-29-memory-engine-configurability-and-forks.md|../../memrank/receipt.py#L170-L175",
    "localdocs/research/2026-07-31-device-dependence-and-comparability.md|../../memrank/compare_versions.py#L82",
    "localdocs/research/2026-07-31-device-dependence-and-comparability.md|../../memrank/leaderboard.py#L155-L156",
    "localdocs/research/2026-07-31-device-dependence-and-comparability.md|../../memrank/leaderboard.py#L269",
    "localdocs/superpowers/evidence/2026-07-30-m4-control-arms.md|../../PRD_Memrank_v2.md",
    "localdocs/superpowers/plans/2026-07-22-web-legacy-retirement.md|../../Documents/projects/atomicstrata/memrank/docs/infrastructure/2026-07-22-audit-web-legacy-retirement.md",
    "localdocs/superpowers/plans/2026-08-11-beam-protocol-fidelity.md|../../../memrank/judge.py",
    "localdocs/superpowers/plans/2026-08-11-beam-protocol-fidelity.md|../../../memrank/judge_client.py",
    "localdocs/superpowers/plans/2026-08-11-beam-protocol-fidelity.md|../../../memrank/judge_prompts.py",
    "localdocs/superpowers/plans/2026-08-11-beam-protocol-fidelity.md|../../../memrank/receipt.py",
    "localdocs/superpowers/specs/2026-07-25-ingestion-latency-benchmark-design.md|../../../memrank/compare.py",
    "localdocs/superpowers/specs/2026-07-27-memory-eval-in-a-box-design.md|../../../memrank/cost.py",
    "localdocs/superpowers/specs/2026-07-27-memory-eval-in-a-box-design.md|../../../memrank/judge.py",
    "localdocs/superpowers/specs/2026-07-27-memory-eval-in-a-box-design.md|../../../memrank/judge_client.py",
    "localdocs/superpowers/specs/2026-07-27-memory-eval-in-a-box-design.md|../../../memrank/judge_prompts.py",
    "localdocs/superpowers/specs/2026-07-27-memory-eval-in-a-box-design.md|../../../memrank/leaderboard_bundle.py",
    "localdocs/superpowers/specs/2026-07-27-memory-eval-in-a-box-design.md|../../../memrank/leaderboard_store.py",
    "localdocs/superpowers/specs/2026-07-27-memory-eval-in-a-box-design.md|../../../memrank/receipt.py",
    "localdocs/superpowers/specs/2026-07-27-memory-eval-in-a-box-design.md|../../../memrank/run_registry.py",
    "localdocs/superpowers/specs/2026-07-27-memory-eval-in-a-box-design.md|../../../memrank/scoring.py",
    "localdocs/superpowers/specs/2026-07-27-memory-eval-in-a-box-design.md|../../../scripts/cloud-run-matrix.sh",
    "localdocs/superpowers/specs/2026-07-27-memory-eval-in-a-box-design.md|../../../scripts/cloud-run.sh",
    "localdocs/superpowers/specs/2026-07-30-eval-run-abstractions-design.md|../../../deploy/ecs/taskdef.mem0.json.tpl",
    "localdocs/superpowers/specs/2026-07-30-eval-run-abstractions-design.md|../../../memrank/adapters/baseline.py",
    "localdocs/superpowers/specs/2026-07-30-eval-run-abstractions-design.md|../../../memrank/engine_provenance.py",
    "localdocs/superpowers/specs/2026-07-30-eval-run-abstractions-design.md|../../../memrank/mlflow_export.py",
    "localdocs/superpowers/specs/2026-07-30-eval-run-abstractions-design.md|../../../memrank/requirements.py",
    "localdocs/superpowers/specs/2026-07-30-eval-run-abstractions-design.md|../../../memrank/run_status.py",
    "localdocs/superpowers/specs/2026-07-30-eval-run-abstractions-design.md|../../../memrank/secret_store.py",
    "localdocs/superpowers/specs/2026-07-30-eval-run-abstractions-design.md|../../../scripts/cloud-run.sh",
    "localdocs/superpowers/specs/2026-07-30-eval-run-abstractions-design.md|../../../scripts/eval-configs/mem0-voyage.env",
    "localdocs/superpowers/specs/2026-07-31-remote-mlflow-design.md|../../../.env.example",
    "localdocs/superpowers/specs/2026-07-31-remote-mlflow-design.md|../../../memrank/cloud_artifacts.py",
    "localdocs/superpowers/specs/2026-07-31-remote-mlflow-design.md|../../../memrank/mlflow_export.py",
    "localdocs/superpowers/specs/2026-07-31-remote-mlflow-design.md|../../../memrank/storage_client.py",
}

#: Public documents linking documents that `publish.toml` classifies internal -- every one a promise
#: the published tree cannot keep. **Empty, and it stays empty.** It held 33 entries when this file
#: landed; Phase 4 cleared them by promoting the protocol-fidelity evidence the benchmark cards rest
#: on and de-linking the build-lane references. The assertion below is what keeps the next one out,
#: so an entry added here is a decision to publish a broken promise, not a stopgap.
KNOWN_PUBLIC_TO_INTERNAL_LINKS: set[str] = set()


def _relative_links(path: str) -> list[tuple[str, str]]:
    """(raw, resolved-repo-path) for every in-repo link in one markdown file.

    External schemes and bare anchors are not this test's business. A percent-encoded target is
    decoded first: `PRD_%20AtomicBench.md` names a real tracked file whose name contains a space,
    and treating the escape literally would report a false break.
    """
    base = Path(path).parent
    found = []
    source = ROOT / path
    if not source.is_file():
        return found          # tracked but absent: a projection that dropped this prefix
    for match in LINK.finditer(source.read_text(encoding="utf-8", errors="replace")):
        raw = match.group(1)
        if raw.startswith(("http://", "https://", "mailto:", "#", "<")):
            continue
        target = urllib.parse.unquote(raw.split("#")[0]).strip()
        if not target or target.startswith("/"):
            if target:
                found.append((raw, ""))
            continue
        try:
            found.append((raw, str((base / target).resolve().relative_to(ROOT))))
        except ValueError:
            found.append((raw, ""))
    return found


@pytest.fixture(scope="module")
def markdown(tracked) -> tuple[str, ...]:
    return tuple(p for p in tracked if p.endswith(".md"))


def _evaluable(pinned: set[str], markdown: tuple[str, ...]) -> set[str]:
    """The pins whose source document is present in THIS tree.

    Both ratchets below assert that a fixed entry has been removed, and that assertion is only
    meaningful for a document the scan actually read. Most pins name `localdocs/` sources, which
    the published tree does not contain -- evaluating them there would report all 63 as "now
    resolved" and fail a test that is otherwise the public tree's only link check. Scoping to
    present sources keeps the ratchet exact here and correct in the projection, without weakening
    it: a pin whose source IS present and no longer dangles still fails.
    """
    present = {path for path in markdown if (ROOT / path).is_file()}
    return {pin for pin in pinned if pin.split("|", 1)[0] in present}


def test_every_relative_link_resolves(markdown, tracked):
    """A link into the repository must name something the repository has."""
    known = set(tracked)
    dangling = {f"{path}|{raw}"
                for path in markdown
                for raw, resolved in _relative_links(path)
                if not resolved or (resolved not in known and not (ROOT / resolved).is_dir())}

    assert dangling <= KNOWN_BROKEN_LINKS, (
        f"{len(dangling - KNOWN_BROKEN_LINKS)} new dangling link(s):\n  "
        + "\n  ".join(sorted(dangling - KNOWN_BROKEN_LINKS)[:20]))
    assert (fixed := _evaluable(KNOWN_BROKEN_LINKS, markdown) - dangling) == set(), (
        f"{len(fixed)} link(s) in KNOWN_BROKEN_LINKS now resolve -- remove them so the ratchet "
        f"keeps its grip:\n  " + "\n  ".join(sorted(fixed)[:20]))


def test_no_public_document_links_an_internal_one(manifest, markdown, tracked):
    """The docs-side analogue of `test_no_public_module_imports_an_internal_one`.

    This one cannot be found by reading the published tree either, because the reader has no way
    to know the link was ever meant to point somewhere. It has to be caught here.
    """
    known = set(tracked)
    leaks = {f"{path}|{resolved}"
             for path in markdown if _classify(path, manifest)[0] == PUBLIC
             for _, resolved in _relative_links(path)
             if resolved in known and _classify(resolved, manifest)[0] == INTERNAL}

    assert leaks <= KNOWN_PUBLIC_TO_INTERNAL_LINKS, (
        f"{len(leaks - KNOWN_PUBLIC_TO_INTERNAL_LINKS)} new public->internal link(s) -- the "
        f"published tree would not contain the target:\n  "
        + "\n  ".join(sorted(leaks - KNOWN_PUBLIC_TO_INTERNAL_LINKS)[:20]))
    assert (fixed := _evaluable(KNOWN_PUBLIC_TO_INTERNAL_LINKS, markdown) - leaks) == set(), (
        f"{len(fixed)} entr(ies) no longer leak -- remove them from "
        f"KNOWN_PUBLIC_TO_INTERNAL_LINKS:\n  " + "\n  ".join(sorted(fixed)[:20]))


def test_the_scan_reaches_the_documents_that_matter(markdown):
    """Guards the guard: an extraction that silently matched nothing would make both tests pass.

    Both the pinned documents and the link floor are PUBLIC ones, so this states the same thing in
    this repository and in the published projection. A floor counted over the whole tree would be
    a floor only this repository can clear, and the guard would fail wherever it matters most.

    The floor was 100 while `docs/` held 33 documents. ATO-1886 cut it to the eight an outsider
    needs, which carry 32 links between them; a floor of 20 still catches an extraction that
    matched nothing without pinning the number of cross-references the kept docs happen to have.
    """
    scanned = set(markdown)
    for must_cover in ("README.md", "docs/README.md", "docs/methodology.md",
                       "docs/adapter-contract.md"):
        assert must_cover in scanned, f"{must_cover} fell out of the corpus"
    public_links = sum(len(_relative_links(p)) for p in markdown if p.startswith("docs/"))
    assert public_links > 20, f"only {public_links} links found under docs/ -- extraction is broken"

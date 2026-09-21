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
"""The seven are the Python surface, and the names they replaced cannot creep back.

`tests/repo/test_docs_teach_the_current_cli.py` records why this is enumerated rather than
left to per-file vigilance: the CLI's cutover was done in three passes, each one missed what
the last had touched, and sixteen call sites were still printing refused commands months
later. This is the same control for the Python surface, and it has the same two halves.

**The surface.** `memrank.__all__` is pinned to the seven, the kinds a person subclasses, the
measures memrank ships and the two readings above the run -- so a name cannot join the first
thing a person reads without a deliberate edit here -- and `memrank.run`'s parameters are
checked by position: the first two are `system` and `evaluation`. The previous run keeps its
own contract, checked here too: it is `memrank.evaluation.api.run`, its first two parameters
are `engine` and `evaluation`, and every deprecated spelling is keyword-only and named in
:data:`memrank.evaluation.api.DEPRECATED_PARAMETERS`. A third spelling fails here.

**The corpus.** Every live document, example and script is scanned for the spellings this
step retired. A retired spelling in an instruction is a person typing it tomorrow.

**What is deliberately not here.** `MemoryAdapter`, `Benchmark` and `EvalResult` are
*deprecated*, not retired: they still work, and plan step 22 is what removes them and extends
the table below. And `memrank submit TARGET EVAL` keeps its own nouns -- *target* is the
command line's word for a catalog entry, this step did not change it, and
`examples/more/custom-target/` is about exactly that. Only Python spellings are
scanned, never a file name.
"""
from __future__ import annotations

import inspect
import re
from pathlib import Path

import pytest

import memrank
import memrank.core
from memrank.evaluation.api import DEPRECATED_PARAMETERS
from memrank.evaluation.api import run as cell_run
from memrank.evaluation.result import EvalResult

ROOT = Path(__file__).resolve().parents[2]

#: The whole of what `import memrank` advertises: the seven, the kinds a person subclasses,
#: the measures memrank ships, the two readings above the run, the three value types a task or
#: a recall is written with (`Document`, `Expected`, `Recall`), and the version. Spelled out
#: rather than counted, so that adding a name is a visible edit to this list and a reader can
#: see what the surface is without running anything.
SURFACE = ("Assistant", "Clearing", "Decider", "Document", "Evaluation", "Expected",
           "FailureRate", "Judge", "Latency", "Measure", "Memory", "Model", "Paired", "Recall",
           "Result", "Retriever", "Scope", "System", "Task", "Trace", "Value", "WordMatch",
           "__version__", "evaluation", "measure", "paired", "run", "system")

#: The two positional parameters of `memrank.run`, in order.
POSITIONAL = ("system", "evaluation")
#: And of the previous run, which the command line and the cloud still call.
CELL_POSITIONAL = ("engine", "evaluation")

#: ``{regex: what to write instead}``. Each pattern is a PYTHON spelling this step retired.
RETIRED = {
    r"\brun\(\s*target\s*=": "run(engine=...)",
    r"\brun\([^)]*\beval\s*=": "run(evaluation=...)",
    r"\bresult\.target\b": "result.engine_ref",
    r"\bresult\.adapter\b": "result.engine",
    r"\bresult\.benchmark\b": "result.evaluation",
    r"\bmemrank\.EvalResult\b": "memrank.Result",
}
RETIRED_PATTERNS = {re.compile(pattern): instead for pattern, instead in RETIRED.items()}

#: Where instructions live -- prose a reader may copy from, and scripts they may run.
LIVE_GLOBS = ("*.md", "docs/**/*.md", "examples/**/*.md", "notebooks/**/*.md",
              "examples/**/*.py", "notebooks/**/*.py", "scripts/*.py")

#: Records of what was typed at the time, not instructions. Rewriting one would falsify the
#: record it exists to preserve -- the same exclusion, for the same reason, as the CLI test's.
HISTORICAL: tuple[str, ...] = ("tech-debt.md", "scripts/internal/one-offs/")
DATED = re.compile(r"/\d{4}-\d{2}-\d{2}-")


def _live_files() -> list[Path]:
    found: set[Path] = set()
    for glob in LIVE_GLOBS:
        found.update(p for p in ROOT.glob(glob) if p.is_file())
    live = []
    for path in found:
        relative = path.relative_to(ROOT).as_posix()
        if any(relative.startswith(h) for h in HISTORICAL) or DATED.search("/" + relative):
            continue
        live.append(path)
    return sorted(live)


def _offences(path: Path) -> list[str]:
    """Every retired spelling this file would have a reader write."""
    found = []
    for number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
        for pattern, instead in RETIRED_PATTERNS.items():
            if pattern.search(line):
                found.append(
                    f"{path.relative_to(ROOT)}:{number} teaches `{pattern.pattern}` -- "
                    f"write {instead}")
    return found


@pytest.mark.parametrize("path", _live_files(), ids=lambda p: p.relative_to(ROOT).as_posix())
def test_no_live_file_teaches_a_retired_python_name(path: Path):
    """A document that teaches the old vocabulary is what puts it back in someone's code."""
    offences = _offences(path)
    assert not offences, "\n".join(offences)


#: Files the scan must reach, or every case above passes vacuously.
MUST_COVER = ("README.md", "examples/02-your-own-system/run.py", "docs/adding-adapters.md")


def test_the_scan_reaches_the_files_that_teach_the_python_surface():
    """Guards the guard: an over-eager exclusion would empty the corpus silently."""
    scanned = {p.relative_to(ROOT).as_posix() for p in _live_files()}
    for must_cover in MUST_COVER:
        assert must_cover in scanned, f"{must_cover} fell out of the live corpus"


def test_the_package_surface_is_the_seven():
    """What a person meets on `import memrank`, pinned by name."""
    assert tuple(memrank.__all__) == SURFACE


def _positional(function) -> tuple[str, ...]:
    return tuple(p.name for p in inspect.signature(function).parameters.values()
                 if p.kind is inspect.Parameter.POSITIONAL_OR_KEYWORD)


def test_run_takes_the_system_and_the_evaluation_by_position():
    """`run(system, evaluation)`: the two arguments a first number needs, in that order."""
    assert _positional(memrank.run) == POSITIONAL
    assert memrank.run.__module__ == "memrank.instrument.run"


def test_the_previous_run_keeps_its_own_nouns_where_the_cli_and_the_cloud_call_it():
    assert _positional(cell_run) == CELL_POSITIONAL


def test_every_deprecated_parameter_is_keyword_only_and_declared():
    """A deprecated spelling may be accepted, never offered a position.

    Both halves matter. Keyword-only is what stops `run(x, y)` meaning the old thing, and the
    declaration is what stops a third spelling arriving without an edit to the table step 22
    removes.
    """
    parameters = inspect.signature(cell_run).parameters
    for old_name, current in DEPRECATED_PARAMETERS.items():
        assert old_name in parameters, f"{old_name}= must keep working until step 22"
        assert parameters[old_name].kind is inspect.Parameter.KEYWORD_ONLY
        assert current in parameters, f"{old_name} is deprecated in favour of {current}"
    undeclared = {name for name in parameters
                  if name in RETIRED and name not in DEPRECATED_PARAMETERS}
    assert undeclared == set(), f"retired parameter names not declared deprecated: {undeclared}"


def test_the_result_answers_to_the_nouns():
    """A reader asks a result which engine and which evaluation, in those words."""
    result = EvalResult(adapter="word-overlap", benchmark="demo", composite=1.0, target="ref")
    assert (result.engine, result.evaluation, result.engine_ref) == ("word-overlap", "demo", "ref")


def test_the_deprecated_exports_are_the_same_objects():
    """Not near-copies: the same class, so a subclass written against either name is one type.

    A parallel hierarchy would pass a name check and fail every `isinstance` in the registry.
    """
    assert memrank.MemoryEngine is memrank.MemoryAdapter
    assert memrank.Memory is memrank.MemoryAdapter, (
        "the memory kind is the memory contract, not a second class beside it")
    assert memrank.Benchmark is memrank.core.Evaluation
    assert memrank.Result is not memrank.EvalResult, (
        "the new Result is the read form of the new run; the stored artifact is EvalResult")

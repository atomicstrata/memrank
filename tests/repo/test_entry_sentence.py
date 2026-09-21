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
"""The three first surfaces say the same thing about what memrank is.

There are three surfaces a person meets first and no two of them met the same way: `README.md`
called memrank *"an instrument for measuring AI memory engines"*, the package docstring said the
same in different words, and `memrank --help` called it a *"benchmark suite"* -- a different
word for the thing, on the surface with the least room to explain itself. Two recorded feedback
sessions in September 2026 failed at exactly this point: a person who had read the entry page
could not say what memrank measures.

Three surfaces drift because nothing compares them. This compares them: each must carry the
direction brief's sentence about what is measured, each must use the one word for what memrank
is, and each must say which pieces are the person's. The word is asserted in both directions --
present, and the retired one absent -- because a surface that gains the sentence and keeps
calling memrank a benchmark suite has half-landed and reads as landed.

`pyproject.toml` is the fourth surface, and it is what PyPI renders, so it carries the sentence
and the word too. It is one line with no room for the ownership half, which is why that half is
asserted of the three prose surfaces only.
"""
from __future__ import annotations

import re
from pathlib import Path

import pytest

# `tomllib` is stdlib only from 3.11, and `pyproject.toml` declares `requires-python = ">=3.10"`.
try:
    import tomllib
except ModuleNotFoundError:  # pragma: no cover -- 3.10 only
    import tomli as tomllib

from memrank.runner import _APP_HELP

ROOT = Path(__file__).resolve().parents[2]

#: The sentence, from the direction brief's section 1 -- *"memrank measures how well a memory helps
#: answer questions about what it was told earlier"*. Only the predicate is pinned: the subject
#: is "Memrank" on one surface and "it" on the others, and that is prose, not vocabulary.
MEASURES = "measures how well a memory helps answer questions about what it was told earlier"

#: Which half of the work is the person's. T1's recognition test is both halves: a reader must
#: restate what is measured AND name which pieces are theirs.
OWNERSHIP = "you bring the engine"

#: One word for what memrank is, and the word it is not. `docs-internal/VISION.md` and the
#: roadmap treat the distinction as load-bearing: an instrument is run by its user against their
#: own system; a benchmark suite is a fixed set of tests with a scoreboard.
WORD = "instrument"
RETIRED_WORD = "benchmark suite"


def _normalised(text: str) -> str:
    """Lowercased, with markdown quoting and line wrapping flattened.

    The sentence is wrapped across lines on every surface that has a line length, so a literal
    substring search would only ever match by accident.
    """
    return re.sub(r"\s+", " ", re.sub(r"^[>#\s]+", "", text, flags=re.MULTILINE)).lower()


def _readme_entry() -> str:
    """The README down to its first heading after the title -- what a reader meets first."""
    body = (ROOT / "README.md").read_text(encoding="utf-8").split("\n## ")[0]
    return _normalised(body)


def _package_docstring() -> str:
    """Read as text rather than imported, so this states what the file says."""
    import memrank

    assert memrank.__doc__ is not None, "the package docstring is the entry surface"
    return _normalised(memrank.__doc__)


SURFACES = {
    "README.md": _readme_entry,
    "memrank/__init__.py": _package_docstring,
    "memrank --help": lambda: _normalised(_APP_HELP),
}


@pytest.mark.parametrize("surface", sorted(SURFACES))
def test_every_entry_surface_says_what_memrank_measures(surface: str):
    """A reader of any one of the three restates the same sentence."""
    assert MEASURES in SURFACES[surface](), f"{surface} does not carry the entry sentence"


@pytest.mark.parametrize("surface", sorted(SURFACES))
def test_every_entry_surface_names_which_pieces_are_the_persons(surface: str):
    """The other half of T1: what the person supplies, said where they first look."""
    assert OWNERSHIP in SURFACES[surface](), f"{surface} does not say which pieces are the reader's"


@pytest.mark.parametrize("surface", sorted(SURFACES))
def test_every_entry_surface_uses_one_word_for_what_memrank_is(surface: str):
    """Present and absent, so a half-done rewording fails rather than passing quietly."""
    text = SURFACES[surface]()
    assert WORD in text, f"{surface} does not call memrank an {WORD}"
    assert RETIRED_WORD not in text, f"{surface} still calls memrank a {RETIRED_WORD}"


def test_the_distribution_description_agrees_with_them():
    """What PyPI renders is the surface a stranger meets before the repository."""
    with (ROOT / "pyproject.toml").open("rb") as handle:
        description = _normalised(tomllib.load(handle)["project"]["description"])
    assert MEASURES in description
    assert WORD in description
    assert RETIRED_WORD not in description

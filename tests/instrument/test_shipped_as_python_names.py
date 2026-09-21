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
"""`memrank.systems`, `memrank.evaluations`, `memrank.catalog()`: the catalog without a string.

`memrank.system("word-overlap")` presupposes the string. Nothing in an editor follows a string,
so a reader who has one cannot reach the class, and a reader who has none cannot find out what
exists. These hold the three things that fixes: the classes are the registered classes and not
copies of them, every shipped evaluation is a typed function returning the same `Evaluation`,
and one call prints the whole catalog.

The downloading three are checked WITHOUT downloading: the function exists, it is typed, and a
tier it does not have is refused before anything is fetched. A test that pulled LoCoMo to prove
`locomo()` is a function would be a test nobody runs offline.
"""
from __future__ import annotations

import inspect
import typing

import pytest

from memrank import evaluations, systems
from memrank.adapters import REGISTRY as SYSTEM_REGISTRY
from memrank.benchmarks import REGISTRY as EVALUATION_REGISTRY
from memrank.instrument.catalog import catalog, evaluation, system
from memrank.instrument.evaluation import Evaluation

#: The evaluations whose `load()` may reach the network. Built here, never called.
DOWNLOADS = ("locomo", "longmemeval", "beam")
#: The evaluations that are wholly in-tree, so a test may actually build one.
OFFLINE = ("demo", "relation_graph")


@pytest.mark.parametrize("entry", systems.SHIPPED, ids=lambda e: e.python_name)
def test_every_shipped_system_is_the_registered_class_object(entry):
    """The same class, not a near-copy: a parallel hierarchy fails every registry isinstance."""
    named = getattr(systems, entry.python_name)

    assert named is SYSTEM_REGISTRY[entry.name]
    assert named.name == entry.name


def test_the_systems_module_covers_the_registry_exactly():
    """A registered system with no Python name is one a reader can only reach by guessing."""
    assert {e.name for e in systems.SHIPPED} == set(SYSTEM_REGISTRY)
    assert len(systems.SHIPPED) == len(SYSTEM_REGISTRY)


@pytest.mark.parametrize("name", OFFLINE)
def test_an_offline_evaluation_function_builds_the_evaluation_it_names(name: str):
    """Built for real, because these two need nothing: the object is the seven's `Evaluation`."""
    built = getattr(evaluations, name)()

    assert isinstance(built, Evaluation)
    assert built.name == name
    assert built.tasks


@pytest.mark.parametrize("name", DOWNLOADS)
def test_a_downloading_evaluation_function_exists_and_is_typed(name: str):
    """Signature only -- calling one fetches a dataset, and that is not this test's business."""
    function = getattr(evaluations, name)
    hints = typing.get_type_hints(function)

    assert callable(function)
    assert hints["return"] is Evaluation
    assert all(parameter in hints for parameter in inspect.signature(function).parameters)


def test_an_unknown_beam_tier_is_refused_before_anything_is_fetched():
    """The benchmark's own error, raised by its constructor, so no download is even begun."""
    with pytest.raises(ValueError) as refused:
        evaluations.beam(tier="9000k")

    assert "9000k" in str(refused.value)


def test_the_evaluations_module_covers_the_registry_exactly():
    """A registered evaluation with no function is one a reader can only reach by guessing."""
    assert {e.name for e in evaluations.SHIPPED} == set(EVALUATION_REGISTRY)
    assert all(callable(getattr(evaluations, e.python_name)) for e in evaluations.SHIPPED)


def test_the_catalog_lists_every_registered_name_once(capsys):
    """One call, nothing presupposed: every name that exists, printed and returned."""
    listed = catalog()
    printed = capsys.readouterr().out

    assert len(listed.systems) == len(SYSTEM_REGISTRY)
    assert len(listed.evaluations) == len(EVALUATION_REGISTRY)
    assert {e.name for e in listed.systems} == set(SYSTEM_REGISTRY)
    assert {e.name for e in listed.evaluations} == set(EVALUATION_REGISTRY)
    for name in (*SYSTEM_REGISTRY, *EVALUATION_REGISTRY):
        assert printed.count(f"{name!r}") == 1, f"{name} is printed {printed.count(name)} times"


def test_the_refusals_point_at_the_python_names():
    """A reader who guessed a string is the reader who did not know the catalog existed."""
    with pytest.raises(ValueError) as system_refused:
        system("word-overlaps")
    with pytest.raises(Exception) as evaluation_refused:
        evaluation("demonstration")

    assert "memrank.systems" in str(system_refused.value)
    assert "memrank.evaluations" in str(evaluation_refused.value)


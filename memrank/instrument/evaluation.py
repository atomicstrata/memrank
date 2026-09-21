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
"""Evaluation -- a named, versioned bundle: tasks, the measures it ships with, and the rule
for when the system's state is cleared.

The thing a person brings, reuses or publishes. memrank's evaluations and private ones are the
same kind of thing, which is why `memrank.evaluation("demo")` returns exactly what a person
writes by hand.

Scoring is not here. An evaluation bundles measures; the measures decide.
"""

from __future__ import annotations

from enum import Enum

from pydantic import BaseModel, ConfigDict, Field

from memrank.instrument.measure import Measure
from memrank.instrument.task import Task

#: What an evaluation states instead of a version when its material cannot be frozen. The same
#: distinction `memrank.quality.UNFREEZABLE` draws for a benchmark's dataset: a gap and an
#: honest statement are different values.
UNFREEZABLE = "cannot-be-frozen"


class Clearing(str, Enum):
    """When the system's state is cleared. Closed, so two runs can be compared on it."""

    PER_TASK = "per-task"
    PER_GROUP = "per-group"
    AT_END = "at-end"


class Evaluation(BaseModel):
    """Tasks, measures, and a clearing rule, under a name and a version."""

    model_config = ConfigDict(frozen=True, arbitrary_types_allowed=True)

    name: str
    #: The version of what this evaluation asks, or :data:`UNFREEZABLE` when it cannot say.
    version: str
    tasks: tuple[Task, ...] = ()
    #: The measures it ships with. A person may run others over the traces afterwards.
    measures: tuple[Measure, ...] = ()
    clearing: Clearing = Clearing.PER_GROUP
    #: Kept out of the way of the seven: what this evaluation wants to record about itself.
    metadata: dict[str, object] = Field(default_factory=dict)

    def group_of(self, task: Task) -> str:
        """The unit of state a task belongs to. A task with no group is its own."""
        return task.group or task.id

    def groups(self) -> list[str]:
        """The groups, in the order their first task appears."""
        seen: list[str] = []
        for task in self.tasks:
            name = self.group_of(task)
            if name not in seen:
                seen.append(name)
        return seen

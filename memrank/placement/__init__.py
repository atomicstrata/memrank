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
"""Where a target materialises -- this laptop, or a cloud task.

Placement is the third noun: a target says *what* is under test, an experiment says what is being
measured, and a placement says *where* it runs. Keeping them separate is what turns "which bash
script did I type" into a flag.

The rule every implementation obeys: **the harness and the engine always colocate.** Never run the
harness here against an engine there, or ingest/retrieve p50/p95/p99 measure the network rather than
the engine -- and ``SPEC.md`` makes latency one of four required axes.
"""

from memrank.placement.base import Endpoint, Placement, PlacementError

__all__ = ["Endpoint", "Placement", "PlacementError"]

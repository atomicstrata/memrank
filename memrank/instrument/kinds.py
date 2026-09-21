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
"""`Memory`, the memory kind, as the same class object as `memrank.core.MemoryAdapter`.

One memory contract, two names while the rename runs: `isinstance(x, MemoryAdapter)` and every
registered adapter keep holding, and the CLI keeps its own names. This module exists rather
than the alias living in `system.py` because `memrank.core` imports `system.py`, and an import
back the other way would close the loop.
"""

from __future__ import annotations

from memrank.core import MemoryAdapter

#: You tell it things, and later you ask it for what is relevant; it clears on request.
Memory = MemoryAdapter

__all__ = ["Memory"]

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
"""Adapter registry.

Adapter classes register themselves here by short name. The CLI looks up by
this name; the conformance suite iterates over the registry to assert every
registered adapter satisfies the contract.
"""

from __future__ import annotations

from memrank.adapters.atomicmemory import AtomicMemoryAdapter
from memrank.adapters.controls import (
    FixedContextAdapter,
    FullContextAdapter,
    NoContextAdapter,
)
from memrank.adapters.hindsight import HindsightAdapter
from memrank.adapters.mem0 import Mem0Adapter
from memrank.adapters.native import NativeAdapter
from memrank.adapters.supermemory import SupermemoryAdapter
from memrank.adapters.word_overlap import WordOverlapAdapter
from memrank.core import MemoryAdapter

REGISTRY: dict[str, type[MemoryAdapter]] = {
    "atomicmemory": AtomicMemoryAdapter,
    "word-overlap": WordOverlapAdapter,
    "mem0": Mem0Adapter,
    "hindsight": HindsightAdapter,
    "supermemory": SupermemoryAdapter,
    # Not an engine: the client for memrank's own translator contract
    # (docs/adapter-contract.md), which is how an engine memrank has never seen gets evaluated
    # without a fork. Every other entry here names one vendor; this one names none.
    "native": NativeAdapter,
    # The mandatory baseline arms (PRD_Memrank_v2.md:86) -- not memory systems.
    "no-context": NoContextAdapter,
    "fixed-context": FixedContextAdapter,
    "full-context": FullContextAdapter,
}


def get_adapter(name: str, **kwargs) -> MemoryAdapter:
    """Construct the adapter registered under ``name``.

    Raises ``ValueError`` with a helpful message when the name is unknown.
    """
    if name not in REGISTRY:
        available = ", ".join(sorted(REGISTRY))
        raise ValueError(f"Unknown adapter: {name!r}. Available: {available}")
    return REGISTRY[name](**kwargs)


def list_adapters() -> list[str]:
    """Return the registered adapter names in deterministic order."""
    return sorted(REGISTRY.keys())


__all__ = [
    "AtomicMemoryAdapter",
    "WordOverlapAdapter",
    "HindsightAdapter",
    "Mem0Adapter",
    "NativeAdapter",
    "SupermemoryAdapter",
    "REGISTRY",
    "get_adapter",
    "list_adapters",
]

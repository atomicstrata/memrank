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
"""``memrank.run`` -- evaluate a memory engine from a Python script, and nothing else.

The supported library entry point: resolve the target and eval the way the CLI does,
run the cell, return a typed :class:`EvalResult`. No run directory, no ``status.json``,
no sync, no cloud -- the only disk touched is the dataset/tokenizer/judge caches, and
the only network egress is the engine under test (plus Anthropic when judged).
"""
from __future__ import annotations

import uuid
from dataclasses import replace
from pathlib import Path

from memrank.core import Benchmark, MemoryAdapter
from memrank.evaluation.cell import _close_adapter, run_cell
from memrank.evaluation.constants import DEFAULT_JUDGE_WORKERS
from memrank.evaluation.observer import NULL_OBSERVER, EvalObserver
from memrank.evaluation.result import EvalResult
from memrank.judging.judge import JudgeConfig


def run(
    target: str | MemoryAdapter,
    eval: str | Benchmark,  # noqa: A002 - the CLI's own noun (`memrank submit TARGET EVAL`)
    *,
    k: int = 10,
    repeats: int = 3,
    seed: int = 42,
    token_budget: int = 5000,
    model: str = "gpt-4o-mini",
    judge: bool | JudgeConfig | None = None,
    units: list | None = None,
    workers: int = 1,
    judge_workers: int = DEFAULT_JUDGE_WORKERS,
    fail_fast: bool = False,
    observer: EvalObserver | None = None,
    checkpoint_path: Path | None = None,
) -> EvalResult:
    """Run one evaluation cell and return its result. Writes nothing, prints nothing.

    Args:
        target: A target ref from the catalog (``"mem0"``, ``"hindsight:matched"``,
            ``"word-overlap"``) or a ready :class:`MemoryAdapter` instance. A ref is
            resolved exactly as ``memrank submit`` resolves it; a container-backed
            target's engine must already be reachable -- this function provisions
            nothing.
        eval: An eval ref (``"demo"``, ``"locomo:smoke"``, ``"beam:100k-smoke"``) or a
            :class:`Benchmark` instance. ``load()`` may download the dataset into the
            cache on first use.
        judge: ``None`` asks the benchmark (`judge_required`) -- the evals whose
            protocol IS the judge get one by default; ``True``/``False`` force it; a
            :class:`JudgeConfig` is used as given. Judging calls Anthropic and keeps a
            local verdict cache (``JudgeConfig(cache=False)`` opts out).
        fail_fast: Stop at the first unit that raises. The default attempts every unit and
            records what happened to each on ``result.unit_outcomes``, with the counts under
            ``units_total``/``units_failed``.
        observer: Where progress narration goes. ``None`` is silent -- pass an
            :class:`EvalObserver` subclass to hear about units, items and warnings.
        checkpoint_path: ``None`` writes no checkpoint. Give a path to make a judged
            run resumable (``memrank ops rejudge``) at the cost of one file.

    Defaults mirror ``memrank submit``'s (k=10, repeats=3, seed=42, token_budget=5000,
    priced at gpt-4o-mini), so a script and a sweep of the same cell agree.

    Note: ``seed`` seeds the process-global ``random`` module, and the tokenizer
    downloads (~4 MB, cached) on first cost accounting -- both inherited from the
    measurement loop and documented rather than hidden.
    """
    if isinstance(eval, Benchmark):
        benchmark = eval
    else:
        from memrank.benchmarks import from_ref

        benchmark = from_ref(eval)

    if judge is None:
        # The single definition of "does this eval need judging" -- an unjudged run of a
        # judge-protocol benchmark measures latency and cost and nothing else.
        judge_cfg = JudgeConfig() if not benchmark.composite_rankable else None
    elif judge is True:
        judge_cfg = JudgeConfig()
    elif judge is False:
        judge_cfg = None
    else:
        judge_cfg = judge

    ref: str | None = None
    make_adapter = None
    owns_adapter = False
    if isinstance(target, MemoryAdapter):
        adapter = target
    else:
        from memrank.targets import resolve_target
        from memrank.targets.factory import build_adapter

        ref = target

        def make_adapter() -> MemoryAdapter:
            return build_adapter(resolve_target(ref))

        adapter = make_adapter()
        owns_adapter = True

    try:
        result = run_cell(
            adapter, benchmark, k=k, repeats=repeats,
            run_id_prefix=f"{adapter.name}-{uuid.uuid4().hex[:8]}",
            model=model, token_budget=token_budget, seed=seed, judge=judge_cfg,
            units=units, workers=workers, judge_workers=judge_workers, fail_fast=fail_fast,
            checkpoint_path=checkpoint_path, make_adapter=make_adapter,
            observer=observer if observer is not None else NULL_OBSERVER,
            )
    finally:
        if owns_adapter:
            _close_adapter(adapter)
    if ref is not None:
        result = replace(result, target=ref)
    return result

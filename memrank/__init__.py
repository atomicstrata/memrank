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
"""Memrank -- an open, vendor-neutral instrument for measuring AI memory engines.

    memrank.run("word-overlap", "demo")   # a shipped engine on a shipped evaluation
    memrank.run(MyEngine(), MyEval())     # your own, passed as instances -- nothing registered

``run(engine, evaluation)`` is the entry point. Either argument takes a catalog name or an object
you built: an engine is any ``MemoryAdapter`` (six methods), an evaluation any ``Benchmark``
(three), and the two forms are interchangeable. Registration is what makes a piece shareable by
name -- from the ``memrank`` command line and from other people's runs -- never a precondition for
measuring it. The call returns an ``EvalResult`` and writes nothing.
"""

from memrank.core import (
    AdapterResponse,
    Benchmark,
    BenchmarkUnit,
    Document,
    EvalInfo,
    MemoryAdapter,
)


def _installed_version() -> str:
    """The version of the installed distribution, so `memrank version` cannot disagree with it.

    A hardcoded constant beside pyproject's is two sources of truth, and the one that goes stale
    is the one users quote in bug reports -- this printed 0.1.0 from a 0.2.0 install. Falls back
    to the literal only when the package is not installed at all (a bare source checkout on
    sys.path), which is the one case metadata genuinely cannot answer.
    """
    from importlib.metadata import PackageNotFoundError, version

    try:
        return version("memrank")
    except PackageNotFoundError:
        return "0.0.0+unknown"


__version__ = _installed_version()

#: The eval-library surface, resolved lazily (PEP 562) so `import memrank` stays as
#: light as the five core contracts above -- `tests/repo/test_import_weight.py` holds the
#: package to a real import-graph budget, and the eval loop only loads when asked for.
_LAZY = {
    "run": ("memrank.evaluation.api", "run"),
    #: `memrank.benchmark("beam:100k-smoke")` -- the one-string benchmark constructor,
    #: same ref grammar as `run`'s eval parameter.
    "benchmark": ("memrank.benchmarks", "from_ref"),
    "EvalResult": ("memrank.evaluation.result", "EvalResult"),
    "EvalObserver": ("memrank.evaluation.observer", "EvalObserver"),
    "EvalPlan": ("memrank.evaluation.observer", "EvalPlan"),
    "JudgeConfig": ("memrank.judging.judge", "JudgeConfig"),
}


def __getattr__(name: str):
    try:
        module_name, attr = _LAZY[name]
    except KeyError:
        raise AttributeError(f"module 'memrank' has no attribute {name!r}") from None
    from importlib import import_module

    return getattr(import_module(module_name), attr)


def __dir__() -> list[str]:
    return sorted([*globals(), *_LAZY])


__all__ = [
    "AdapterResponse",
    "Benchmark",
    "BenchmarkUnit",
    "Document",
    "EvalInfo",
    "EvalObserver",
    "EvalPlan",
    "EvalResult",
    "JudgeConfig",
    "MemoryAdapter",
    "__version__",
    "benchmark",
    "run",
]

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
"""Registering an adapter memrank does not ship.

An adapter is not only a class. Driving one needs facts memrank keeps in tables keyed by adapter
name: which env vars carry its components, where the harness finds it, how long it may take to
become ready, what credentials launching it implies, and what its receipt should say about the
artifact that ran. A registration that supplies the class and forgets a table produces a failure
far from its cause -- a ``KeyError`` at planning time, or worse, an empty ``engine_provenance``
facet that nothing checks.

So the unit here is the class **and** its rows together, in one frozen object with no defaults for
the five that are load-bearing. Omitting one is a ``TypeError`` at the call, not a mystery later.

WHAT THIS IS NOT. memrank does not load, sandbox, or lifecycle-manage foreign code. This is an
addressing mechanism: it lets a manifest's ``interface.adapter`` resolve to a class that lives
somewhere else, which is what makes an engine evaluable from outside the tree without a fork.
The engine itself is still reached exactly as any other is.

WHAT IT DOES NOT CONFER. A module reachable on ``sys.path`` has no version and no resolvable
origin, so registering through it earns no reproducibility claim of its own: the run's evidence
class still derives from how its *artifact* was bound, which for a source-bound target is
``development_observation``. Provenance here is asserted by the registering module, and memrank
cannot verify it -- see the direction brief on addressability
(``localdocs/directions/2026-08-28-customizability-and-reproducibility.md``).
"""

from __future__ import annotations

import importlib
from dataclasses import dataclass, field
from typing import Any

from memrank.core import MemoryAdapter
from memrank.errors import MemrankError
from memrank.secrets.requirements import EngineRequirements
from memrank.targets.engine_env import Readiness

#: Modules already imported by :func:`load_plugins`, so a second call is a no-op rather than a
#: re-import that would re-register and raise on the duplicate check below.
_LOADED: set[str] = set()


class PluginError(MemrankError):
    """A plugin module could not be loaded, or registered something memrank cannot accept."""


@dataclass(frozen=True)
class AdapterRegistration:
    """One out-of-tree adapter, with every table row driving it needs.

    The first seven fields have no defaults on purpose: each is read on a path where absence is
    either a loud failure far from the cause or, for ``provenance``, a silent one.

    Args:
        adapter: The :class:`~memrank.core.MemoryAdapter` subclass. Its ``name`` is the key every
            table is written under, and the string a manifest's ``interface.adapter`` names.
        engine_env: ``{(component role, field) -> env var the ENGINE reads}``. An empty mapping is
            a positive statement -- "this engine exposes no component knobs" -- and differs from
            absence, which memrank refuses.
        base_url_env: The env var THE HARNESS reads to find the engine, or ``None`` for an
            in-process adapter that is never placed.
        readiness: How to ask the engine whether it is ready, or ``None`` when nothing launches it.
        engine_command: The command that starts the engine, or ``None`` to keep the image's own
            CMD. Source-bound targets start from their manifest's ``launch.command`` and ignore
            this; it is still required, because defaulting it silently hands an engine whichever
            command was written first.
        requirements: What launching the engine implies in credentials.
        provenance: Static, code-reviewed provenance facts. Without this the receipt's
            ``engine_provenance`` facet is empty and the run's origin reads as ``unknown``.
        engine_settings: Engine settings true wherever it runs.
        secret_env: ``{canonical credential name -> the var THE ENGINE reads}``, for engines that
            rename one.
        paired_token: ``(harness var, engine var)`` when harness and engine must agree on a bearer
            token they each call something different.
        provenance_fields: Suffixes appended to ``{ADAPTER}_`` that the adapter reads for dynamic
            pins.
        providers: Extra ``provider -> API-key env var`` entries this engine's component
            vocabulary needs. Empty string means keyless.
    """

    adapter: type[MemoryAdapter]
    engine_env: dict[tuple[str, str], str]
    base_url_env: str | None
    readiness: Readiness | None
    engine_command: str | None
    requirements: EngineRequirements
    provenance: dict[str, Any]
    engine_settings: dict[str, str] = field(default_factory=dict)
    secret_env: dict[str, str] = field(default_factory=dict)
    paired_token: tuple[str, str] | None = None
    provenance_fields: tuple[str, ...] = ()
    providers: dict[str, str] = field(default_factory=dict)

    @classmethod
    def in_process(cls, adapter: type[MemoryAdapter], *, requirements: EngineRequirements,
                   provenance: dict[str, Any],
                   providers: dict[str, str] | None = None) -> AdapterRegistration:
        """A registration for an engine that runs inside memrank, with no process to drive.

        Four of the required fields describe how to reach and start a separate engine, and an
        in-process adapter has none: nothing is launched, nothing listens, no readiness is waited
        on, and no component reaches an engine through the environment. This fills them with the
        values that say so.

        Not a shortcut around the "absence is not a default" rule -- it is what stops that rule
        being applied where it does not belong. memrank's own in-process arms are absent from all
        six engine tables (`test_adapter_table_coverage` derives its list from adapters whose
        ``transport`` is not ``in-process``), so requiring a plugin to state four inapplicable
        values would hold it to a stricter standard than the engines memrank ships.

        Raises:
            PluginError: When the adapter's ``transport`` is not ``in-process``. Reaching for this
                on an engine memrank must actually drive would skip exactly the rows whose absence
                fails far from its cause -- or, for ``provenance``, silently.
        """
        transport = getattr(adapter, "transport", None)
        if transport != "in-process":
            raise PluginError(
                f"{adapter.__name__}.transport is {transport!r}, not 'in-process'; an engine "
                f"memrank has to reach or start needs the full registration, because the rows this "
                f"omits are the ones that drive it.")
        return cls(adapter=adapter, engine_env={}, base_url_env=None, readiness=None,
                   engine_command=None, requirements=requirements, provenance=provenance,
                   providers=providers or {})


def register_adapter(registration: AdapterRegistration) -> str:
    """Write ``registration`` into every table keyed by adapter name, and return that name.

    Raises:
        PluginError: When the adapter's ``name`` is already registered. Shadowing a shipped engine
            would make a target ref mean something different depending on a setting, and the
            receipt would carry the shadowed engine's provenance under the shipped one's name.
    """
    from memrank.adapters import REGISTRY
    from memrank.provenance.engine import PROVENANCE
    from memrank.secrets.requirements import PROVIDER_KEY_ENV, REQUIREMENTS
    from memrank.targets import engine_env as tables

    name = registration.adapter.name
    if name in REGISTRY:
        raise PluginError(
            f"adapter {name!r} is already registered; a plugin may not shadow it. Rename the "
            f"plugin's adapter, or remove the shipped one.")
    _refuse_provider_conflicts(registration.providers, PROVIDER_KEY_ENV)

    REGISTRY[name] = registration.adapter
    tables.ENGINE_ENV[name] = dict(registration.engine_env)
    tables.ENGINE_SETTINGS[name] = dict(registration.engine_settings)
    tables.ENGINE_COMMAND[name] = registration.engine_command
    tables.PROVENANCE_FIELDS[name] = tuple(registration.provenance_fields)
    REQUIREMENTS[name] = registration.requirements
    PROVENANCE[name] = dict(registration.provenance)
    PROVIDER_KEY_ENV.update(registration.providers)
    if registration.base_url_env is not None:
        tables.BASE_URL_ENV[name] = registration.base_url_env
    if registration.readiness is not None:
        tables.READINESS[name] = registration.readiness
    if registration.paired_token is not None:
        tables.PAIRED_TOKENS[name] = registration.paired_token
    if registration.secret_env:
        tables.SECRET_ENV[name] = dict(registration.secret_env)
    return name


def _refuse_provider_conflicts(providers: dict[str, str], known: dict[str, str]) -> None:
    """Refuse a provider name already meaning something else.

    Provider names are a shared vocabulary across engines, unlike the adapter-keyed tables. A
    plugin quietly repointing ``anthropic`` at another variable would change which credential
    every other engine preflights for.
    """
    clashes = sorted(p for p, env in providers.items() if p in known and known[p] != env)
    if clashes:
        raise PluginError(
            f"provider(s) {', '.join(clashes)} already map to a different key env var; a plugin "
            f"may not repoint a provider other engines share.")


def load_plugins() -> list[str]:
    """Import every module named by the ``adapters.plugins`` setting, and return their names.

    Each module registers what it provides at import time by calling :func:`register_adapter`.
    Idempotent: a module already imported by this process is skipped, so the duplicate check in
    :func:`register_adapter` stays meaningful.

    Raises:
        PluginError: When a named module cannot be imported. A plugin that is configured but
            missing is a target that would resolve to the wrong thing or not at all; skipping it
            would degrade the run silently.
    """
    from memrank import settings

    configured = settings.get("adapters.plugins")
    if not configured:
        return []
    loaded = []
    for module in [part.strip() for part in configured.split(",") if part.strip()]:
        if module in _LOADED:
            continue
        try:
            importlib.import_module(module)
        except Exception as exc:
            raise PluginError(
                f"could not import adapter plugin {module!r}: {exc}. It is named by the "
                f"`adapters.plugins` setting. Put the module on the interpreter's import path "
                f"(PYTHONPATH, or install it), or clear the setting with "
                f"`memrank config set adapters.plugins \"\"`.") from exc
        _LOADED.add(module)
        loaded.append(module)
    return loaded


__all__ = ["AdapterRegistration", "PluginError", "load_plugins", "register_adapter"]

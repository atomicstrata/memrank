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
"""An adapter memrank does not ship can be driven exactly as one it does.

The point of the mechanism is that it leaves nothing behind: a registered plugin must satisfy the
same table coverage a builtin does, or the failure surfaces far from its cause -- a KeyError at
planning time, or an empty provenance facet nothing checks.
"""
from __future__ import annotations

import pytest

from memrank.adapters import REGISTRY
from memrank.core import REQUIRED_LATENCY_KEYS, REQUIRED_TOKEN_KEYS, MemoryAdapter
from memrank.plugins import AdapterRegistration, PluginError, register_adapter
from memrank.provenance.engine import PROVENANCE, build_provenance
from memrank.secrets.requirements import PROVIDER_KEY_ENV, REQUIREMENTS, EngineRequirements
from memrank.targets import engine_env as tables
from memrank.targets.engine_env import Readiness

_TABLES = (tables.ENGINE_ENV, tables.ENGINE_SETTINGS, tables.ENGINE_COMMAND,
           tables.PROVENANCE_FIELDS, tables.BASE_URL_ENV, tables.READINESS,
           tables.PAIRED_TOKENS, tables.SECRET_ENV, PROVENANCE, REQUIREMENTS, REGISTRY)


class _Stub(MemoryAdapter):
    """A registrable adapter that measures nothing -- the mechanism is what is under test."""

    name = "stub"
    version = "0.1.0"
    engine_version = "0.0.0"

    def prepare(self, isolation_unit: str) -> None: ...
    def ingest(self, documents) -> None: ...
    def retrieve(self, query, k, user_id, query_timestamp=None): return [], {}
    def cleanup(self) -> None: ...
    def latency_metrics(self): return dict.fromkeys(REQUIRED_LATENCY_KEYS, 0.0)
    def token_metrics(self): return dict.fromkeys(REQUIRED_TOKEN_KEYS, None)


def _registration(name: str, **over) -> AdapterRegistration:
    """A complete registration for a fictional engine, overridable field by field."""
    adapter = type(f"Adapter{name}", (_Stub,), {"name": name})
    fields = {
        "adapter": adapter,
        "engine_env": {("llm", "provider"): "STUB_LLM"},
        "base_url_env": "STUB_API_URL",
        "readiness": Readiness("curl {port}{path}", "/health", 30),
        "engine_command": None,
        "requirements": EngineRequirements(name, providers={"llm": "regex-stub"}),
        "provenance": {"prefix": "STUB_", "type": "container", "image_name": "stub",
                       "manufacturer": "someone", "supplier": "someone",
                       "source_repo": "someone/stub", "ancestors": [], "patches": [],
                       "properties": {}},
        "providers": {"regex-stub": ""},
    }
    return AdapterRegistration(**{**fields, **over})


@pytest.fixture
def clean_tables():
    """Undo every table write, so a registration cannot leak into another test."""
    before = [dict(table) for table in _TABLES]
    providers_before = dict(PROVIDER_KEY_ENV)
    yield
    for table, snapshot in zip(_TABLES, before, strict=True):
        table.clear()
        table.update(snapshot)
    PROVIDER_KEY_ENV.clear()
    PROVIDER_KEY_ENV.update(providers_before)


def test_a_registered_adapter_satisfies_every_table_a_builtin_does(clean_tables):
    """The coverage contract holds for a plugin, which is the whole point of registering rows."""
    name = register_adapter(_registration("stubengine"))

    assert REGISTRY[name].name == name
    for table in (tables.ENGINE_ENV, tables.ENGINE_SETTINGS, tables.ENGINE_COMMAND,
                  tables.PROVENANCE_FIELDS, tables.BASE_URL_ENV, tables.READINESS,
                  PROVENANCE, REQUIREMENTS):
        assert name in table, f"{name} missing from a table a builtin would populate"


def test_provenance_reaches_the_receipt_facet(clean_tables):
    """Without a PROVENANCE row build_provenance returns {} -- silently, which is the hazard."""
    register_adapter(_registration("stubengine"))

    facet = build_provenance("stubengine", env={"STUB_ENGINE_SOURCE_SHA": "abc123"})

    assert facet["generatedFrom"] == "pkg:github/someone/stub@abc123"
    assert facet["declared"] is True


def test_a_plugin_may_not_shadow_a_shipped_adapter(clean_tables):
    """A ref would otherwise mean different engines depending on a setting."""
    with pytest.raises(PluginError, match="already registered"):
        register_adapter(_registration("word-overlap"))


def test_a_plugin_may_not_repoint_a_shared_provider(clean_tables):
    """Provider names are shared vocabulary: repointing one changes what other engines preflight."""
    with pytest.raises(PluginError, match="anthropic"):
        register_adapter(_registration("stubengine", providers={"anthropic": "SOMETHING_ELSE"}))


def test_a_registration_cannot_omit_a_load_bearing_row():
    """Absence is a TypeError at the call, not a KeyError at planning time."""
    with pytest.raises(TypeError):
        AdapterRegistration(adapter=_Stub, engine_env={}, base_url_env=None)  # type: ignore[call-arg]


def test_an_in_process_registration_needs_only_what_applies(clean_tables):
    """memrank's own in-process arms carry no engine-table rows; a plugin is held to the same bar.

    `test_adapter_table_coverage` derives its list from adapters whose transport is not
    "in-process", so the four fields describing how to reach and start a separate engine do not
    apply here -- and requiring them would be stricter than the standard `word-overlap` meets.
    """
    adapter = type("InProcAdapter", (_Stub,), {"name": "inproc", "transport": "in-process"})

    name = register_adapter(AdapterRegistration.in_process(
        adapter,
        requirements=EngineRequirements("inproc"),
        provenance={"prefix": None, "type": "application", "image_name": None,
                    "manufacturer": "example", "supplier": "example", "source_repo": None,
                    "ancestors": [], "patches": [], "properties": {}}))

    assert REGISTRY[name] is adapter
    assert name in REQUIREMENTS and name in PROVENANCE
    assert tables.BASE_URL_ENV.get(name) is None, "nothing listens, so there is no address"
    assert tables.READINESS.get(name) is None, "nothing is launched, so nothing is waited on"


def test_in_process_refuses_an_engine_memrank_has_to_drive(clean_tables):
    """The shortcut omits exactly the rows that start and reach a separate process."""
    adapter = type("HttpAdapter", (_Stub,), {"name": "httpish", "transport": "http"})

    with pytest.raises(PluginError, match="not 'in-process'"):
        AdapterRegistration.in_process(
            adapter, requirements=EngineRequirements("httpish"), provenance={})

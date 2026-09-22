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
"""Local Supermemory adapter.

This adapter targets the self-hosted local Supermemory server. It intentionally
does not manage the server process; start the installed binary from ``$HOME`` so
it uses ``~/.supermemory``:

    cd "$HOME" && "$HOME/.supermemory/bin/supermemory-server"

The adapter supports ordinary Memrank retrieval and exposes a normalized graph
snapshot in ``raw["graph_snapshot"]`` for relation-graph benchmarks.
"""

from __future__ import annotations

import os
from datetime import datetime
from typing import Any

import httpx

from memrank.adapters import errors as adapter_errors
from memrank.adapters import transcript
from memrank.adapters.effective import embedder_from_env, llm_from_env
from memrank.core import Document, Memory, Recall
from memrank.instrumentation import LatencyCollector, TokenCollector

_DEFAULT_BASE_URL = "http://localhost:6767"
_DEFAULT_TIMEOUT_S = 60.0

# Regular documents are ingested via /v4/memories, NOT /v3/documents: supermemory's document
# ingestion auto-detects content type and mis-claims transcript/technical content (colon- and
# URL-like tokens such as "User:", "localhost:5000", "http://...", code "::") as a malformed URL,
# rejecting it with 400 "All extractors rejected". /v4/memories stores content directly and skips
# that sniffer; it returns memories synchronously (no readiness poll needed) but caps each memory
# near 8k chars, so we chunk. See docs/research/2026-07-27-supermemory-v3-documents-extractor-limitation.md.
_MAX_MEMORY_CHARS = 8000


class Supermemory(Memory):
    """HTTP adapter for local self-hosted Supermemory."""

    name = "supermemory"
    base_url_env = "SUPERMEMORY_BASE_URL"
    version = "0.1.0"
    engine_version = os.environ.get("SUPERMEMORY_ENGINE_VERSION", "0.0.3-local")
    transport = "http"
    cleanup_is_destructive = True
    graph_capable = True

    def __init__(
        self,
        base_url: str | None = None,
        timeout_s: float | None = None,
    ) -> None:
        self.base_url = (base_url or os.environ.get("SUPERMEMORY_BASE_URL", _DEFAULT_BASE_URL)).rstrip("/")
        self.timeout_s = (
            timeout_s
            if timeout_s is not None
            else float(os.environ.get("SUPERMEMORY_TIMEOUT_S", _DEFAULT_TIMEOUT_S))
        )
        self._isolation: str | None = None
        self._client: httpx.Client | None = None
        self.latency = LatencyCollector()
        self.tokens = TokenCollector()

    def _http(self) -> httpx.Client:
        if self._client is None:
            self._client = adapter_errors.engine_client(
                engine=self.name, timeout_s=self.timeout_s, env_var="SUPERMEMORY_TIMEOUT_S",
                base_url=self.base_url,
                headers={"Content-Type": "application/json"},
            )
        return self._client

    def prepare(self, isolation_unit: str) -> None:
        self._isolation = isolation_unit
        self._cleanup_namespace(isolation_unit)

    def ingest(self, documents: list[Document]) -> None:
        assert self._isolation is not None, "call prepare() before ingest()"
        seeds = [d for d in documents if (d.metadata or {}).get("relation_graph_role") == "seed"]
        ingest_docs = [d for d in documents if (d.metadata or {}).get("relation_graph_role") != "seed"]
        if seeds:
            with self.latency.track("ingest"):
                self._add_seed_memories(seeds)
        if ingest_docs:
            with self.latency.track("ingest"):
                self._post_documents(ingest_docs)

    def retrieve(
        self,
        query: str,
        k: int,
        user_id: str,
        query_timestamp: datetime | str | None = None,
    ) -> Recall:
        namespace = user_id or self._isolation
        if namespace is None:
            raise RuntimeError("retrieve called before prepare")
        # searchMode is STATED, not inherited. The API defaults to "memories"; the vendor's docs
        # recommend "hybrid" and their own benchmark harness uses it, so leaving the default meant
        # running a configuration nobody chose and no receipt recorded (audit F9). Expect little
        # behavioural change while ingest still posts to /v4/memories and bypasses the extractor
        # (F8) -- this is about the run saying what it asked for.
        #
        # threshold stays 0: a recall benchmark should let `limit` decide what comes back rather
        # than have the engine drop candidates by score first. The vendor's harness uses 0.3 and
        # the API default is 0.5; both would silently discard low-scoring-but-correct memories.
        payload = {
            "containerTag": namespace,
            "q": query,
            "limit": k,
            "threshold": 0,
            "searchMode": "hybrid",
            "include": {"relatedMemories": True, "documents": True},
        }
        with self.latency.track("retrieve"):
            response = self._http().post("/v4/search", json=payload)
            adapter_errors.raise_for_status(response)
        body = adapter_errors.safe_json(response)
        self._record_tokens("query", body)
        docs: list[Document] = []
        for i, entry in enumerate(body.get("results") or body.get("memories") or []):
            doc_id = str(entry.get("id") or i)
            content = str(entry.get("memory") or entry.get("content") or entry.get("text") or "")
            metadata = dict(entry.get("metadata") or {})
            if entry.get("similarity") is not None:
                metadata["score"] = entry["similarity"]
            metadata["relation_context"] = self._normalize_context(entry.get("context") or entry.get("relatedMemories") or {})
            docs.append(Document(id=doc_id, content=content, user_id=namespace, metadata=metadata))
        raw = {
            "search": body,
            "graph_snapshot": self._graph_snapshot(namespace),
        }
        return Recall(documents=docs, declared=raw)

    def cleanup(self) -> None:
        if self._isolation is not None:
            self._cleanup_namespace(self._isolation)
        self._isolation = None

    def close(self) -> None:
        if self._client is not None:
            self._client.close()
            self._client = None

    def latency_metrics(self) -> dict[str, float]:
        return self.latency.as_metrics()

    def token_metrics(self) -> dict[str, float | None]:
        return self.tokens.as_metrics()

    def _effective_llm(self) -> dict:
        return llm_from_env("SUPERMEMORY_")

    def _effective_embedder(self) -> dict:
        return embedder_from_env("SUPERMEMORY_")

    def _record_tokens(self, bucket: str, body: dict[str, Any]) -> None:
        """Record ``total_tokens`` from a response body under ``bucket`` if present.

        When the API omits usage, nothing is recorded and the bucket stays
        ``0.0`` -- the codebase's idiomatic "unmeasured" signal, which
        ``compare._engine_tokens`` already renders as ``n/a``. No fabricated
        default and no NaN (which is truthy and would leak past that n/a check).
        """
        usage = body.get("usage") or {}
        total = usage.get("total_tokens")
        if isinstance(total, (int, float)) and total:
            self.tokens.record(bucket, int(total))

    def _add_seed_memories(self, documents: list[Document]) -> None:
        assert self._isolation is not None
        payload = {
            "containerTag": self._isolation,
            "memories": [
                {
                    "content": doc.content,
                    "isStatic": False,
                    "metadata": {
                        "doc_id": doc.id,
                        **(doc.metadata or {}),
                    },
                }
                for doc in documents
            ],
        }
        response = self._http().post("/v4/memories", json=payload)
        adapter_errors.raise_for_status(response)
        self._record_tokens("ingest", adapter_errors.safe_json(response))

    def _post_documents(self, documents: list[Document]) -> None:
        """Ingest documents as memories via /v4/memories, chunked under the per-memory size cap.

        Bypasses /v3/documents, whose content-type sniffer rejects transcript/technical content (see
        the module note). /v4/memories stores content directly and returns synchronously, so no
        readiness poll is needed.
        """
        assert self._isolation is not None
        memories: list[dict[str, Any]] = []
        for doc in documents:
            meta = {"doc_id": doc.id, **(doc.metadata or {})}
            if doc.context:
                meta["entity_context"] = doc.context
            # Rendered, not raw: their own benchmark harness prepends the session date to
            # the content it stores, and `/v4/memories` carries no timestamp field, so the
            # text is the only place a date can travel.
            for chunk in self._chunk(transcript.render(doc)):
                memories.append({"content": chunk, "isStatic": False, "metadata": meta})
        if not memories:
            return
        response = self._http().post(
            "/v4/memories", json={"containerTag": self._isolation, "memories": memories}
        )
        adapter_errors.raise_for_status(response)
        self._record_tokens("ingest", adapter_errors.safe_json(response))

    @staticmethod
    def _chunk(content: str, size: int = _MAX_MEMORY_CHARS) -> list[str]:
        """Split content into <=size pieces, preferring newline boundaries so turns stay intact."""
        if len(content) <= size:
            return [content]
        chunks: list[str] = []
        start = 0
        while start < len(content):
            end = start + size
            if end < len(content):
                nl = content.rfind("\n", start, end)
                if nl > start:
                    end = nl + 1
            chunks.append(content[start:end])
            start = end
        return chunks

    def _graph_snapshot(self, namespace: str) -> dict[str, Any]:
        try:
            response = self._http().post(
                "/v4/memories/list",
                json={"containerTags": [namespace], "limit": 200, "sort": "createdAt", "order": "desc"},
            )
            adapter_errors.raise_for_status(response)
        # See the note in atomicmemory's snapshot: `EngineRejected` is a MemrankError, so leaving
        # it out here would turn a best-effort snapshot into a run-ending failure.
        except (httpx.HTTPError, adapter_errors.EngineRejected) as exc:
            return {"memories": [], "error": str(exc)}
        body = adapter_errors.safe_json(response)
        if not any(key in body for key in ("memoryEntries", "memories", "results")):
            return {"memories": [], "error": f"memories/list body missing a memory list: got keys {sorted(body)}"}
        memories = body.get("memoryEntries") or body.get("memories") or body.get("results") or []
        return {"memories": [self._normalize_memory(m) for m in memories]}

    def _cleanup_namespace(self, namespace: str) -> dict[str, Any]:
        response = self._http().request("DELETE", "/v3/documents/bulk", json={"containerTags": [namespace]})
        adapter_errors.raise_for_status(response)
        return adapter_errors.safe_json(response)

    @staticmethod
    def _normalize_memory(entry: dict[str, Any]) -> dict[str, Any]:
        return {
            "provider_memory_id": entry.get("id"),
            "text": entry.get("memory") or entry.get("content") or entry.get("text") or "",
            "is_latest": entry.get("isLatest", entry.get("is_latest", True)),
            "is_forgotten": entry.get("isForgotten", entry.get("is_forgotten", False)),
            "is_inference": entry.get("isInference", entry.get("is_inference", False)),
            "version": entry.get("version"),
            "relations": [
                {"parent_provider_memory_id": parent, "relation": relation}
                for parent, relation in (entry.get("memoryRelations") or {}).items()
            ],
            "history": [
                {
                    "provider_memory_id": h.get("id"),
                    "text": h.get("memory") or h.get("content") or h.get("text") or "",
                    "is_latest": h.get("isLatest", h.get("is_latest", False)),
                    "is_forgotten": h.get("isForgotten", h.get("is_forgotten", False)),
                    "version": h.get("version"),
                }
                for h in entry.get("history") or []
            ],
            "metadata": entry.get("metadata") or {},
        }

    @staticmethod
    def _normalize_context(context: dict[str, Any]) -> list[dict[str, Any]]:
        out: list[dict[str, Any]] = []
        for group in ("parents", "children", "related"):
            for item in context.get(group) or []:
                out.append({
                    "provider_memory_id": item.get("id"),
                    "text": item.get("memory") or item.get("content") or item.get("text") or "",
                    "relation": item.get("relation"),
                    "context_group": group,
                })
        return out


#: Deprecated alias of the class above -- the same class object, so an out-of-tree import and
#: every ``isinstance`` against the older spelling keep holding. The suffix went because a reader
#: copies the class name out of a first result, and ``Adapter`` is memrank's word for the wrapper
#: rather than the reader's word for the system. Removing it is plan step 22 (ATO-2151).
SupermemoryAdapter = Supermemory

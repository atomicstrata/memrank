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
"""Evidence-based retrieval scoring.

Engine-id-agnostic: a query is scored by whether the gold answer's required
spans appear in the *content* of a single retrieved document, optionally gated
by true evidence doc ids (matched against ``metadata['doc_id']``, never the
engine's opaque ``id``). Negative queries invert: correct means the wrong
memory was NOT surfaced. There is deliberately no "non-empty = hit" fallback.
"""

from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass, field

from memrank.core import Document

_PUNCT_WS = re.compile(r"[^\w\s]", flags=re.UNICODE)
_WS = re.compile(r"\s+")


def normalize(text: str) -> str:
    """Lowercase, strip accents, drop punctuation, collapse whitespace."""
    decomposed = unicodedata.normalize("NFKD", text)
    no_accents = "".join(c for c in decomposed if not unicodedata.combining(c))
    no_punct = _PUNCT_WS.sub(" ", no_accents.lower())
    return _WS.sub(" ", no_punct).strip()


@dataclass
class EvidenceSpec:
    """Per-query gold evidence.

    ``kind='positive'``: hit if a single doc contains all ``required_spans``
    (and no ``forbidden_spans``), optionally within ``evidence_doc_ids``.
    ``kind='negative'``: hit if NO retrieved doc contains any ``forbidden_spans``.
    """

    required_spans: list[str] = field(default_factory=list)
    forbidden_spans: list[str] = field(default_factory=list)
    evidence_doc_ids: list[str] = field(default_factory=list)
    kind: str = "positive"


@dataclass
class MatchResult:
    """Outcome of scoring one query against retrieved docs."""

    hit: bool
    matched_span: str | None = None
    matched_doc_id: str | None = None


def _source_id(doc: Document) -> str | None:
    return (doc.metadata or {}).get("doc_id")


def _doc_satisfies(spec: EvidenceSpec, doc: Document) -> str | None:
    """Return the matched span set as a string if ``doc`` satisfies a positive spec."""
    content = normalize(doc.content or "")
    source = _source_id(doc)
    # Lenient gate: enforce evidence_doc_ids only when the doc actually carries a
    # doc_id. Fact-extracting engines (AM, Mem0) and some benchmarks (BEAM) don't
    # preserve source ids; fall back to content matching rather than voiding all hits.
    if spec.evidence_doc_ids and source is not None and source not in spec.evidence_doc_ids:
        return None
    if any(normalize(f) in content for f in spec.forbidden_spans):
        return None
    required = [normalize(s) for s in spec.required_spans]
    if required and all(span in content for span in required):
        return " + ".join(required)
    return None


def score_query(spec: EvidenceSpec, retrieved: list[Document]) -> MatchResult:
    """Score one query's retrieved documents against its evidence spec."""
    if spec.kind == "negative":
        for doc in retrieved:
            if any(normalize(f) in normalize(doc.content or "") for f in spec.forbidden_spans):
                return MatchResult(hit=False, matched_doc_id=doc.id)
        return MatchResult(hit=True)
    for doc in retrieved:
        span = _doc_satisfies(spec, doc)
        if span is not None:
            return MatchResult(hit=True, matched_span=span, matched_doc_id=doc.id)
    return MatchResult(hit=False)


def spec_from_query(query: dict) -> EvidenceSpec:
    """Build an EvidenceSpec from a benchmark query dict."""
    return EvidenceSpec(
        required_spans=list(query.get("required_spans") or []),
        forbidden_spans=list(query.get("forbidden_spans") or []),
        evidence_doc_ids=list(query.get("evidence_doc_ids") or []),
        kind=str(query.get("kind") or "positive"),
    )

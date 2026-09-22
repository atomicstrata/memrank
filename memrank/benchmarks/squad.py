"""SQuAD v1.1 as passage retrieval, never answer-span correctness."""

from __future__ import annotations

import hashlib
import json
import os
import tempfile
import urllib.request
from collections import defaultdict
from pathlib import Path
from typing import Any

from memrank.core import AdapterResponse, Benchmark, BenchmarkUnit, Document, EvalInfo
from memrank.errors import MemrankError
from memrank.quality import declaration_for

_DATA_URL = "https://rajpurkar.github.io/SQuAD-explorer/dataset/dev-v1.1.json"
_DATA_SHA256 = "95aa6a52d5d6a735563366753ca50492a658031da74f301ac5238b03966972c9"
_BUNDLED = Path(__file__).resolve().parent / "data" / "squad_quickstart.json"
_BUNDLED_SHA256 = "3259224bef87fe0db06281f728efde2c5d2bd9943e2bd4dd4dbed25566461a95"
_PASSAGES = 32
_QUESTIONS_PER_PASSAGE = 2


def _digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _verify(path: Path, expected: str) -> None:
    if _digest(path) != expected:
        raise MemrankError(
            f"SQuAD checksum mismatch at {path}. Restore the packaged subset or delete the "
            "cached dev-v1.1.json to download again; SQUAD_DATA_PATH selects a local variant.")


def _download(path: Path) -> None:
    from memrank.benchmarks import dataset_download_notice

    # Only a complete, verified download becomes the cache. Concurrent callers own their
    # temporary files, so one failed transfer cannot replace another's verified copy.
    with tempfile.TemporaryDirectory(dir=path.parent) as temporary:
        staged = Path(temporary) / "dev-v1.1.json"
        try:
            with dataset_download_notice("SQuAD v1.1", _DATA_URL, path):
                urllib.request.urlretrieve(_DATA_URL, staged)
                _verify(staged, _DATA_SHA256)
                os.replace(staged, path)
        except OSError as exc:
            raise MemrankError(
                f"Cannot download SQuAD from {_DATA_URL}: {exc}. Check your connection or "
                "set SQUAD_DATA_PATH to a local SQuAD v1.1 JSON file.") from exc


def _question(qa: dict[str, Any], context: str, doc_id: str,
              group: str, category: str) -> dict[str, Any]:
    """Validate the source annotation, then retain only the relevant passage identity."""
    answers = qa.get("answers") or []
    if not answers or not all(
        isinstance(a.get("answer_start"), int) and a["answer_start"] >= 0
        and isinstance(a.get("text"), str) and bool(a["text"])
        and context[a["answer_start"]:a["answer_start"] + len(a["text"])] == a["text"]
        for a in answers
    ):
        raise MemrankError(f"SQuAD question {qa.get('id')!r} has invalid answer spans.")
    if not isinstance(qa.get("id"), str) or not qa["id"] or not qa.get("question"):
        raise MemrankError("SQuAD questions require a nonempty id and question.")
    return {"id": qa["id"], "text": qa["question"], "user_id": group,
            "evidence_doc_ids": [doc_id], "category": category}


def _normalized(text: str) -> str:
    return " ".join(text.split())


class SQuADBenchmark(Benchmark):
    """One passage pool, ingested before its questions; full dev is an explicit mode."""

    name = "squad"
    dataset_version = "squad-dev-v1.1"
    substring_recall_supported = False
    quality_metric = "passage_recall"
    # Browser policy allows smoke but must keep full disallowed: full downloads the dev set.
    info = EvalInfo(unit="passage pool", units_declared="32 passages, 64 questions (quick start)",
                    slices=("smoke", "full"))

    def __init__(self, slice: str | None = None, k: int = 10,
                 data_path: str | None = None) -> None:
        if slice not in (None, "smoke", "full"):
            raise ValueError("SQuAD slice must be None or 'smoke' (quick start), or 'full'.")
        if not isinstance(k, int) or isinstance(k, bool) or k < 1:
            raise ValueError("SQuAD k must be a positive integer.")
        self.slice, self.k = (None if slice == "smoke" else slice), k
        local = os.environ.get("SQUAD_DATA_PATH") or data_path
        self._local_path = Path(local) if local else None
        self.question_text_public = local is None

    def _data_path(self) -> Path:
        if self._local_path is not None:
            if not self._local_path.is_file():
                raise MemrankError(f"SQUAD_DATA_PATH is not a file: {self._local_path}")
            return self._local_path
        if self.slice is None:
            if not _BUNDLED.is_file():
                raise MemrankError("SQuAD quick-start data is missing. Reinstall memrank.")
            _verify(_BUNDLED, _BUNDLED_SHA256)
            return _BUNDLED
        from memrank.benchmarks import cache_root

        path = cache_root() / "squad" / "dev-v1.1.json"
        path.parent.mkdir(parents=True, exist_ok=True)
        if not path.exists():
            _download(path)
        _verify(path, _DATA_SHA256)
        return path

    def _load_raw(self) -> list[dict[str, Any]]:
        path = self._data_path()
        try:
            raw = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, ValueError) as exc:
            raise MemrankError(f"Cannot read SQuAD JSON at {path}: {exc}") from exc
        if not isinstance(raw, dict) or raw.get("version") != "1.1":
            raise MemrankError("SQuAD requires a v1.1 JSON object with version '1.1'.")
        articles = raw.get("data")
        if not isinstance(articles, list) or not articles:
            raise MemrankError("SQuAD data must contain a nonempty article array.")
        return articles

    def _paragraphs(self) -> list[tuple[int, int, str, dict[str, Any]]]:
        paragraphs = [(ai, pi, article["title"], paragraph)
                      for ai, article in enumerate(self._load_raw())
                      for pi, paragraph in enumerate(article["paragraphs"])]
        if self.slice is None:
            if len(paragraphs) < _PASSAGES:
                raise MemrankError(f"SQuAD quick start needs at least {_PASSAGES} passages.")
            paragraphs = paragraphs[:_PASSAGES]
        if not paragraphs:
            raise MemrankError("SQuAD contains no passages.")
        return paragraphs

    def load(self) -> list[BenchmarkUnit]:
        group = f"squad-v1.1-{self.slice or 'quickstart'}"
        documents: list[Document] = []
        queries: list[dict[str, Any]] = []
        for ai, pi, title, paragraph in self._paragraphs():
            context, qas = paragraph["context"], paragraph["qas"]
            if not isinstance(context, str) or not context.strip() or not qas:
                raise MemrankError(f"SQuAD passage {ai}:{pi} needs text and questions.")
            if self.slice is None:
                if len(qas) < _QUESTIONS_PER_PASSAGE:
                    raise MemrankError(f"SQuAD passage {ai}:{pi} needs two questions.")
                qas = qas[:_QUESTIONS_PER_PASSAGE]
            doc_id = f"squad-v1.1-a{ai}-p{pi}"
            documents.append(Document(id=doc_id, content=context, user_id=group,
                                      metadata={"title": title}))
            queries.extend(_question(qa, context, doc_id, group, title) for qa in qas)
        if len({q["id"] for q in queries}) != len(queries):
            raise MemrankError("SQuAD question ids must be unique.")
        return [BenchmarkUnit(unit_id=group, isolation_id=group,
                              documents=documents, queries=queries)]

    def config_for_receipt(self) -> dict[str, Any]:
        return {**super().config_for_receipt(), "source_url": _DATA_URL,
                "upstream_sha256": _DATA_SHA256, "dataset_sha256": _digest(self._data_path()),
                "selection": "article/paragraph/question array order",
                "passages": _PASSAGES if self.slice is None else "all",
                "questions_per_passage": _QUESTIONS_PER_PASSAGE if self.slice is None else "all",
                "mode": self.slice or "quickstart", "local_override": self._local_path is not None,
                "matcher": "whole-passage containment; whitespace collapsed; case preserved"}

    def score(self, unit: BenchmarkUnit, responses: list[AdapterResponse]) -> dict[str, Any]:
        passages = {d.id: _normalized(d.content) for d in unit.documents}
        recalled = {r.query_id: [_normalized(d.content) for d in r.documents] for r in responses}
        categories: dict[str, list[float]] = defaultdict(list)
        per_query = []
        for query in unit.queries:
            gold = passages[query["evidence_doc_ids"][0]]
            hit = float(any(gold and gold in text for text in recalled.get(query["id"], [])))
            categories[query["category"]].append(hit)
            per_query.append({"query_id": query["id"], "passage_recall": hit})
        if not per_query:
            raise MemrankError("SQuAD cannot score a unit with no questions.")
        return {"composite": sum(q["passage_recall"] for q in per_query) / len(per_query),
                "per_category": {c: sum(v) / len(v) for c, v in categories.items()},
                "n_queries": len(per_query), "per_query": per_query,
                "metric": declaration_for(self.quality_metric).description}

    def report_template(self) -> str:
        return ("# SQuAD passage retrieval -- {adapter}\n\n"
                + declaration_for(self.quality_metric).description + "\n\n"
                "- Passage recall: **{composite}**\n- Dataset: {dataset_version}\n"
                "\n## Per-category\n{per_category_md}\n")

"""Hand-authored data pins passage retrieval without copying any SQuAD text."""

import hashlib
import json
from pathlib import Path
from unittest.mock import patch

import pytest

from memrank.benchmarks import squad
from memrank.core import AdapterResponse, Document
from memrank.errors import MemrankError


def _fixture():
    return {"version": "1.1", "data": [
        {"title": "Gardens", "paragraphs": [
            {"context": "Ada planted blue flowers.", "qas": [
                {"id": "q1", "question": "What did Ada plant?",
                 "answers": [{"text": "blue flowers", "answer_start": 12}]},
                {"id": "q2", "question": "Who planted flowers?",
                 "answers": [{"text": "Ada", "answer_start": 0}]},
            ]}]},
        {"title": "Boats", "paragraphs": [
            {"context": "Ben painted blue boats.", "qas": [
                {"id": "q3", "question": "What did Ben paint?",
                 "answers": [{"text": "blue boats", "answer_start": 12}]},
            ]}]},
    ]}


@pytest.fixture
def local_data(tmp_path, monkeypatch):
    path = tmp_path / "squad.json"
    path.write_text(json.dumps(_fixture()))
    monkeypatch.setenv("SQUAD_DATA_PATH", str(path))
    return path


def test_loader_keeps_passage_pool_and_source_question_ids(local_data):
    benchmark = squad.SQuADBenchmark(slice="full")
    unit, = benchmark.load()

    assert unit.unit_id == unit.isolation_id == "squad-v1.1-full"
    assert [d.id for d in unit.documents] == ["squad-v1.1-a0-p0", "squad-v1.1-a1-p0"]
    assert [q["id"] for q in unit.queries] == ["q1", "q2", "q3"]
    assert unit.queries[2]["evidence_doc_ids"] == [unit.documents[1].id]
    assert all(q["user_id"] == unit.isolation_id for q in unit.queries)
    assert all("gold_answers" not in q and "required_spans" not in q for q in unit.queries)
    assert not benchmark.question_text_public
    assert benchmark.raw() == _fixture()["data"]


def test_scorer_requires_whole_passage_not_answer_or_document_id(local_data):
    benchmark = squad.SQuADBenchmark(slice="full")
    unit, = benchmark.load()
    responses = [
        AdapterResponse(query_id="q1", documents=[Document(id="rewritten", content=
            "Header: Ada  planted\nblue flowers. Footer")]),
        AdapterResponse(query_id="q2", documents=[Document(id=unit.documents[0].id,
                                                         content="Ada")]),
    ]
    scored = benchmark.score(unit, responses)

    assert scored["composite"] == pytest.approx(1 / 3)
    assert scored["per_category"] == {"Gardens": 0.5, "Boats": 0.0}
    assert scored["n_queries"] == 3
    assert [q["passage_recall"] for q in scored["per_query"]] == [1.0, 0.0, 0.0]
    assert scored["metric"] == (
        "full-passage retrieval recall, not answer-span or end-to-end answer correctness")


def test_scorer_counts_duplicate_passages_once_and_missing_responses_as_misses(local_data):
    benchmark = squad.SQuADBenchmark(slice="full")
    unit, = benchmark.load()
    repeated = AdapterResponse(query_id="q1", documents=[unit.documents[0]] * 3)

    assert benchmark.score(unit, [repeated])["composite"] == pytest.approx(1 / 3)
    assert benchmark.score(unit, [])["composite"] == 0.0
    all_returned = [AdapterResponse(query_id=q["id"], documents=unit.documents)
                    for q in unit.queries]
    assert benchmark.score(unit, all_returned)["composite"] == 1.0


def test_local_override_is_in_receipt_and_is_never_replaced_by_a_download(local_data):
    benchmark = squad.SQuADBenchmark(slice="full")
    config = benchmark.config_for_receipt()

    assert config["dataset_sha256"] == hashlib.sha256(local_data.read_bytes()).hexdigest()
    assert config["local_override"] is True
    local_data.unlink()
    with patch.object(squad.urllib.request, "urlretrieve") as fetch:
        with pytest.raises(MemrankError, match="SQUAD_DATA_PATH is not a file"):
            benchmark.load()
        fetch.assert_not_called()


@pytest.mark.parametrize("bad", ["wrong-version", "span", "duplicate-id", "empty-context"])
def test_invalid_data_fails_loudly(local_data, bad):
    raw = _fixture()
    paragraph = raw["data"][0]["paragraphs"][0]
    if bad == "wrong-version":
        raw["version"] = "2.0"
    elif bad == "span":
        paragraph["qas"][0]["answers"][0]["answer_start"] = 0
    elif bad == "duplicate-id":
        paragraph["qas"][1]["id"] = "q1"
    else:
        paragraph["context"] = ""
    local_data.write_text(json.dumps(raw))

    with pytest.raises(MemrankError):
        squad.SQuADBenchmark(slice="full").load()


def test_quickstart_refuses_a_smaller_local_subset(local_data):
    with pytest.raises(MemrankError, match="at least 32 passages"):
        squad.SQuADBenchmark().load()


def test_full_download_cache_is_verified_and_reused(tmp_path, monkeypatch):
    raw = json.dumps(_fixture()).encode()
    monkeypatch.delenv("SQUAD_DATA_PATH", raising=False)
    monkeypatch.setenv("MEMRANK_CACHE_DIR", str(tmp_path))
    monkeypatch.setattr(squad, "_DATA_SHA256", hashlib.sha256(raw).hexdigest())
    benchmark = squad.SQuADBenchmark(slice="full")

    def download(url, destination):
        Path(destination).write_bytes(raw)

    with patch.object(squad.urllib.request, "urlretrieve", side_effect=download) as fetch:
        assert len(benchmark.load()[0].queries) == 3
        benchmark.load()
        assert fetch.call_count == 1
    cached = tmp_path / "squad" / "dev-v1.1.json"
    assert cached.read_bytes() == raw
    cached.write_text("corrupted")
    with pytest.raises(MemrankError, match="checksum mismatch"):
        benchmark.load()


def test_failed_download_never_becomes_a_cache(tmp_path, monkeypatch):
    monkeypatch.delenv("SQUAD_DATA_PATH", raising=False)
    monkeypatch.setenv("MEMRANK_CACHE_DIR", str(tmp_path))
    with patch.object(squad.urllib.request, "urlretrieve", side_effect=OSError("offline")):
        with pytest.raises(MemrankError, match="set SQUAD_DATA_PATH"):
            squad.SQuADBenchmark(slice="full").load()
    assert not (tmp_path / "squad" / "dev-v1.1.json").exists()


def test_bundled_quickstart_is_offline_and_pins_provenance(monkeypatch):
    monkeypatch.delenv("SQUAD_DATA_PATH", raising=False)
    with patch.object(squad.urllib.request, "urlretrieve") as fetch:
        benchmark = squad.SQuADBenchmark()
        unit, = benchmark.load()
        config = benchmark.config_for_receipt()
        fetch.assert_not_called()
    raw = json.loads(squad._BUNDLED.read_text())
    assert len(unit.documents) == 32
    assert len(unit.queries) == 64
    assert unit.queries[0]["id"] == "56be4db0acb8001400a502ec"
    assert raw["provenance"]["upstream_sha256"] == squad._DATA_SHA256
    assert len(raw["provenance"]["wikipedia_sources"]) == 32
    assert config["dataset_sha256"] == squad._BUNDLED_SHA256
    assert (config["passages"], config["questions_per_passage"]) == (32, 2)


@pytest.mark.parametrize("missing", [False, True])
def test_missing_or_corrupt_bundle_never_downloads(tmp_path, monkeypatch, missing):
    monkeypatch.delenv("SQUAD_DATA_PATH", raising=False)
    path = tmp_path / "bundle.json"
    if not missing:
        path.write_text("corrupt")
    monkeypatch.setattr(squad, "_BUNDLED", path)
    with patch.object(squad.urllib.request, "urlretrieve") as fetch:
        with pytest.raises(MemrankError, match="missing|checksum mismatch"):
            squad.SQuADBenchmark().load()
        fetch.assert_not_called()


def test_public_squad_runs_tfidf_and_round_trips_its_honest_metric(tmp_path, monkeypatch):
    from memrank import Result
    from memrank.evaluations import SQuAD
    from memrank.systems import TFIDF

    monkeypatch.delenv("SQUAD_DATA_PATH", raising=False)
    result = SQuAD().run(system=TFIDF())
    restored = Result.load(result.save(tmp_path / "squad.json"))
    score, = restored.values_of("squad-score")
    assert score.value == 62 / 64
    assert "full-passage retrieval recall, not answer-span or end-to-end answer correctness" in str(restored)
    assert len(restored.traces) == 64
    assert restored.values_of("failure-rate")[0].value == 0


def test_smoke_alias_uses_the_same_bundle_and_receipt(monkeypatch):
    monkeypatch.delenv("SQUAD_DATA_PATH", raising=False)
    default, smoke = squad.SQuADBenchmark(), squad.SQuADBenchmark(slice="smoke")
    assert smoke.load() == default.load()
    assert smoke.config_for_receipt() == default.config_for_receipt()
    assert smoke.info.slices == ("smoke", "full")

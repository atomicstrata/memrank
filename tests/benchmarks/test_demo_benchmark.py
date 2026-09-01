from memrank.benchmarks.demo import DemoBenchmark
from memrank.core import AdapterResponse, Document


def _resp(qid, *contents):
    docs = [Document(id=f"m{i}", content=c, metadata={"doc_id": _src(c)})
            for i, c in enumerate(contents)]
    return AdapterResponse(query_id=qid, documents=docs)


def _src(content):
    if "marine biologist" in content or "blue whale" in content:
        return "sess_1"
    if "april" in content.lower():
        return "sess_2"
    return "sess_3"


def test_load_returns_one_unit_with_five_queries():
    units = DemoBenchmark().load()
    assert len(units) == 1
    assert len(units[0].queries) == 5


def test_perfect_retrieval_scores_high():
    unit = DemoBenchmark().load()[0]
    responses = [
        _resp("q_job", "Alex is a marine biologist in Portland."),
        _resp("q_animal", "favorite animal is the blue whale"),
        _resp("q_visit", "Dana is visiting in April"),
        _resp("q_diet", "Alex orders vegetarian sushi"),
        _resp("q_allergy_neg", "Alex enjoys hiking"),
    ]
    score = DemoBenchmark().score(unit, responses)
    assert score["composite"] == 1.0


def test_negative_query_fails_when_wrong_memory_surfaced():
    unit = DemoBenchmark().load()[0]
    responses = [_resp("q_allergy_neg", "Alex is allergic to peanuts")]
    score = DemoBenchmark().score(unit, responses)
    assert score["per_category"]["abstention"] == 0.0


def test_distractor_does_not_false_hit_on_diet():
    unit = DemoBenchmark().load()[0]
    responses = [_resp("q_diet", "Sam loves regular sushi")]
    score = DemoBenchmark().score(unit, responses)
    assert score["per_category"]["preference"] == 0.0

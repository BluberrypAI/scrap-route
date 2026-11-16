import json
from threading import Barrier, Lock

import pytest
from pydantic import ValidationError

from resource_ai.agents.intake_review import IntakeBatchRequest, review_batch
from resource_ai.integrations.llm_client import ReviewModelUnavailable
from tests.unit.test_lot_review import context, finding, packet


def response(packets):
    return json.dumps(
        [
            {
                "capability_key": p["capability_key"],
                "kind": "form_mentioned",
                "source_id": "s1",
                "quote": "This site accepts PP scrap.",
                "lot_review": finding(),
            }
            for p in packets
        ]
    )


def test_five_candidates_share_one_observation_and_all_receive_bounded_reviews():
    request = IntakeBatchRequest(
        candidates=[packet(f"site-{i}") for i in range(5)], lot_context=context()
    )
    lock, barrier = Lock(), Barrier(3, timeout=5)
    seen, photos = [], []
    observation = finding()["photo_observations"]

    def model(**kwargs):
        evidence = json.loads(kwargs["evidence"])
        if kwargs.get("images"):
            assert evidence == {"photo_ids": ["photo-1"]}
            photos.append(evidence)
            return json.dumps({"observations": observation})
        assert evidence["visual_observations"] == [{**observation[0], "visibility": "limited"}]
        batch = evidence["candidates"]
        with lock:
            seen.append([p["capability_key"] for p in batch])
        barrier.wait()
        return response(batch)

    results = review_batch(request, model).results
    assert len(photos) == 1
    assert sorted(map(len, seen)) == [1, 2, 2]
    assert sorted(key for batch in seen for key in batch) == list(results)
    assert all(value.status == "reviewed" for value in results.values())
    assert all(value.lot_review.status == "reviewed" for value in results.values())
    assert all(not value.dispatch_approved for value in results.values())
    assert all(
        value.lot_review.photo_observations == results["site-0"].lot_review.photo_observations
        for value in results.values()
    )


@pytest.mark.parametrize("fault", ["timeout", "invalid_json", "invalid_shape", "duplicate"])
def test_failed_comparison_does_not_discard_other_candidates_or_retry_photos(fault):
    request = IntakeBatchRequest(
        candidates=[packet(f"site-{i}") for i in range(5)], lot_context=context()
    )
    calls = []

    def model(**kwargs):
        evidence = json.loads(kwargs["evidence"])
        if kwargs.get("images"):
            calls.append("photo")
            return json.dumps({"observations": finding()["photo_observations"]})
        batch = evidence["candidates"]
        if batch[0]["capability_key"] == "site-0":
            if fault == "timeout":
                raise ReviewModelUnavailable("provider timeout")
            if fault == "invalid_json":
                return "unparseable"
            if fault == "invalid_shape":
                return "{}"
            rows = json.loads(response(batch))
            return json.dumps(rows + rows)
        return response(batch)

    results = review_batch(request, model).results
    assert calls == ["photo"]
    assert [r.status for r in results.values()] == [
        "model_unavailable",
        "model_unavailable",
        "reviewed",
        "reviewed",
        "reviewed",
    ]
    assert all(results[f"site-{i}"].lot_review.status == "model_unavailable" for i in (0, 1))


def test_public_evidence_only_still_uses_one_call_for_five_candidates():
    calls = []
    request = IntakeBatchRequest(candidates=[packet(f"site-{i}") for i in range(5)])

    def model(**kwargs):
        assert "images" not in kwargs
        candidates = json.loads(kwargs["evidence"])
        calls.append(candidates)
        return response(candidates)

    results = review_batch(request, model).results
    assert len(calls) == 1 and len(calls[0]) == 5
    assert all(r.status == "reviewed" and r.lot_review is None for r in results.values())


def test_duplicate_candidate_keys_are_rejected_instead_of_silently_dropped():
    with pytest.raises(ValidationError, match="Duplicate candidate keys"):
        IntakeBatchRequest(candidates=[packet(), packet()])


def test_lot_without_photos_is_also_bounded_but_never_calls_vision():
    request = IntakeBatchRequest(
        candidates=[packet(f"site-{i}") for i in range(5)], lot_context=context(False)
    )
    seen = []

    def model(**kwargs):
        assert kwargs["images"] == []
        evidence = json.loads(kwargs["evidence"])
        assert evidence["visual_observations"] == []
        seen.extend(p["capability_key"] for p in evidence["candidates"])
        return response(evidence["candidates"])

    results = review_batch(request, model).results
    assert sorted(seen) == list(results)
    assert all(r.lot_review.observation_method == "no_photo" for r in results.values())

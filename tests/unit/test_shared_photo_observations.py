import json

import pytest
from pydantic import ValidationError

from resource_ai.agents.intake_review import IntakeBatchRequest, review_batch
from tests.unit.test_lot_review import context, packet


def test_preobserved_references_never_send_images_to_model():
    lot = context().model_dump()
    lot.update(photos=[], photo_ids=["photo-1"])
    observations = [
        {"photo_id": "photo-1", "description": "작은 조각이 보여요", "visibility": "clear"}
    ]
    request = IntakeBatchRequest(
        candidates=[packet()], lot_context=lot, photo_observations=observations
    )
    calls = []

    def model(**kwargs):
        assert kwargs["images"] == []
        data = json.loads(kwargs["evidence"])
        assert data["visual_observations"] == observations
        calls.append(data)
        return json.dumps(
            [
                {
                    "capability_key": "site-a",
                    "kind": "insufficient",
                    "source_id": None,
                    "quote": None,
                    "lot_review": {"photo_observations": [], "concerns": [], "questions": []},
                }
            ]
        )

    result = review_batch(request, model).results["site-a"]
    assert len(calls) == 1
    assert result.lot_review.observation_method == "isolated_vision"
    assert result.lot_review.photo_observations[0].photo_id == "photo-1"


def test_non_waste_short_circuit_still_produces_the_existing_blocking_signal():
    req = IntakeBatchRequest(
        candidates=[packet(), packet("site-b")],
        lot_context=context(),
        photo_observations=[
            {"photo_id": "photo-1", "description": "캐릭터 그림", "visibility": "not_waste"}
        ],
    )

    def never(**kwargs):
        pytest.fail("A non-waste photograph must not trigger facility comparisons")

    response = review_batch(req, never)
    assert len(response.results) == 2
    assert all(
        r.lot_review.photo_observations[0].visibility == "not_waste"
        for r in response.results.values()
    )


def test_unobserved_references_and_wrong_photo_ids_are_rejected():
    lot = context().model_dump()
    lot.update(photos=[], photo_ids=["photo-1"])
    with pytest.raises(ValidationError):
        IntakeBatchRequest(candidates=[packet()], lot_context=lot)
    with pytest.raises(ValidationError):
        IntakeBatchRequest(candidates=[packet()], lot_context=lot, photo_observations=[])

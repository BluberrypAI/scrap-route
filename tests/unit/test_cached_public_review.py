import json

import pytest

from resource_ai.agents.intake_review import IntakeBatchRequest, review_batch
from resource_ai.integrations.llm_client import ReviewModelUnavailable
from tests.unit.test_lot_review import context, packet


def request(quote="This site accepts PP scrap."):
    return IntakeBatchRequest(
        candidates=[packet()],
        lot_context=context(photos=False),
        public_findings={"site-a": {"kind": "form_mentioned", "source_id": "s1", "quote": quote}},
    )


def test_public_citation_is_reused_and_only_current_lot_is_sent_for_judgment():
    calls = []

    def model(**kwargs):
        evidence = json.loads(kwargs["evidence"])
        assert "sources" not in evidence["candidate"]
        assert evidence["verified_public_review"]["quote"] == "This site accepts PP scrap."
        assert evidence["lot"]["condition"] == context(photos=False).condition
        assert kwargs["images"] == []
        calls.append(kwargs)
        return json.dumps({"photo_observations": [], "concerns": [], "questions": []})

    value = review_batch(request(), model).results["site-a"]
    assert len(calls) == 1 and value.finding == "form_mentioned"
    assert value.lot_review.status == "reviewed" and not value.dispatch_approved


@pytest.mark.parametrize("quote", ["This site accepts PET scrap.", "Invented acceptance quote."])
def test_reused_public_result_cannot_bypass_source_and_material_validation(quote):
    def never(**kwargs):
        pytest.fail("An invalid public citation must not trigger a lot review")

    value = review_batch(request(quote), never).results["site-a"]
    assert value.status == "needs_evidence" and value.lot_review is None


def test_lot_model_failure_preserves_public_fact_but_never_marks_lot_reviewed():
    def unavailable(**kwargs):
        raise ReviewModelUnavailable("provider timeout")

    value = review_batch(request(), unavailable).results["site-a"]
    assert value.finding == "form_mentioned" and value.lot_review.status == "model_unavailable"

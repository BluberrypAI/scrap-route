import json

import pytest

from resource_ai.agents.intake_review import (
    Finding,
    IntakeBatchRequest,
    PublicIntakePacket,
    apply_public_finding,
    review_batch,
)
from tests.unit.test_lot_review import context, packet


def reviewed(summary, *, material="pp", scope="published_site_process"):
    value = packet()
    value.update(material=material, site_scope=scope)
    value["sources"][0]["summary"] = summary
    result = Finding(
        kind="insufficient",
        process_match="matched",
        process_source_id="s1",
        process_quote=summary,
        evidence_gaps=["input_form_unproven"],
    )
    return PublicIntakePacket.model_validate(value), result


def test_process_manufacturing_without_explicit_feedstock_acceptance_is_a_candidate():
    p, finding = reviewed("This factory manufactures recycled PP pellets.")
    result = apply_public_finding(p, finding)
    assert result.status == "reviewed" and result.process_match == "matched"
    assert result.finding == "insufficient" and result.quote is None
    assert result.process_quote == p.sources[0].summary and not result.dispatch_approved


@pytest.mark.parametrize(
    "summary,material,scope",
    [
        ("This supplier sells PP pellets.", "pp", "published_site_process"),
        ("This factory manufactures PE pellets.", "pp", "published_site_process"),
        ("This factory does not manufacture PP pellets.", "pp", "published_site_process"),
        ("This company manufactures recycled PP pellets.", "pp", "site_role_hypothesis"),
    ],
)
def test_sales_wrong_material_negated_operation_and_unknown_site_are_not_confirmed(
    summary, material, scope
):
    p, finding = reviewed(summary, material=material, scope=scope)
    assert apply_public_finding(p, finding).process_match == "unverified"


@pytest.mark.parametrize("cached", [True, False])
def test_lot_review_does_not_turn_unknown_purity_into_evidence_questions(cached):
    p, finding = reviewed("This factory manufactures recycled PP pellets.")
    request = IntakeBatchRequest(
        candidates=[p],
        lot_context=context(photos=False),
        public_findings={p.capability_key: finding} if cached else None,
    )

    def model(**kwargs):
        lot = {
            "photo_observations": [],
            "questions": ["허가증과 시험성적서를 제출해 주세요"],
            "concerns": [
                {
                    "basis": "description",
                    "reference": "순도는 모릅니다",
                    "concern": "시험자료가 없음",
                    "next_check": "시험성적서 제출",
                    "category": "testing",
                }
            ],
        }
        if cached:
            return json.dumps(lot)
        return json.dumps(
            [{**finding.model_dump(), "capability_key": p.capability_key, "lot_review": lot}]
        )

    result = review_batch(request, model).results[p.capability_key]
    assert result.process_match == "matched" and result.lot_review.status == "reviewed"
    assert result.lot_review.questions == result.lot_review.concerns == []

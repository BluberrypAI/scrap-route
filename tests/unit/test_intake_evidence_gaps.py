import json

import pytest

from resource_ai.agents.intake_review import IntakeBatchRequest, review_batch


@pytest.mark.parametrize(
    "kind,quote,gaps,scope,expected",
    [
        (
            "insufficient",
            None,
            ["output_only", "input_form_unproven"],
            "published_site_process",
            ["output_only", "input_form_unproven"],
        ),
        ("insufficient", None, [], "published_site_process", ["unspecified"]),
        (
            "form_mentioned",
            "PP 스크랩을 받습니다.",
            [],
            "site_role_hypothesis",
            ["site_scope_unverified"],
        ),
        (
            "form_mentioned",
            "허구의 PP 스크랩 문장",
            [],
            "published_site_process",
            ["citation_invalid"],
        ),
        (
            "form_mentioned",
            "PE 스크랩을 받습니다.",
            [],
            "published_site_process",
            ["material_unproven"],
        ),
        (
            "form_mentioned",
            "PP 펠릿을 생산합니다.",
            [],
            "published_site_process",
            ["input_form_unproven"],
        ),
        (
            "form_mentioned",
            "PP 스크랩은",
            [],
            "published_site_process",
            ["source_context_conflict"],
        ),
    ],
)
def test_gap_reasons_preserve_model_finding_and_enforce_server_guards(
    kind, quote, gaps, scope, expected
):
    request = IntakeBatchRequest(
        candidates=[
            {
                "capability_key": "site",
                "site": "합성 사업장",
                "site_scope": scope,
                "material": "pp",
                "form": "scrap",
                "process": "분쇄",
                "waste_code": "51-03-01",
                "recycling_types": {},
                "next_check": "사업장 확인",
                "sources": [
                    {
                        "source_id": "public",
                        "publisher": "시험",
                        "url": "https://example.org/process",
                        "locator": "공정",
                        "summary": "PP 스크랩을 받습니다. PE 스크랩을 받습니다. PP 펠릿을 생산합니다. PP 스크랩은 오염시 반입 불가입니다.",
                    }
                ],
            }
        ]
    )
    response = review_batch(
        request,
        lambda **_: json.dumps(
            [
                {
                    "capability_key": "site",
                    "kind": kind,
                    "quote": quote,
                    "source_id": "public" if quote else None,
                    "evidence_gaps": gaps,
                }
            ]
        ),
    ).results["site"]
    assert response.status == "needs_evidence"
    assert response.evidence_gaps == expected
    assert response.dispatch_approved is False


def test_missing_public_sources_have_explicit_reason():
    request = IntakeBatchRequest(
        candidates=[
            {
                "capability_key": "site",
                "site": "합성 사업장",
                "site_scope": "published_site_process",
                "material": "pp",
                "form": "scrap",
                "process": "분쇄",
                "waste_code": "51-03-01",
                "recycling_types": {},
                "next_check": "사업장 확인",
                "sources": [],
            }
        ]
    )
    result = review_batch(request, lambda **_: '[{"capability_key":"site","kind":"insufficient"}]')
    assert result.results["site"].evidence_gaps == ["source_missing"]


@pytest.mark.parametrize("code", ["51-03-01", "51-03-07"])
@pytest.mark.parametrize("word", ["폐PET병", "PET 병", "폐페트병", "PET bottles"])
def test_pet_bottle_evidence_is_not_rejected_by_latin_korean_boundary(code, word):
    quote = f"합성 시화 공장은 {word}을 수거해 PET 플레이크로 재활용합니다."
    request = IntakeBatchRequest(
        candidates=[
            {
                "capability_key": "site",
                "site": "합성 시화 공장",
                "site_scope": "published_site_process",
                "material": "pet",
                "form": "bottle",
                "process": "분쇄·세척",
                "waste_code": code,
                "recycling_types": {},
                "next_check": "현재 인수 별도 확인",
                "sources": [
                    {
                        "source_id": "public",
                        "publisher": "시험",
                        "url": "https://example.org/pet",
                        "locator": "공정",
                        "summary": quote,
                    }
                ],
            }
        ]
    )
    result = review_batch(
        request,
        lambda **_: json.dumps(
            [
                {
                    "capability_key": "site",
                    "kind": "form_mentioned",
                    "source_id": "public",
                    "quote": quote,
                    "evidence_gaps": [],
                }
            ]
        ),
    ).results["site"]
    assert result.status == "reviewed"
    assert result.evidence_gaps == []
    assert result.dispatch_approved is False

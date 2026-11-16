import json

import pytest

from resource_ai.agents.intake_review import IntakeBatchRequest, review_batch


@pytest.mark.parametrize(
    "material,form,quote,expected",
    [
        ("pa6", "net", "넷스파는 폐어망에서 회수한 PA6 원료를 생산한다.", "reviewed"),
        ("ferrous", "scrap", "녹산공장은 철스크랩을 원료로 빌릿을 생산한다.", "reviewed"),
        ("pa66", "rigid", "넷스파는 폐어망에서 회수한 PA6 원료를 생산한다.", "needs_evidence"),
        ("ferrous", "scrap", "다른 공장은 철근 압연만 수행한다.", "needs_evidence"),
        ("pp", "bale", "PP 베일은 반입 불가입니다.", "needs_evidence"),
    ],
)
def test_legal_context_reaches_model_without_overriding_input_evidence(
    material, form, quote, expected
):
    packet = {
        "capability_key": "synthetic",
        "site": "합성 시험 사업장",
        "site_scope": "published_site_process",
        "material": material,
        "form": form,
        "process": "공개 공정 사실 대조",
        "waste_code": "51-03-01",
        "recycling_types": {"free": ["R-10"], "analysis": ["R-10"], "unmarked": []},
        "recycling_basis": {
            "version": "test",
            "as_of": "2026-11-16",
            "source_url": "https://www.law.go.kr/test",
            "pages": [9],
            "notes": ["허가 미확인"],
        },
        "next_check": "현재 반입은 업체 확인",
        "sources": [
            {
                "source_id": "public",
                "publisher": "시험",
                "url": "https://example.org/",
                "locator": "공개 투입 공정",
                "summary": quote,
            }
        ],
    }

    def model(**kwargs):
        data = json.loads(kwargs["evidence"])[0]
        assert data["recycling_types"]["free"] == data["recycling_types"]["analysis"] == ["R-10"]
        assert data["recycling_basis"]["source_url"] == "https://www.law.go.kr/test"
        assert "허가 증명이 아니다" in kwargs["instructions"]
        return json.dumps(
            [
                {
                    "capability_key": "synthetic",
                    "kind": "form_mentioned",
                    "source_id": "public",
                    "quote": quote,
                }
            ]
        )

    result = review_batch(IntakeBatchRequest(candidates=[packet]), model).results["synthetic"]
    assert result.status == expected and result.dispatch_approved is False

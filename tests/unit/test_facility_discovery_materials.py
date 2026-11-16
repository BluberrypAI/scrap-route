import pytest
from pydantic import ValidationError

from resource_ai.agents import facility_discovery as discovery


@pytest.mark.parametrize(
    "material,form,transition,code",
    [
        ("pe", "bale", "pe-bale-prepare", "51-03-01"),
        ("ps", "bale", "ps-bale-prepare", "51-03-01"),
        ("pet", "bottle", "pet-bottle-to-flake", "51-03-07"),
        ("eps", "foam", "eps-foam-densify", "51-03-06"),
        ("ferrous", "scrap", "ferrous-eaf-billet", "51-29-01"),
        ("aluminium", "can", "al-can-sheet", "51-29-03"),
    ],
)
def test_non_pp_search_uses_exact_material_and_only_cited_leads(
    monkeypatch, material, form, transition, code
):
    def response(settings, body, *, timeout):
        assert f"재질 {material.upper()}\n" in body["input"]
        assert discovery.FORMS[form] in body["input"]
        assert code in body["input"]
        return {
            "output": [
                {"type": "web_search_call", "status": "completed", "action": {"sources": []}},
                {"type": "message", "content": [{"type": "output_text", "text": "[]"}]},
            ]
        }

    monkeypatch.setattr(discovery, "azure_response", response)
    request = discovery.FacilityDiscoveryRequest(
        transition_key=transition,
        input_form=form,
        material=material,
        process_label="등록된 공개 공정",
        operation_steps=["등록 단계"],
        region="honam",
        waste_code=code,
        recycling_types=None,
    )
    result = discovery.discover(request, None)
    assert result.status == "searched" and result.leads == [] and not result.dispatch_approved


def test_unknown_or_mismatched_process_is_not_assumed_pp():
    base = {"input_form": "bale", "region": "capital", "waste_code": None, "recycling_types": None}
    with pytest.raises(ValidationError):
        discovery.FacilityDiscoveryRequest(transition_key="pe-bale-prepare", **base)
    with pytest.raises(ValidationError):
        discovery.FacilityDiscoveryRequest(
            transition_key="pe-bale-prepare", material="ps", process_label="선별", **base
        )

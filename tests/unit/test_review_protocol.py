import json
import time
from concurrent.futures import ThreadPoolExecutor
from threading import Lock

from fastapi.testclient import TestClient
from pydantic import SecretStr

from resource_ai.api.routes import intake
from resource_ai.core.config import get_settings
from resource_ai.integrations import llm_client
from resource_ai.main import app
from tests.unit.test_lot_review import JPEG, packet


def test_photo_endpoint_requires_service_auth_and_returns_versioned_independent_observations(
    monkeypatch,
):
    settings = get_settings()
    monkeypatch.setattr(settings, "scrap_intake_service_token", SecretStr("test-token"))
    calls = []

    def model(settings, **kwargs):
        assert json.loads(kwargs["evidence"]) == {"photo_ids": ["photo-1"]}
        assert len(kwargs["images"]) == 1
        calls.append(kwargs)
        return json.dumps(
            {
                "observations": [
                    {"photo_id": "photo-1", "description": "플라스틱 조각", "visibility": "clear"}
                ]
            }
        )

    monkeypatch.setattr(intake, "review_with_azure", model)
    with TestClient(app) as client:
        body = {"photos": [{"photo_id": "photo-1", "data_url": JPEG}]}
        assert client.post("/treatment/photo-observations", json=body).status_code == 401
        headers = {"Authorization": "Bearer test-token"}
        config = client.get("/treatment/review-config", headers=headers).json()
        response = client.post("/treatment/photo-observations", json=body, headers=headers)
        assert response.status_code == 200, response.text
        assert response.json()["signature"] == config["photo_signature"]
        assert response.json()["status"] == "reviewed"
        duplicate = client.post(
            "/treatment/photo-observations",
            json={"photos": body["photos"] * 2},
            headers=headers,
        )
        assert duplicate.status_code == 422
        changed = client.post(
            "/treatment/intake-reviews",
            headers=headers,
            json={
                "candidates": [packet()],
                "lot_context": {
                    "state_key": "pp-scrap",
                    "mass_kg": 100,
                    "condition": "합성 물량",
                    "photo_ids": ["photo-1"],
                },
                "photo_observations": response.json()["observations"],
                "observation_signature": "stale-version",
            },
        )
        assert changed.status_code == 409
    assert len(calls) == 1


def test_model_concurrency_is_bounded_across_separate_http_requests(monkeypatch):
    active = maximum = 0
    lock = Lock()

    def provider(*args, **kwargs):
        nonlocal active, maximum
        with lock:
            active += 1
            maximum = max(active, maximum)
        time.sleep(0.02)
        with lock:
            active -= 1
        return {"status": "completed"}

    monkeypatch.setattr(llm_client, "_azure_response", provider)
    with ThreadPoolExecutor(max_workers=8) as pool:
        values = list(pool.map(lambda _: llm_client.azure_response(None, {}, timeout=5), range(8)))
    assert len(values) == 8 and maximum == 3

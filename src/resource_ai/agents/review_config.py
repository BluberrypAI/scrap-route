"""Opaque fingerprints for safe server-side result reuse. No credentials in output."""

import hashlib
import json
from pathlib import Path

from resource_ai.agents.intake_review import INSTRUCTIONS, LOT_INSTRUCTIONS
from resource_ai.agents.lot_review import PHOTO_INSTRUCTIONS


def review_config(settings):
    identity = [settings.azure_openai_endpoint, settings.azure_openai_deployment, "high", 6500]
    code = hashlib.sha256(
        Path(__file__).with_name("intake_review.py").read_bytes()
        + Path(__file__).with_name("lot_review.py").read_bytes()
    ).hexdigest()

    def signature(value):
        return hashlib.sha256(json.dumps(value, ensure_ascii=False).encode()).hexdigest()

    return {
        "version": "progressive-review-v1",
        "photo_signature": signature([identity, PHOTO_INSTRUCTIONS, code]),
        "comparison_signature": signature([identity, INSTRUCTIONS, LOT_INSTRUCTIONS, code]),
        "public_signature": signature([identity, INSTRUCTIONS, code, "public-only-v1"]),
    }

import pytest

from resource_ai.agents.intake_review import log_review_failure
from resource_ai.integrations.llm_client import ReviewModelUnavailable


@pytest.mark.parametrize(
    "message,reason",
    [
        ("HTTP 429", "provider_rate_limit"),
        ("HTTP 401", "provider_auth"),
        ("provider timeout", "provider_timeout"),
        ("incomplete: max_output_tokens", "output_budget"),
        ("incomplete: content_filter", "provider_filter"),
        ("incomplete response", "incomplete_response"),
        ("private-company secret-key https://private.invalid", "provider_unavailable"),
    ],
)
def test_failure_logging_only_emits_allowlisted_reason(caplog, message, reason):
    log_review_failure(ReviewModelUnavailable(message))
    assert caplog.messages == [f"intake_review_failed reason={reason}"]


def test_invalid_json_does_not_log_model_text(caplog):
    log_review_failure(ValueError("invalid JSON: private-company secret-key"))
    assert caplog.messages == ["intake_review_failed reason=invalid_model_json"]

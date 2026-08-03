"""Tests for the shared environment contract and bounded settings."""

import pytest
from pydantic import ValidationError

from app.config import Settings


def test_backend_settings_use_the_app_prefix(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("APP_LLM_API_KEY", "app-key")
    monkeypatch.setenv("LLM_API_KEY", "legacy-key")

    settings = Settings(_env_file=None)

    assert settings.llm_api_key == "app-key"


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("signal_threshold", 1.1),
        ("contact_threshold", -0.1),
        ("collection_concurrency", 0),
        ("upload_max_bytes", 0),
        ("pipeline_batch_size", 101),
    ],
)
def test_operational_limits_reject_invalid_values(field: str, value: float) -> None:
    with pytest.raises(ValidationError):
        Settings(_env_file=None, **{field: value})

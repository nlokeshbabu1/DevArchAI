"""Tests for LLM_PROVIDER env normalization."""

import os
from unittest.mock import patch

import pytest

from app.config import Settings, get_settings


@pytest.fixture(autouse=True)
def clear_settings_cache():
    get_settings.cache_clear()
    yield
    get_settings.cache_clear()


def test_mistral_model_name_in_llm_provider_is_normalized():
    with patch.dict(
        os.environ,
        {
            "LLM_PROVIDER": "mistral-small-latest",
            "MISTRAL_MODEL": "",
        },
        clear=False,
    ):
        settings = Settings()
        assert settings.LLM_PROVIDER == "mistral"
        assert settings.MISTRAL_MODEL == "mistral-small-latest"


def test_valid_llm_provider_unchanged():
    with patch.dict(os.environ, {"LLM_PROVIDER": "mistral", "MISTRAL_MODEL": "mistral-small-latest"}, clear=False):
        settings = Settings()
        assert settings.LLM_PROVIDER == "mistral"
        assert settings.MISTRAL_MODEL == "mistral-small-latest"

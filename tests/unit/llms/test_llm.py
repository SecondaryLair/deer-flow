# Copyright (c) 2025 Bytedance Ltd. and/or its affiliates
# SPDX-License-Identifier: MIT

from typing import TYPE_CHECKING, cast

import pytest

from deerflowx.config.settings import AppSettings, BasicModelSettings, ReasoningModelSettings, VisionModelSettings
from deerflowx.llms import llm

if TYPE_CHECKING:
    from deerflowx.config.agents import LLMType


class DummyChatOpenAI:
    def __init__(self, **kwargs):
        self.kwargs = kwargs

    def invoke(self, msg):
        return f"Echo: {msg}"


class DummyChatDeepSeek:
    def __init__(self, **kwargs):
        self.kwargs = kwargs

    def invoke(self, msg):
        return f"DeepSeek Echo: {msg}"


@pytest.fixture(autouse=True)
def patch_llm_classes(monkeypatch):
    monkeypatch.setattr(llm, "ChatOpenAI", DummyChatOpenAI)
    monkeypatch.setattr(llm, "ChatDeepSeek", DummyChatDeepSeek)


@pytest.fixture
def mock_settings(monkeypatch):
    """Mock settings with test configuration."""
    test_settings = AppSettings()
    test_settings._basic_model = BasicModelSettings(
        api_key="test_basic_key", base_url="http://test-basic", model="test-basic-model"
    )
    test_settings._reasoning_model = ReasoningModelSettings(
        api_key="test_reasoning_key", base_url="http://test-reasoning", model="test-reasoning-model"
    )
    test_settings._vision_model = VisionModelSettings(
        api_key="test_vision_key", base_url="http://test-vision", model="test-vision-model"
    )

    monkeypatch.setattr("deerflowx.llms.llm.settings", test_settings)
    return test_settings


def test_create_llm_instance_basic(mock_settings):
    """Test creating basic model instance."""
    llm._llm_cache.clear()
    result = llm._create_llm_instance("basic")
    assert isinstance(result, DummyChatOpenAI)
    assert result.kwargs["api_key"] == "test_basic_key"
    assert result.kwargs["base_url"] == "http://test-basic"
    assert result.kwargs["model"] == "test-basic-model"


def test_create_llm_instance_reasoning(mock_settings):
    """Test creating reasoning model instance."""
    llm._llm_cache.clear()
    result = llm._create_llm_instance("reasoning")
    assert isinstance(result, DummyChatDeepSeek)
    assert result.kwargs["api_key"] == "test_reasoning_key"
    assert result.kwargs["api_base"] == "http://test-reasoning"
    assert result.kwargs["model"] == "test-reasoning-model"


def test_create_llm_instance_vision(mock_settings):
    """Test creating vision model instance."""
    llm._llm_cache.clear()
    result = llm._create_llm_instance("vision")
    assert isinstance(result, DummyChatOpenAI)
    assert result.kwargs["api_key"] == "test_vision_key"
    assert result.kwargs["base_url"] == "http://test-vision"
    assert result.kwargs["model"] == "test-vision-model"


def test_create_llm_instance_invalid_type(mock_settings):
    """Test creating LLM with invalid type raises error."""
    with pytest.raises(ValueError, match="Unknown LLM type"):
        llm._create_llm_instance(cast("LLMType", "unknown"))


def test_create_llm_instance_no_api_key(mock_settings):
    """Test creating LLM without API key raises error."""
    mock_settings._basic_model.api_key = ""
    with pytest.raises(ValueError, match="No API key configured"):
        llm._create_llm_instance("basic")


def test_create_llm_instance_reasoning_missing_config(mock_settings):
    """Test creating reasoning model without required config raises error."""
    mock_settings._reasoning_model.base_url = None
    with pytest.raises(ValueError, match="Reasoning model requires base_url and model"):
        llm._create_llm_instance("reasoning")


def test_get_llm_by_type_caches(mock_settings):
    """Test that get_llm_by_type caches instances."""
    llm._llm_cache.clear()
    inst1 = llm.get_llm_by_type("basic")
    inst2 = llm.get_llm_by_type("basic")
    assert inst1 is inst2


def test_get_configured_llm_models(mock_settings):
    """Test getting configured models."""
    result = llm.get_configured_llm_models()
    assert "basic" in result
    assert "reasoning" in result
    assert "vision" in result
    assert result["basic"] == ["test-basic-model"]
    assert result["reasoning"] == ["test-reasoning-model"]
    assert result["vision"] == ["test-vision-model"]


def test_get_configured_llm_models_reasoning_missing_base_url(mock_settings):
    """Test that reasoning model without base_url is not included."""
    mock_settings._reasoning_model.base_url = None
    result = llm.get_configured_llm_models()
    assert "reasoning" not in result


def test_clear_llm_cache(mock_settings):
    """Test clearing the LLM cache."""
    llm.get_llm_by_type("basic")
    assert len(llm._llm_cache) > 0
    llm.clear_llm_cache()
    assert len(llm._llm_cache) == 0


def test_ssl_verification_disabled(mock_settings, monkeypatch):
    """Test SSL verification can be disabled."""
    mock_settings._basic_model.verify_ssl = False

    # Mock httpx clients
    mock_client = object()
    mock_async_client = object()

    def mock_httpx_client(verify):
        assert verify is False
        return mock_client

    def mock_httpx_async_client(verify):
        assert verify is False
        return mock_async_client

    monkeypatch.setattr("deerflowx.llms.llm.httpx.Client", mock_httpx_client)
    monkeypatch.setattr("deerflowx.llms.llm.httpx.AsyncClient", mock_httpx_async_client)

    # Just test that the function runs without error when SSL is disabled
    result = llm._create_llm_instance("basic")
    assert result is not None

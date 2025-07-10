# Copyright (c) 2025 Bytedance Ltd. and/or its affiliates
# SPDX-License-Identifier: MIT

import pytest

from deerflowx.config.settings import AppSettings, BasicModelSettings, ReasoningModelSettings, VisionModelSettings


def test_basic_model_settings_defaults():
    """Test basic model settings with defaults."""
    settings = BasicModelSettings(api_key="test_key")
    assert settings.base_url == "https://ark.cn-beijing.volces.com/api/v3"
    assert settings.model == "doubao-1-5-pro-32k-250115"
    assert settings.api_key == "test_key"
    assert settings.verify_ssl is True


def test_basic_model_settings_with_env(monkeypatch):
    """Test basic model settings with environment variables."""
    monkeypatch.setenv("BASIC_MODEL_API_KEY", "env_key")
    monkeypatch.setenv("BASIC_MODEL_BASE_URL", "http://env")
    monkeypatch.setenv("BASIC_MODEL_MODEL", "env_model")
    monkeypatch.setenv("BASIC_MODEL_VERIFY_SSL", "false")

    settings = BasicModelSettings()
    assert settings.api_key == "env_key"
    assert settings.base_url == "http://env"
    assert settings.model == "env_model"
    assert settings.verify_ssl is False


def test_reasoning_model_settings_defaults():
    """Test reasoning model settings with defaults."""
    settings = ReasoningModelSettings()
    assert settings.base_url is None
    assert settings.model is None
    assert settings.api_key is None
    assert settings.verify_ssl is True


def test_reasoning_model_settings_with_env(monkeypatch):
    """Test reasoning model settings with environment variables."""
    monkeypatch.setenv("REASONING_MODEL_API_KEY", "reason_key")
    monkeypatch.setenv("REASONING_MODEL_BASE_URL", "http://reason")
    monkeypatch.setenv("REASONING_MODEL_MODEL", "reason_model")

    settings = ReasoningModelSettings()
    assert settings.api_key == "reason_key"
    assert settings.base_url == "http://reason"
    assert settings.model == "reason_model"


def test_vision_model_settings_defaults():
    """Test vision model settings with defaults."""
    settings = VisionModelSettings()
    assert settings.base_url is None
    assert settings.model is None
    assert settings.api_key is None
    assert settings.verify_ssl is True


def test_app_settings_defaults():
    """Test app settings with defaults."""
    settings = AppSettings()
    assert settings.search_api == "tavily"
    assert settings.rag_provider is None
    assert isinstance(settings.basic_model, BasicModelSettings)
    assert isinstance(settings.reasoning_model, ReasoningModelSettings)
    assert isinstance(settings.vision_model, VisionModelSettings)


def test_app_settings_with_env(monkeypatch):
    """Test app settings with environment variables."""
    monkeypatch.setenv("SEARCH_API", "duckduckgo")
    monkeypatch.setenv("RAG_PROVIDER", "vikingdb")

    settings = AppSettings()
    assert settings.search_api == "duckduckgo"
    assert settings.rag_provider == "vikingdb"


def test_app_settings_nested_models_initialized():
    """Test that nested model settings are properly initialized."""
    settings = AppSettings()

    # Test that properties return the correct instances
    basic = settings.basic_model
    reasoning = settings.reasoning_model
    vision = settings.vision_model

    assert isinstance(basic, BasicModelSettings)
    assert isinstance(reasoning, ReasoningModelSettings)
    assert isinstance(vision, VisionModelSettings)

    # Test that accessing the same property returns the same instance
    assert settings.basic_model is basic
    assert settings.reasoning_model is reasoning
    assert settings.vision_model is vision

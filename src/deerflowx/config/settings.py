# Copyright (c) 2025 Bytedance Ltd. and/or its affiliates
# SPDX-License-Identifier: MIT
"""Application settings using pydantic-settings."""

from __future__ import annotations

from typing import Any

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class BasicModelSettings(BaseSettings):
    """Basic model configuration settings."""

    model_config = SettingsConfigDict(env_prefix="BASIC_MODEL_")

    base_url: str = "https://ark.cn-beijing.volces.com/api/v3"
    model: str = "doubao-1-5-pro-32k-250115"
    api_key: str = ""
    verify_ssl: bool = True


class ReasoningModelSettings(BaseSettings):
    """Reasoning model configuration settings."""

    model_config = SettingsConfigDict(env_prefix="REASONING_MODEL_")

    base_url: str | None = None
    model: str | None = None
    api_key: str | None = None
    verify_ssl: bool = True


class VisionModelSettings(BaseSettings):
    """Vision model configuration settings."""

    model_config = SettingsConfigDict(env_prefix="VISION_MODEL_")

    base_url: str | None = None
    model: str | None = None
    api_key: str | None = None
    verify_ssl: bool = True


class AppSettings(BaseSettings):
    """Main application settings."""

    model_config = SettingsConfigDict(env_prefix="")

    # Global settings
    search_api: str = Field(default="tavily", alias="SEARCH_API")
    rag_provider: str | None = Field(default=None, alias="RAG_PROVIDER")

    def __init__(self, **data: Any) -> None:
        """Initialize settings."""
        super().__init__(**data)
        # Initialize nested model settings
        self._basic_model = BasicModelSettings()
        self._reasoning_model = ReasoningModelSettings()
        self._vision_model = VisionModelSettings()

    @property
    def basic_model(self) -> BasicModelSettings:
        """Get basic model settings."""
        return self._basic_model

    @property
    def reasoning_model(self) -> ReasoningModelSettings:
        """Get reasoning model settings."""
        return self._reasoning_model

    @property
    def vision_model(self) -> VisionModelSettings:
        """Get vision model settings."""
        return self._vision_model


# Global settings instance
settings = AppSettings()

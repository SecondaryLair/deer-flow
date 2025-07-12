# Copyright (c) 2025 Bytedance Ltd. and/or its affiliates
# SPDX-License-Identifier: MIT
"""Application settings using pydantic-settings."""

from pydantic import Field
from pydantic_settings import BaseSettings as _BaseSettings
from pydantic_settings import SettingsConfigDict


class BaseSettings(_BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )


class BasicModelSettings(BaseSettings):
    """Basic model configuration settings."""

    model_config = SettingsConfigDict(
        env_prefix="BASIC_MODEL_",
    )

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


class LangfuseSettings(BaseSettings):
    """Langfuse observability configuration settings.

    For detailed configuration guide, see: https://langfuse.com/docs/get-started
    """

    model_config = SettingsConfigDict(
        env_prefix="LANGFUSE_",
    )

    public_key: str = ""
    secret_key: str = ""
    host: str = "https://cloud.langfuse.com"

    @property
    def is_enabled(self) -> bool:
        """Check if Langfuse is properly minimally configured."""
        return bool(self.public_key and self.secret_key)


class AppSettings(BaseSettings):
    """Main application settings."""

    model_config = SettingsConfigDict(
        env_prefix="",
    )

    # Global settings
    search_api: str = Field(default="tavily", alias="SEARCH_API")
    rag_provider: str | None = Field(default=None, alias="RAG_PROVIDER")

    basic_model: BasicModelSettings = BasicModelSettings()
    reasoning_model: ReasoningModelSettings = ReasoningModelSettings()
    vision_model: VisionModelSettings = VisionModelSettings()
    langfuse: LangfuseSettings = LangfuseSettings()


# Global settings instance
settings = AppSettings()

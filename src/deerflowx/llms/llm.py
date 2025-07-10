# Copyright (c) 2025 Bytedance Ltd. and/or its affiliates
# SPDX-License-Identifier: MIT
"""LLM management and configuration utilities."""

from __future__ import annotations

from typing import Any, get_args

import httpx
from langchain_deepseek import ChatDeepSeek
from langchain_openai import ChatOpenAI

from deerflowx.config.agents import LLMType
from deerflowx.config.settings import settings

# Cache for LLM instances
_llm_cache: dict[LLMType, ChatOpenAI | ChatDeepSeek] = {}


def _create_llm_instance(llm_type: LLMType) -> ChatOpenAI | ChatDeepSeek:
    """Create LLM instance using configuration from settings."""
    if llm_type == "basic":
        model_settings = settings.basic_model
    elif llm_type == "reasoning":
        model_settings = settings.reasoning_model
    elif llm_type == "vision":
        model_settings = settings.vision_model
    else:
        msg = f"Unknown LLM type: {llm_type}"
        raise ValueError(msg)

    # Check if required configuration is present
    if not model_settings.api_key:
        msg = f"No API key configured for LLM type: {llm_type}"
        raise ValueError(msg)

    # For reasoning model, we need both base_url and model to be configured
    if llm_type == "reasoning" and (not model_settings.base_url or not model_settings.model):
        msg = "Reasoning model requires base_url and model to be configured"
        raise ValueError(msg)

    # Prepare configuration
    config: dict[str, Any] = {
        "model": model_settings.model,
        "api_key": model_settings.api_key,
    }

    # Add base_url if configured
    if model_settings.base_url:
        if llm_type == "reasoning":
            config["api_base"] = model_settings.base_url
        else:
            config["base_url"] = model_settings.base_url

    # Handle SSL verification settings
    if not model_settings.verify_ssl:
        http_client = httpx.Client(verify=False)  # noqa: S501
        http_async_client = httpx.AsyncClient(verify=False)  # noqa: S501
        config["http_client"] = http_client
        config["http_async_client"] = http_async_client

    # Create appropriate LLM instance
    if llm_type == "reasoning":
        return ChatDeepSeek(**config)
    return ChatOpenAI(**config)


def get_llm_by_type(llm_type: LLMType) -> ChatOpenAI | ChatDeepSeek:
    """Get LLM instance by type. Returns cached instance if available."""
    if llm_type in _llm_cache:
        return _llm_cache[llm_type]

    llm = _create_llm_instance(llm_type)
    _llm_cache[llm_type] = llm
    return llm


def get_configured_llm_models() -> dict[str, list[str]]:
    """Get all configured LLM models grouped by type.

    Returns:
        Dictionary mapping LLM type to list of configured model names.

    """
    configured_models: dict[str, list[str]] = {}

    for llm_type in get_args(LLMType):
        try:
            if llm_type == "basic":
                model_settings = settings.basic_model
            elif llm_type == "reasoning":
                model_settings = settings.reasoning_model
            elif llm_type == "vision":
                model_settings = settings.vision_model
            else:
                continue

            # Check if model is configured
            if model_settings.api_key and model_settings.model:
                # For reasoning model, also check base_url
                if llm_type == "reasoning" and not model_settings.base_url:
                    continue
                configured_models.setdefault(llm_type, []).append(model_settings.model)

        except (ValueError, AttributeError):
            # Skip if configuration is invalid
            continue

    return configured_models


def clear_llm_cache() -> None:
    """Clear the LLM cache. Useful for testing or when configuration changes."""
    global _llm_cache
    _llm_cache.clear()

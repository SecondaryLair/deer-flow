# Copyright (c) 2025 Bytedance Ltd. and/or its affiliates
# SPDX-License-Identifier: MIT
"""LLM management and configuration utilities."""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any, get_args

import httpx
from langchain_deepseek import ChatDeepSeek
from langchain_openai import ChatOpenAI

from src.config import load_yaml_config
from src.config.agents import LLMType

# Cache for LLM instances
_llm_cache: dict[LLMType, ChatOpenAI] = {}


def _get_config_file_path() -> str:
    """Get the path to the configuration file."""
    return str((Path(__file__).parent.parent.parent / "conf.yaml").resolve())


def _get_llm_type_config_keys() -> dict[str, str]:
    """Get mapping of LLM types to their configuration keys."""
    return {
        "reasoning": "REASONING_MODEL",
        "basic": "BASIC_MODEL",
        "vision": "VISION_MODEL",
    }


def _get_env_llm_conf(llm_type: str) -> dict[str, Any]:
    """Get LLM configuration from environment variables.
    Environment variables should follow the format: {LLM_TYPE}__{KEY}
    e.g., BASIC_MODEL__api_key, BASIC_MODEL__base_url.
    """
    prefix = f"{llm_type.upper()}_MODEL__"
    conf = {}
    for key, value in os.environ.items():
        if key.startswith(prefix):
            conf_key = key[len(prefix) :].lower()
            conf[conf_key] = value
    return conf


def _create_llm_use_conf(llm_type: LLMType, conf: dict[str, Any]) -> ChatOpenAI | ChatDeepSeek:
    """Create LLM instance using configuration."""
    llm_type_config_keys = _get_llm_type_config_keys()
    config_key = llm_type_config_keys.get(llm_type)

    if not config_key:
        msg = f"Unknown LLM type: {llm_type}"
        raise ValueError(msg)

    llm_conf = conf.get(config_key, {})
    if not isinstance(llm_conf, dict):
        msg = f"Invalid LLM configuration for {llm_type}: {llm_conf}"
        raise TypeError(msg)

    # Get configuration from environment variables
    env_conf = _get_env_llm_conf(llm_type)

    # Merge configurations, with environment variables taking precedence
    merged_conf = {**llm_conf, **env_conf}

    if not merged_conf:
        msg = f"No configuration found for LLM type: {llm_type}"
        raise ValueError(msg)

    if llm_type == "reasoning":
        merged_conf["api_base"] = merged_conf.pop("base_url", None)

    # Handle SSL verification settings
    verify_ssl = merged_conf.pop("verify_ssl", True)

    # Create custom HTTP client if SSL verification is disabled
    if not verify_ssl:
        http_client = httpx.Client(verify=False)  # noqa: S501
        http_async_client = httpx.AsyncClient(verify=False)  # noqa: S501
        merged_conf["http_client"] = http_client
        merged_conf["http_async_client"] = http_async_client

    return ChatOpenAI(**merged_conf) if llm_type != "reasoning" else ChatDeepSeek(**merged_conf)


def get_llm_by_type(
    llm_type: LLMType,
) -> ChatOpenAI | ChatDeepSeek:
    """Get LLM instance by type. Returns cached instance if available."""
    if llm_type in _llm_cache:
        return _llm_cache[llm_type]

    conf = load_yaml_config(_get_config_file_path())
    llm = _create_llm_use_conf(llm_type, conf)
    _llm_cache[llm_type] = llm
    return llm


def get_configured_llm_models() -> dict[str, list[str]]:
    """Get all configured LLM models grouped by type.

    Returns:
        Dictionary mapping LLM type to list of configured model names.

    """
    try:
        conf = load_yaml_config(_get_config_file_path())
        llm_type_config_keys = _get_llm_type_config_keys()

        configured_models: dict[str, list[str]] = {}

        for llm_type in get_args(LLMType):
            # Get configuration from YAML file
            config_key = llm_type_config_keys.get(llm_type, "")
            yaml_conf = conf.get(config_key, {}) if config_key else {}

            # Get configuration from environment variables
            env_conf = _get_env_llm_conf(llm_type)

            # Merge configurations, with environment variables taking precedence
            merged_conf = {**yaml_conf, **env_conf}

            # Check if model is configured
            model_name = merged_conf.get("model")
            if model_name:
                configured_models.setdefault(llm_type, []).append(model_name)

    except (FileNotFoundError, KeyError, ValueError):
        # Log error and return empty dict to avoid breaking the application
        return {}
    else:
        return configured_models

# Copyright (c) 2025 Bytedance Ltd. and/or its affiliates
# SPDX-License-Identifier: MIT
"""Configuration management for the application."""

from __future__ import annotations

import dataclasses
from dataclasses import field
from typing import Any

from deerflowx.libs.rag import Resource


@dataclasses.dataclass(kw_only=True)
class Configuration:
    """Configuration for the agent system"""

    # the mcp_settings is a dict of settings for the MCP servers
    mcp_settings: dict | None = None
    resources: list[Resource] = field(default_factory=list)
    max_step_num: int = 3
    max_search_results: int = 3
    max_plan_iterations: int = 1

    enable_deep_thinking: bool = False
    enable_background_investigation: bool = True
    auto_accepted_plan: bool = False
    enable_context_compression: bool = True
    max_context_tokens: int = 32000

    # Token management settings for observations compression
    max_observations_tokens: int = 45000
    compression_safety_margin: float = 0.8

    # Summarizer settings
    summarizer_chunk_size: int = 8000
    summarizer_chunk_overlap: int = 400
    summarizer_enable_second_pass: bool = True

    @classmethod
    def from_runnable_config(cls, config: dict | None = None) -> Configuration:
        """Create a Configuration object from a RunnableConfig object"""
        if config is None:
            config = {}
        if not isinstance(config, dict):
            msg = "config must be a dict"
            raise TypeError(msg)

        configurable = config.get("configurable", {})

        # Helper function to get value with default fallback for None/falsy values
        def get_with_default(key: str, default: Any):
            value = configurable.get(key, default)
            # Use default if value is None or falsy for numeric/string types
            if value is None or (isinstance(default, (int, float, str)) and not value):
                return default
            return value

        return Configuration(
            mcp_settings=configurable.get("mcp_settings"),
            resources=configurable.get("resources", []),
            max_step_num=get_with_default("max_step_num", 3),
            max_search_results=get_with_default("max_search_results", 3),
            max_plan_iterations=get_with_default("max_plan_iterations", 1),
            enable_deep_thinking=configurable.get("enable_deep_thinking", False),
            enable_background_investigation=configurable.get("enable_background_investigation", True),
            auto_accepted_plan=configurable.get("auto_accepted_plan", False),
            enable_context_compression=configurable.get("enable_context_compression", True),
            max_context_tokens=get_with_default("max_context_tokens", 32000),
            max_observations_tokens=get_with_default("max_observations_tokens", 45000),
            compression_safety_margin=get_with_default("compression_safety_margin", 0.8),
            summarizer_chunk_size=get_with_default("summarizer_chunk_size", 8000),
            summarizer_chunk_overlap=get_with_default("summarizer_chunk_overlap", 400),
            summarizer_enable_second_pass=configurable.get("summarizer_enable_second_pass", True),
        )

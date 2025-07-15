# Copyright (c) 2025 Bytedance Ltd. and/or its affiliates
# SPDX-License-Identifier: MIT
"""Configuration management for the application."""

from __future__ import annotations

import os
from dataclasses import dataclass, field, fields
from typing import Any

from langchain_core.runnables import RunnableConfig

from deerflowx.config.report_style import ReportStyle
from deerflowx.libs.rag.retriever import Resource


@dataclass(kw_only=True)
class Configuration:
    """The configurable fields."""

    resources: list[Resource] = field(default_factory=list)
    max_step_num: int = 3
    max_search_results: int = 3
    max_plan_iterations: int = 1

    enable_deep_thinking: bool = False
    enable_background_investigation: bool = True
    auto_accepted_plan: bool = False

    report_style: str = ReportStyle.ACADEMIC.value
    mcp_settings: dict[str, Any] | None = None

    max_observations_tokens: int = 45000
    compression_safety_margin: float = 0.8
    summarizer_chunk_size: int = 8000
    summarizer_chunk_overlap: int = 400
    summarizer_enable_second_pass: bool = True

    @classmethod
    def from_runnable_config(cls, config: RunnableConfig | None = None) -> Configuration:
        """Create a Configuration instance from a RunnableConfig."""
        configurable = config["configurable"] if config and "configurable" in config else {}
        values: dict[str, Any] = {
            f.name: os.environ.get(f.name.upper(), configurable.get(f.name)) for f in fields(cls) if f.init
        }
        return cls(**{k: v for k, v in values.items() if v})

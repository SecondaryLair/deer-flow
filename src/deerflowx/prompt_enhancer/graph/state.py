# Copyright (c) 2025 Bytedance Ltd. and/or its affiliates
# SPDX-License-Identifier: MIT

from typing import TypedDict

from deerflowx.config.report_style import ReportStyle


class PromptEnhancerState(TypedDict):
    """State for the prompt enhancer workflow."""

    prompt: str  # Original prompt to enhance
    context: str | None  # Additional context
    report_style: ReportStyle | None  # Report style preference
    output: str | None  # Enhanced prompt result

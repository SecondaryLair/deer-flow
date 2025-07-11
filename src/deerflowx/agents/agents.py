# Copyright (c) 2025 Bytedance Ltd. and/or its affiliates
# SPDX-License-Identifier: MIT
"""Agent creation utilities for building reactive agents."""

from typing import Any

from langgraph.graph.graph import CompiledGraph
from langgraph.prebuilt import create_react_agent

from deerflowx.config.agents import AGENT_LLM_MAP
from deerflowx.llms.llm import get_llm_by_type
from deerflowx.prompts import apply_prompt_template


# Create agents using configured LLM types
def create_agent(
    agent_name: str,
    agent_type: str,
    tools: list[Any],
    prompt_template: str,
) -> CompiledGraph:
    """Factory function to create agents with consistent configuration."""
    return create_react_agent(
        name=agent_name,
        model=get_llm_by_type(AGENT_LLM_MAP[agent_type]),
        tools=tools,
        prompt=lambda state: apply_prompt_template(prompt_template, state),
    )

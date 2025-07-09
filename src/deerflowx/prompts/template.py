# Copyright (c) 2025 Bytedance Ltd. and/or its affiliates
# SPDX-License-Identifier: MIT
"""Prompt template utilities and management."""

import dataclasses
from datetime import UTC, datetime
from pathlib import Path

from jinja2 import Environment, FileSystemLoader, TemplateNotFound, TemplateSyntaxError, select_autoescape
from langgraph.prebuilt.chat_agent_executor import AgentState

from deerflowx.config.configuration import Configuration

# Initialize Jinja2 environment
env = Environment(
    loader=FileSystemLoader(Path(__file__).parent),
    autoescape=select_autoescape(),
    trim_blocks=True,
    lstrip_blocks=True,
)


def get_prompt_template(prompt_name: str) -> str:
    """Load and return a prompt template using Jinja2.

    Args:
        prompt_name: Name of the prompt template file (without .md extension)

    Returns:
        The template string with proper variable substitution syntax

    """
    try:
        template = env.get_template(f"{prompt_name}.md")
        return template.render()
    except (FileNotFoundError, TemplateNotFound, TemplateSyntaxError) as e:
        msg = f"Error loading template {prompt_name}: {e}"
        raise ValueError(msg) from e


def apply_prompt_template(prompt_name: str, state: AgentState, configurable: Configuration = None) -> list:
    """Apply template variables to a prompt template and return formatted messages.

    Args:
        prompt_name: Name of the prompt template to use
        state: Current agent state containing variables to substitute

    Returns:
        List of messages with the system prompt as the first message

    """
    # Convert state to dict for template rendering
    state_vars = {
        "CURRENT_TIME": datetime.now(UTC).strftime("%a %b %d %Y %H:%M:%S %z"),
        **state,
    }

    # Add configurable variables
    if configurable:
        state_vars.update(dataclasses.asdict(configurable))

    try:
        template = env.get_template(f"{prompt_name}.md")
        system_prompt = template.render(**state_vars)
        return [{"role": "system", "content": system_prompt}] + state["messages"]
    except (TemplateNotFound, TemplateSyntaxError, TypeError, KeyError) as e:
        msg = f"Error applying template {prompt_name}: {e}"
        raise ValueError(msg) from e

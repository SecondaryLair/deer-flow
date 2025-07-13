# Copyright (c) 2025 Bytedance Ltd. and/or its affiliates
# SPDX-License-Identifier: MIT

import logging
from typing import Any

from langchain_core.messages import HumanMessage
from langchain_core.runnables import RunnableConfig

from deerflowx.config.agents import AGENT_LLM_MAP
from deerflowx.config.configuration import Configuration
from deerflowx.graph.types import State
from deerflowx.llms.llm import get_llm_by_type
from deerflowx.prompts.template import apply_prompt_template
from deerflowx.utils.node_base import NodeBase

logger = logging.getLogger(__name__)


async def reporter_node(state: State, config: RunnableConfig) -> dict[str, Any]:
    """Reporter node that write a final report."""
    logger.info("Reporter write final report")
    configurable = Configuration.from_runnable_config(config)
    current_plan = state.get("current_plan")
    input_ = {
        "messages": [
            HumanMessage(
                f"# Research Requirements\n\n## Task\n\n{current_plan.title}\n\n"
                f"## Description\n\n{current_plan.thought}",
            ),
        ],
        "locale": state.get("locale", "en-US"),
    }
    invoke_messages = apply_prompt_template("reporter", input_, configurable)
    observations = state.get("observations", [])

    # Add a reminder about the new report format, citation style, and table usage
    invoke_messages.append(
        HumanMessage(
            content=(
                "IMPORTANT: Structure your report according to the format in the prompt. "
                "Remember to include:\n\n"
                "1. Key Points - A bulleted list of the most important findings\n"
                "2. Overview - A brief introduction to the topic\n"
                "3. Detailed Analysis - Organized into logical sections\n"
                "4. Survey Note (optional) - For more comprehensive reports\n"
                "5. Key Citations - List all references at the end\n\n"
                "For citations, DO NOT include inline citations in the text. Instead, "
                "place all citations in the 'Key Citations' section at the end using the "
                "format: `- [Source Title](URL)`. Include an empty line between each "
                "citation for better readability.\n\n"
                "PRIORITIZE USING MARKDOWN TABLES for data presentation and comparison. "
                "Use tables whenever presenting comparative data, statistics, features, "
                "or options. Structure tables with clear headers and aligned columns. "
                "Example table format:\n\n"
                "| Feature | Description | Pros | Cons |\n"
                "|---------|-------------|------|------|\n"
                "| Feature 1 | Description 1 | Pros 1 | Cons 1 |\n"
                "| Feature 2 | Description 2 | Pros 2 | Cons 2 |"
            ),
            name="system",
        ),
    )

    for observation in observations:
        invoke_messages.append(
            HumanMessage(
                content=f"Below are some observations for the research task:\n\n{observation}",
                name="observation",
            ),
        )
    logger.debug(f"Current invoke messages: {invoke_messages}")
    response = get_llm_by_type(AGENT_LLM_MAP["reporter"]).invoke(invoke_messages)
    response_content = response.content
    logger.info(f"reporter response: {response_content}")

    return {"final_report": response_content}


class ReporterNode(NodeBase):
    """Reporter node that write a final report."""

    @classmethod
    def name(cls) -> str:
        return "reporter"

    @classmethod
    async def action(cls, state: State, config: RunnableConfig) -> dict[str, Any]:
        """Reporter node that write a final report."""
        return await reporter_node(state, config)

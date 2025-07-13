# Copyright (c) 2025 Bytedance Ltd. and/or its affiliates
# SPDX-License-Identifier: MIT

import logging
from typing import Any

from langchain.schema import HumanMessage

from deerflowx.config.agents import AGENT_LLM_MAP
from deerflowx.graphs.prompt_enhancer.graph.state import PromptEnhancerState
from deerflowx.utils.llms.llm import get_llm_by_type
from deerflowx.utils.node_base import NodeBase

logger = logging.getLogger(__name__)


async def prompt_enhancer_node(state: PromptEnhancerState) -> dict[str, Any]:
    """Node that enhances user prompts using AI analysis."""
    logger.info("Enhancing user prompt...")

    model = get_llm_by_type(AGENT_LLM_MAP["prompt_enhancer"])

    try:
        # Create messages with context if provided
        context_info = ""
        if state.get("context"):
            context_info = f"\n\nAdditional context: {state['context']}"

        prompt_message = f"Please enhance this prompt:{context_info}\n\nOriginal prompt: {state['prompt']}"

        # Get the response from the model
        response = model.invoke([HumanMessage(content=prompt_message)])

        # Clean up the response - remove any extra formatting or comments
        enhanced_prompt = response.content if hasattr(response, "content") else str(response)

        # Ensure we have a string
        if not isinstance(enhanced_prompt, str):
            enhanced_prompt = str(enhanced_prompt)

        # Remove common prefixes that might be added by the model
        prefixes_to_remove = [
            "Enhanced Prompt:",
            "Enhanced prompt:",
            "Here's the enhanced prompt:",
            "Here is the enhanced prompt:",
            "**Enhanced Prompt**:",
            "**Enhanced prompt**:",
        ]

        for prefix in prefixes_to_remove:
            if enhanced_prompt.startswith(prefix):
                enhanced_prompt = enhanced_prompt[len(prefix) :].strip()
                break

        # Always strip whitespace from the final result
        enhanced_prompt = enhanced_prompt.strip()

        logger.info(f"Enhanced prompt: {enhanced_prompt}")

    except Exception:
        logger.exception("Error enhancing prompt ")
        # Return original prompt if enhancement fails
        return {"enhanced_prompt": state["prompt"]}
    else:
        return {"enhanced_prompt": enhanced_prompt}


class PromptEnhancerNode(NodeBase):
    """Prompt enhancer node."""

    @classmethod
    def name(cls) -> str:
        return "enhancer"

    @classmethod
    async def action(cls, state: PromptEnhancerState) -> Any:
        """Prompt enhancer node."""
        return await prompt_enhancer_node(state)

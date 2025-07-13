# Copyright (c) 2025 Bytedance Ltd. and/or its affiliates
# SPDX-License-Identifier: MIT

import logging
from typing import Any

from langchain.schema import HumanMessage, SystemMessage

from deerflowx.config.agents import AGENT_LLM_MAP
from deerflowx.graphs.prose.graph.state import ProseState
from deerflowx.prompts.template import get_prompt_template
from deerflowx.utils.llms.llm import get_llm_by_type
from deerflowx.utils.node_base import NodeBase

logger = logging.getLogger(__name__)


async def prose_longer_node(state: ProseState) -> dict[str, Any]:
    logger.info("Generating prose longer content...")
    model = get_llm_by_type(AGENT_LLM_MAP["prose_writer"])
    prose_content = model.invoke(
        [
            SystemMessage(content=get_prompt_template("prose/prose_longer")),
            HumanMessage(content=f"The existing text is: {state['content']}"),
        ],
    )
    logger.info(f"prose_content: {prose_content}")
    return {"output": prose_content.content}


class ProseLongerNode(NodeBase):
    """Prose longer node."""

    @classmethod
    def name(cls) -> str:
        return "prose_longer"

    @classmethod
    async def action(cls, state: ProseState) -> Any:
        """Prose longer node."""
        return await prose_longer_node(state)

# Copyright (c) 2025 Bytedance Ltd. and/or its affiliates
# SPDX-License-Identifier: MIT

import logging
from typing import Literal

from langchain_core.runnables import RunnableConfig
from langgraph.types import Command

from deerflowx.config.configuration import Configuration
from deerflowx.graphs.research.graph.nodes._executor import _setup_and_execute_agent_step
from deerflowx.graphs.research.graph.types import State
from deerflowx.tools import (
    crawl_tool,
    get_retriever_tool,
    get_web_search_tool,
)
from deerflowx.utils.node_base import NodeBase

logger = logging.getLogger(__name__)


async def researcher_node(state: State, config: RunnableConfig) -> Command[Literal["research_team"]]:
    """Researcher node that do research."""
    logger.info("Researcher node is researching.")
    configurable = Configuration.from_runnable_config(config)
    tools = [get_web_search_tool(configurable.max_search_results), crawl_tool]
    retriever_tool = get_retriever_tool(state.get("resources", []))
    if retriever_tool:
        tools.insert(0, retriever_tool)
    logger.info(f"Researcher tools: {tools}")
    return await _setup_and_execute_agent_step(
        state,
        config,
        "researcher",
        tools,
    )


class ResearcherNode(NodeBase):
    """Researcher node that do research."""

    @classmethod
    def name(cls) -> str:
        return "researcher"

    @classmethod
    async def action(cls, state: State, config: RunnableConfig) -> Command[Literal["research_team"]]:
        """Researcher node that do research."""
        return await researcher_node(state, config)

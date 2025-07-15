# Copyright (c) 2025 Bytedance Ltd. and/or its affiliates
# SPDX-License-Identifier: MIT

import json
import logging
from typing import Any

from langchain_core.runnables import RunnableConfig

from deerflowx.config import SELECTED_SEARCH_ENGINE, SearchEngine
from deerflowx.config.configuration import Configuration
from deerflowx.graphs.research.graph.state import State
from deerflowx.tools import (
    get_web_search_tool,
)
from deerflowx.tools.search import LoggedTavilySearch
from deerflowx.utils.node_base import NodeBase

logger = logging.getLogger(__name__)


async def background_investigation_node(state: State, config: RunnableConfig) -> dict[str, Any]:
    logger.info("background investigation node is running.")
    configurable = Configuration.from_runnable_config(config)
    query = state.get("research_topic")
    background_investigation_results = None
    if SearchEngine.TAVILY.value == SELECTED_SEARCH_ENGINE:
        searched_content = await LoggedTavilySearch(max_results=configurable.max_search_results).ainvoke(query)
        if isinstance(searched_content, list):
            background_investigation_results = [f"## {elem['title']}\n\n{elem['content']}" for elem in searched_content]
            return {"background_investigation_results": "\n\n".join(background_investigation_results)}
        logger.error(f"Tavily search returned malformed response: {searched_content}")
    else:
        background_investigation_results = await get_web_search_tool(configurable.max_search_results).ainvoke(query)
    return {"background_investigation_results": json.dumps(background_investigation_results, ensure_ascii=False)}


class BackgroundInvestigationNode(NodeBase):
    """Background investigation node that performs initial research."""

    @classmethod
    def name(cls) -> str:
        return "background_investigator"

    @classmethod
    async def action(cls, state: State, config: RunnableConfig) -> dict[str, Any]:
        """Background investigation node that performs initial research."""
        return await background_investigation_node(state, config)

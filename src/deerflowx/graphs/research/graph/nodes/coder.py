# Copyright (c) 2025 Bytedance Ltd. and/or its affiliates
# SPDX-License-Identifier: MIT

import logging
from typing import Literal

from langchain_core.runnables import RunnableConfig
from langgraph.types import Command

from deerflowx.graphs.research.graph.nodes._executor import _setup_and_execute_agent_step
from deerflowx.graphs.research.graph.state import State
from deerflowx.tools import (
    python_repl_tool,
)
from deerflowx.utils.node_base import NodeBase

logger = logging.getLogger(__name__)


async def coder_node(state: State, config: RunnableConfig) -> Command[Literal["research_team"]]:
    """Coder node that do code analysis."""
    logger.info("Coder node is coding.")
    return await _setup_and_execute_agent_step(
        state,
        config,
        "coder",
        [python_repl_tool],
    )


class CoderNode(NodeBase):
    """Coder node that do code analysis."""

    @classmethod
    def name(cls) -> str:
        return "coder"

    @classmethod
    async def action(cls, state: State, config: RunnableConfig) -> Command[Literal["research_team"]]:
        """Coder node that do code analysis."""
        return await coder_node(state, config)

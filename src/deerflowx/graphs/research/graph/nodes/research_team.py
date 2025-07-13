# Copyright (c) 2025 Bytedance Ltd. and/or its affiliates
# SPDX-License-Identifier: MIT

import logging
from typing import Any

from deerflowx.graphs.research.graph.types import State
from deerflowx.utils.node_base import NodeBase

logger = logging.getLogger(__name__)


async def research_team_node(_state: State) -> dict[str, Any]:
    """Research team node that collaborates on tasks."""
    logger.info("Research team is collaborating on tasks.")
    return {}


class ResearchTeamNode(NodeBase):
    """Research team node that collaborates on tasks."""

    @classmethod
    def name(cls) -> str:
        return "research_team"

    @classmethod
    async def action(cls, state: State) -> dict[str, Any]:
        """Research team node that collaborates on tasks."""
        return await research_team_node(state)

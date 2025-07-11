# Copyright (c) 2025 Bytedance Ltd. and/or its affiliates
# SPDX-License-Identifier: MIT

import asyncio
import logging

from langgraph.graph import END, START, StateGraph
from langgraph.graph.state import CompiledStateGraph

from deerflowx.prose.graph.prose_continue_node import prose_continue_node
from deerflowx.prose.graph.prose_fix_node import prose_fix_node
from deerflowx.prose.graph.prose_improve_node import prose_improve_node
from deerflowx.prose.graph.prose_longer_node import prose_longer_node
from deerflowx.prose.graph.prose_shorter_node import prose_shorter_node
from deerflowx.prose.graph.prose_zap_node import prose_zap_node
from deerflowx.prose.graph.state import ProseState


def optional_node(state: ProseState) -> str:
    return state["option"]


def build_graph() -> CompiledStateGraph:
    """Build and return the prose workflow graph."""
    # build state graph
    builder = StateGraph(ProseState)
    builder.add_node("prose_continue", prose_continue_node)
    builder.add_node("prose_improve", prose_improve_node)
    builder.add_node("prose_shorter", prose_shorter_node)
    builder.add_node("prose_longer", prose_longer_node)
    builder.add_node("prose_fix", prose_fix_node)
    builder.add_node("prose_zap", prose_zap_node)
    builder.add_conditional_edges(
        START,
        optional_node,
        {
            "continue": "prose_continue",
            "improve": "prose_improve",
            "shorter": "prose_shorter",
            "longer": "prose_longer",
            "fix": "prose_fix",
            "zap": "prose_zap",
        },
        END,
    )
    return builder.compile()


async def _test_workflow() -> None:
    workflow = build_graph()
    events = workflow.astream(
        {
            "content": "The weather in Beijing is sunny",
            "option": "continue",
        },
        stream_mode="messages",
        subgraphs=True,
    )
    async for _node, event in events:
        event[0]


if __name__ == "__main__":
    from dotenv import load_dotenv

    load_dotenv()
    logging.basicConfig(level=logging.INFO)
    asyncio.run(_test_workflow())

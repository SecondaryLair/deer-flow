# Copyright (c) 2025 Bytedance Ltd. and/or its affiliates
# SPDX-License-Identifier: MIT

import asyncio
import logging

from langgraph.graph import END, START, StateGraph
from langgraph.graph.state import CompiledStateGraph

from deerflowx.graphs.prose.graph.prose_continue_node import ProseContinueNode
from deerflowx.graphs.prose.graph.prose_fix_node import ProseFixNode
from deerflowx.graphs.prose.graph.prose_improve_node import ProseImproveNode
from deerflowx.graphs.prose.graph.prose_longer_node import ProseLongerNode
from deerflowx.graphs.prose.graph.prose_shorter_node import ProseShorterNode
from deerflowx.graphs.prose.graph.prose_zap_node import ProseZapNode
from deerflowx.graphs.prose.graph.state import ProseState


def optional_node(state: ProseState) -> str:
    return state["option"]


def build_graph() -> CompiledStateGraph:
    """Build and return the prose workflow graph."""
    # build state graph
    builder = StateGraph(ProseState)
    builder.add_node(ProseContinueNode.name(), ProseContinueNode.action)
    builder.add_node(ProseImproveNode.name(), ProseImproveNode.action)
    builder.add_node(ProseShorterNode.name(), ProseShorterNode.action)
    builder.add_node(ProseLongerNode.name(), ProseLongerNode.action)
    builder.add_node(ProseFixNode.name(), ProseFixNode.action)
    builder.add_node(ProseZapNode.name(), ProseZapNode.action)
    builder.add_conditional_edges(
        START,
        optional_node,
        {
            "continue": ProseContinueNode.name(),
            "improve": ProseImproveNode.name(),
            "shorter": ProseShorterNode.name(),
            "longer": ProseLongerNode.name(),
            "fix": ProseFixNode.name(),
            "zap": ProseZapNode.name(),
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


def example_test_workflow() -> None:
    from dotenv import load_dotenv  # noqa: PLC0415

    load_dotenv()
    logging.basicConfig(level=logging.INFO)
    asyncio.run(_test_workflow())


def example_get_mermaid_graph() -> None:
    print(build_graph().get_graph(xray=True).draw_mermaid())  # noqa: T201


if __name__ == "__main__":
    example_get_mermaid_graph()

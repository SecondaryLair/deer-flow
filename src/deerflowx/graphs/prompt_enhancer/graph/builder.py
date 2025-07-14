# Copyright (c) 2025 Bytedance Ltd. and/or its affiliates
# SPDX-License-Identifier: MIT

from langgraph.graph import StateGraph
from langgraph.graph.graph import CompiledGraph

from deerflowx.graphs.prompt_enhancer.graph.enhancer_node import PromptEnhancerNode
from deerflowx.graphs.prompt_enhancer.graph.state import PromptEnhancerState


def build_graph() -> CompiledGraph:
    """Build and return the prompt enhancer workflow graph."""
    # Build state graph
    builder = StateGraph(PromptEnhancerState)

    # Add the enhancer node
    builder.add_node(PromptEnhancerNode.name(), PromptEnhancerNode.action)

    # Set entry point
    builder.set_entry_point(PromptEnhancerNode.name())

    # Set finish point
    builder.set_finish_point(PromptEnhancerNode.name())

    # Compile and return the graph
    return builder.compile()


def example_get_mermaid_graph() -> None:
    print(build_graph().get_graph(xray=True).draw_mermaid())  # noqa: T201


if __name__ == "__main__":
    example_get_mermaid_graph()

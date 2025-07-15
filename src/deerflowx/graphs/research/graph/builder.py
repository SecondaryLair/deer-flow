# Copyright (c) 2025 Bytedance Ltd. and/or its affiliates
# SPDX-License-Identifier: MIT

import logging

from langgraph.checkpoint.memory import MemorySaver
from langgraph.graph import END, START, StateGraph
from langgraph.graph.state import CompiledStateGraph

from deerflowx.graphs.research.graph.nodes.background_investigation import BackgroundInvestigationNode
from deerflowx.graphs.research.graph.nodes.coder import CoderNode
from deerflowx.graphs.research.graph.nodes.coordinator import CoordinatorNode
from deerflowx.graphs.research.graph.nodes.human_feedback import HumanFeedbackNode
from deerflowx.graphs.research.graph.nodes.planner import PlannerNode
from deerflowx.graphs.research.graph.nodes.reporter import ReporterNode
from deerflowx.graphs.research.graph.nodes.research_team import ResearchTeamNode
from deerflowx.graphs.research.graph.nodes.researcher import ResearcherNode
from deerflowx.graphs.research.graph.nodes.summarizer import (
    MapSummarizeChunkNode,
    ReduceSummariesNode,
    SummarizerNode,
)
from deerflowx.graphs.research.graph.nodes.tokens_evaluator import TokensEvaluatorNode
from deerflowx.graphs.research.graph.state import State
from deerflowx.prompts.planner_model import StepType


def continue_to_running_research_team(state: State) -> str:
    current_plan = state.get("current_plan")
    if not current_plan or isinstance(current_plan, str):
        return "planner"

    if not current_plan.steps:
        return "planner"

    if all(step.execution_res for step in current_plan.steps):
        return "tokens_evaluator"  # 研究完成后,先进行token估算
    for step in current_plan.steps:
        if not step.execution_res:
            break
    if step.step_type and step.step_type == StepType.RESEARCH:
        return "researcher"
    if step.step_type and step.step_type == StepType.PROCESSING:
        return "coder"
    return "planner"


def route_after_token_estimation(state: State) -> str:
    """根据token估算结果和配置决定路由."""
    logger = logging.getLogger(__name__)

    try:
        compression_decision = state.get("compression_decision", "")

        if compression_decision == "direct_to_reporter":
            return "reporter"
        if compression_decision == "compress_first":
            return "summarizer"

        logger.warning("No compression decision found, defaulting to reporter")
    except Exception as e:
        logger.exception(f"Error in token estimation routing: {e}")
        return "reporter"  # 安全回退
    else:
        return "reporter"


def route_after_summarization(state: State) -> str:
    """摘要完成后路由到reporter."""
    logger = logging.getLogger(__name__)

    try:
        summarized_observations = state.get("summarized_observations", "")
        if not summarized_observations:
            logger.warning(
                "Summarization completed but no summarized_observations found, proceeding to reporter anyway"
            )
        else:
            logger.info(f"Summarization completed, content length: {len(summarized_observations)} chars")

    except Exception as e:
        logger.exception(f"Error in summarization routing: {e}")
        return "reporter"  # 安全回退
    else:
        return "reporter"


def _build_base_graph() -> StateGraph:
    """Build and return the base state graph with all nodes and edges."""
    builder = StateGraph(State)
    builder.add_edge(START, CoordinatorNode.name())

    builder.add_node(CoordinatorNode.name(), CoordinatorNode.action)
    builder.add_node(BackgroundInvestigationNode.name(), BackgroundInvestigationNode.action)
    builder.add_node(PlannerNode.name(), PlannerNode.action)
    builder.add_node(ReporterNode.name(), ReporterNode.action)
    builder.add_node(ResearchTeamNode.name(), ResearchTeamNode.action)
    builder.add_node(ResearcherNode.name(), ResearcherNode.action)
    builder.add_node(CoderNode.name(), CoderNode.action)
    builder.add_node(HumanFeedbackNode.name(), HumanFeedbackNode.action)

    builder.add_node(TokensEvaluatorNode.name(), TokensEvaluatorNode.action)
    builder.add_node(SummarizerNode.name(), SummarizerNode.action)
    builder.add_node(MapSummarizeChunkNode.name(), MapSummarizeChunkNode.action)
    builder.add_node(ReduceSummariesNode.name(), ReduceSummariesNode.action)

    builder.add_edge(BackgroundInvestigationNode.name(), PlannerNode.name())

    builder.add_conditional_edges(
        ResearchTeamNode.name(),
        continue_to_running_research_team,
        [PlannerNode.name(), ResearcherNode.name(), CoderNode.name(), TokensEvaluatorNode.name()],
    )

    builder.add_conditional_edges(
        TokensEvaluatorNode.name(),
        route_after_token_estimation,
        [ReporterNode.name(), SummarizerNode.name()],
    )

    builder.add_edge(SummarizerNode.name(), MapSummarizeChunkNode.name())
    builder.add_edge(MapSummarizeChunkNode.name(), ReduceSummariesNode.name())

    builder.add_edge(ReduceSummariesNode.name(), ReporterNode.name())

    builder.add_edge(ReporterNode.name(), END)

    return builder


def build_graph_with_memory() -> CompiledStateGraph:
    """Build and return the agent workflow graph with memory."""
    # use persistent memory to save conversation history
    # NOTE: Future enhancement - add SQLite/PostgreSQL compatibility
    memory = MemorySaver()

    # build state graph
    builder = _build_base_graph()
    return builder.compile(checkpointer=memory)


def build_graph() -> CompiledStateGraph:
    """Build and return the agent workflow graph without memory."""
    # build state graph
    builder = _build_base_graph()
    return builder.compile()


graph = build_graph()


def example_get_mermaid_graph() -> None:
    print(build_graph().get_graph(xray=True).draw_mermaid())  # noqa: T201


if __name__ == "__main__":
    example_get_mermaid_graph()

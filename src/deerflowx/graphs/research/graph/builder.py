# Copyright (c) 2025 Bytedance Ltd. and/or its affiliates
# SPDX-License-Identifier: MIT


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
from deerflowx.prompts.planner_model import StepType

from .types import State


def continue_to_running_research_team(state: State) -> str:
    current_plan = state.get("current_plan")
    if not current_plan or isinstance(current_plan, str):
        return "planner"
    if all(step.execution_res for step in current_plan.steps):
        return "planner"
    for step in current_plan.steps:
        if not step.execution_res:
            break
    if step.step_type and step.step_type == StepType.RESEARCH:
        return "researcher"
    if step.step_type and step.step_type == StepType.PROCESSING:
        return "coder"
    return "planner"


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
    builder.add_edge(BackgroundInvestigationNode.name(), PlannerNode.name())
    builder.add_conditional_edges(
        ResearchTeamNode.name(),
        continue_to_running_research_team,
        [PlannerNode.name(), ResearcherNode.name(), CoderNode.name()],
    )
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

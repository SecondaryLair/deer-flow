# Copyright (c) 2025 Bytedance Ltd. and/or its affiliates
# SPDX-License-Identifier: MIT


from typing import Annotated, NotRequired, TypedDict

from langchain_core.messages import AnyMessage
from langgraph.graph import add_messages

from deerflowx.libs.rag import Resource
from deerflowx.prompts.planner_model import Plan


class State(TypedDict):
    """State for the agent system"""

    messages: Annotated[list[AnyMessage], add_messages]

    auto_accepted_plan: bool
    enable_background_investigation: bool
    locale: str
    research_topic: str
    observations: list[str]
    resources: list[Resource]
    plan_iterations: int
    current_plan: Plan | str
    final_report: str
    background_investigation_results: str

    compression_decision: NotRequired[str]
    estimated_tokens: NotRequired[int]
    decision_reason: NotRequired[str]
    summarized_observations: NotRequired[str]

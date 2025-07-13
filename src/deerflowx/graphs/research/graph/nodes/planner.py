# Copyright (c) 2025 Bytedance Ltd. and/or its affiliates
# SPDX-License-Identifier: MIT

import json
import logging
from typing import Literal

from langchain_core.messages import AIMessage
from langchain_core.runnables import RunnableConfig
from langgraph.types import Command

from deerflowx.config.agents import AGENT_LLM_MAP
from deerflowx.config.configuration import Configuration
from deerflowx.graphs.research.graph.types import State
from deerflowx.prompts.planner_model import Plan
from deerflowx.prompts.template import apply_prompt_template
from deerflowx.utils.json_utils import repair_json_output
from deerflowx.utils.llms.llm import get_llm_by_type
from deerflowx.utils.node_base import NodeBase

logger = logging.getLogger(__name__)


async def planner_node(state: State, config: RunnableConfig) -> Command[Literal["human_feedback", "reporter"]]:
    """Planner node that generate the full plan."""
    logger.info("Planner generating full plan")
    configurable = Configuration.from_runnable_config(config)
    plan_iterations = state["plan_iterations"] if state.get("plan_iterations", 0) else 0
    messages = apply_prompt_template("planner", state, configurable)

    if state.get("enable_background_investigation") and state.get("background_investigation_results"):
        messages += [
            {
                "role": "user",
                "content": (
                    "background investigation results of user query:\n"
                    + state["background_investigation_results"]
                    + "\n"
                ),
            },
        ]

    if configurable.enable_deep_thinking:
        llm = get_llm_by_type("reasoning")
    elif AGENT_LLM_MAP["planner"] == "basic":
        llm = get_llm_by_type("basic").with_structured_output(
            Plan,
            method="json_mode",
        )
    else:
        llm = get_llm_by_type(AGENT_LLM_MAP["planner"])

    # if the plan iterations is greater than the max plan iterations, return the reporter node
    if plan_iterations >= configurable.max_plan_iterations:
        return Command(goto="reporter")

    full_response = ""
    if AGENT_LLM_MAP["planner"] == "basic" and not configurable.enable_deep_thinking:
        response = await llm.ainvoke(messages)
        full_response = response.model_dump_json(indent=4, exclude_none=True)
    else:
        # Use async streaming for better performance
        response_stream = llm.astream(messages)
        async for chunk in response_stream:
            full_response += chunk.content

    logger.debug(f"Current state messages: {state['messages']}")
    logger.info(f"Planner response: {full_response}")

    try:
        curr_plan = json.loads(repair_json_output(full_response))
    except json.JSONDecodeError:
        logger.warning("Planner response is not a valid JSON")
        if plan_iterations > 0:
            return Command(goto="reporter")
        return Command(goto="__end__")
    if curr_plan.get("has_enough_context"):
        logger.info("Planner response has enough context.")
        new_plan = Plan.model_validate(curr_plan)
        return Command(
            update={
                "messages": [AIMessage(content=full_response, name="planner")],
                "current_plan": new_plan,
            },
            goto="reporter",
        )
    return Command(
        update={
            "messages": [AIMessage(content=full_response, name="planner")],
            "current_plan": full_response,
        },
        goto="human_feedback",
    )


class PlannerNode(NodeBase):
    """Planner node that generate the full plan."""

    @classmethod
    def name(cls) -> str:
        return "planner"

    @classmethod
    async def action(cls, state: State, config: RunnableConfig) -> Command[Literal["human_feedback", "reporter"]]:
        """Planner node that generate the full plan."""
        return await planner_node(state, config)

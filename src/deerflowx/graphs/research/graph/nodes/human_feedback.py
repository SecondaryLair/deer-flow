# Copyright (c) 2025 Bytedance Ltd. and/or its affiliates
# SPDX-License-Identifier: MIT

import json
import logging
from typing import Literal

from langchain_core.messages import HumanMessage
from langgraph.types import Command, interrupt

from deerflowx.graphs.research.graph.state import State
from deerflowx.prompts.planner_model import Plan
from deerflowx.utils.json_utils import repair_json_output
from deerflowx.utils.node_base import NodeBase

logger = logging.getLogger(__name__)


async def human_feedback_node(
    state: State,
) -> Command[Literal["planner", "research_team", "reporter", "__end__"]]:
    current_plan = state.get("current_plan", "")
    # check if the plan is auto accepted
    auto_accepted_plan = state.get("auto_accepted_plan", False)
    if not auto_accepted_plan:
        feedback = interrupt("Please Review the Plan.")

        # if the feedback is not accepted, return the planner node
        if feedback and str(feedback).upper().startswith("[EDIT_PLAN]"):
            return Command(
                update={
                    "messages": [
                        HumanMessage(content=feedback, name="feedback"),
                    ],
                },
                goto="planner",
            )
        if feedback and str(feedback).upper().startswith("[ACCEPTED]"):
            logger.info("Plan is accepted by user.")
        else:
            msg = f"Interrupt value of {feedback} is not supported."
            raise TypeError(msg)

    plan_iterations = state["plan_iterations"] if state.get("plan_iterations", 0) else 0
    goto = "research_team"
    try:
        if isinstance(current_plan, str):
            current_plan_str = repair_json_output(current_plan)
        else:
            current_plan_str = (
                current_plan.model_dump_json() if hasattr(current_plan, "model_dump_json") else str(current_plan)
            )

        # increment the plan iterations
        plan_iterations += 1
        # parse the plan
        new_plan = json.loads(current_plan_str)

        has_research_steps = new_plan.get("steps") and any(
            step.get("need_search", False) or step.get("step_type") == "research" for step in new_plan.get("steps", [])
        )

        if has_research_steps:
            logger.info(f"Plan contains {len(new_plan.get('steps', []))} steps, proceeding to research team")
            goto = "research_team"
        elif new_plan["has_enough_context"]:
            logger.info("Plan has enough context and no research steps, proceeding directly to reporter")
            goto = "reporter"
        else:
            goto = "research_team"
    except json.JSONDecodeError:
        logger.warning("Planner response is not a valid JSON")
        if plan_iterations > 1:  # the plan_iterations is increased before this check
            return Command(goto="reporter")
        return Command(goto="__end__")

    return Command(
        update={
            "current_plan": Plan.model_validate(new_plan),
            "plan_iterations": plan_iterations,
            "locale": new_plan["locale"],
        },
        goto=goto,
    )


class HumanFeedbackNode(NodeBase):
    """Human feedback node for plan review."""

    @classmethod
    def name(cls) -> str:
        return "human_feedback"

    @classmethod
    async def action(cls, state: State) -> Command[Literal["planner", "research_team", "reporter", "__end__"]]:
        """Human feedback node for plan review."""
        return await human_feedback_node(state)

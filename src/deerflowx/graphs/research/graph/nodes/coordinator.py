# Copyright (c) 2025 Bytedance Ltd. and/or its affiliates
# SPDX-License-Identifier: MIT

import logging
from typing import Annotated, Literal

from langchain_core.messages import AIMessage
from langchain_core.runnables import RunnableConfig
from langchain_core.tools import tool
from langgraph.types import Command

from deerflowx.config.agents import AGENT_LLM_MAP
from deerflowx.config.configuration import Configuration
from deerflowx.graphs.research.graph.state import State
from deerflowx.prompts.template import apply_prompt_template
from deerflowx.utils.llms.llm import get_llm_by_type
from deerflowx.utils.node_base import NodeBase

logger = logging.getLogger(__name__)


@tool
def handoff_to_planner(
    research_topic: Annotated[str, "The topic of the research task to be handed off."],  # noqa: ARG001
    locale: Annotated[str, "The user's detected language locale (e.g., en-US, zh-CN)."],  # noqa: ARG001
) -> None:
    """Handoff to planner agent to do plan."""
    # This tool is not returning anything: we're just using it
    # as a way for LLM to signal that it needs to hand off to planner agent
    return


async def coordinator_node(
    state: State,
    config: RunnableConfig,
) -> Command[Literal["planner", "background_investigator", "__end__"]]:
    """Coordinator node that communicate with customers."""
    logger.info("Coordinator talking.")
    configurable = Configuration.from_runnable_config(config)
    messages = apply_prompt_template("coordinator", state)
    response = await get_llm_by_type(AGENT_LLM_MAP["coordinator"]).bind_tools([handoff_to_planner]).ainvoke(messages)
    logger.debug(f"Current state messages: {state['messages']}")

    goto = "__end__"
    locale = state.get("locale", "en-US")  # Default locale if not specified
    research_topic = state.get("research_topic", "")

    if isinstance(response, AIMessage) and response.tool_calls:
        goto = "planner"
        if state.get("enable_background_investigation"):
            # if the search_before_planning is True, add the web search tool to the planner agent
            goto = "background_investigator"
        try:
            for tool_call in response.tool_calls:
                if tool_call.get("name", "") != "handoff_to_planner":
                    continue
                if tool_call.get("args", {}).get("locale") and tool_call.get("args", {}).get("research_topic"):
                    locale = tool_call.get("args", {}).get("locale")
                    research_topic = tool_call.get("args", {}).get("research_topic")
                    break
        except (AttributeError, KeyError, TypeError):
            logger.exception("Error processing tool calls")
    else:
        logger.warning("Coordinator response contains no tool calls. Terminating workflow execution.")
        logger.debug(f"Coordinator response: {response}")

    return Command(
        update={
            "locale": locale,
            "research_topic": research_topic,
            "resources": configurable.resources,
            "goto": goto,
        },
        goto=goto,
    )


class CoordinatorNode(NodeBase):
    """Coordinator node that communicate with customers."""

    @classmethod
    def name(cls) -> str:
        return "coordinator"

    @classmethod
    async def action(
        cls,
        state: State,
        config: RunnableConfig,
    ) -> Command[Literal["planner", "background_investigator", "__end__"]]:
        """Coordinator node that communicate with customers."""
        return await coordinator_node(state, config)

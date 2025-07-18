import logging
import os
from typing import Any, Literal

from langchain_core.messages import AnyMessage, HumanMessage
from langchain_core.messages.utils import count_tokens_approximately
from langchain_core.runnables import RunnableConfig
from langchain_mcp_adapters.client import MultiServerMCPClient
from langgraph.graph.graph import CompiledGraph
from langgraph.prebuilt import create_react_agent
from langgraph.types import Command

from deerflowx.config.agents import AGENT_LLM_MAP
from deerflowx.config.configuration import Configuration
from deerflowx.graphs.research.graph.state import State
from deerflowx.prompts import apply_prompt_template
from deerflowx.utils.context_compressor import SmartContextCompressor
from deerflowx.utils.llms.llm import get_llm_by_type, get_model_name_for_agent

logger = logging.getLogger(__name__)

DEFAULT_TOKEN_WARNING_THRESHOLD = 20000
DEFAULT_MAX_CONTEXT_TOKENS = 32000


def create_agent(
    agent_name: str,
    agent_type: str,
    tools: list[Any],
    prompt_template: str,
) -> CompiledGraph:
    """Create agents using configured LLM types
    Factory function to create agents with consistent configuration."""
    return create_react_agent(
        name=agent_name,
        model=get_llm_by_type(AGENT_LLM_MAP[agent_type]),
        tools=tools,
        prompt=lambda state: apply_prompt_template(prompt_template, state),
    )


async def _execute_agent_step(  # noqa: C901, PLR0912, PLR0915
    state: State,
    agent: CompiledGraph,
    agent_name: str,
    config: RunnableConfig,
) -> Command[Literal["research_team"]]:
    # TODO: @l8ng 太复杂了需要重构
    """Helper function to execute a step using the specified agent."""
    current_plan = state.get("current_plan")
    observations = state.get("observations", [])

    if not current_plan or isinstance(current_plan, str):
        logger.warning("Invalid current_plan type, expected Plan object")
        return Command(goto="research_team")

    current_step = None
    completed_steps = []
    for step in current_plan.steps:
        if not step.execution_res:
            current_step = step
            break
        completed_steps.append(step)

    if not current_step:
        logger.warning("No unexecuted step found")
        return Command(goto="research_team")

    messages = state.get("messages", [])

    completed_steps_info = ""
    if completed_steps:
        completed_steps_info += "## Completed Steps\n\n"
        for i, step in enumerate(completed_steps):
            completed_steps_info += f"### Step {i + 1}: {step.title}\n\n"
            completed_steps_info += f"Result: {step.execution_res}\n\n"

    if observations:
        completed_steps_info += "## Observations\n\n"
        completed_steps_info += "\n\n".join(observations) + "\n\n"

    num_tokens = count_tokens_approximately(messages)
    if num_tokens > DEFAULT_TOKEN_WARNING_THRESHOLD:
        logger.warning(f"High token count ({num_tokens}) detected in messages before agent execution.")

    messages_for_agent: list[AnyMessage] = [
        HumanMessage(
            content=(
                f"{completed_steps_info}# Current Task\n\n## Title\n\n{current_step.title}\n\n"
                f"## Description\n\n{current_step.description}\n\n## Locale\n\n{state.get('locale', 'en-US')}"
            ),
        ),
    ]
    agent_input: dict[str, Any] = {"messages": messages_for_agent}

    if agent_name == "researcher":
        if state.get("resources"):
            resources_info = "**The user mentioned the following resource files:**\n\n"
            for resource in state.get("resources"):
                resources_info += f"- {resource.title} ({resource.description})\n"

            agent_input["messages"].append(
                HumanMessage(
                    content=resources_info
                    + "\n\n"
                    + "You MUST use the **local_search_tool** to retrieve the information from the resource files.",
                ),
            )

        agent_input["messages"].append(
            HumanMessage(
                content=(
                    "IMPORTANT: DO NOT include inline citations in the text. Instead, track all sources "
                    "and include a References section at the end using link reference format. "
                    "Include an empty line between each citation for better readability. "
                    "Use this format for each reference:\n- [Source Title](URL)\n\n- [Another Source](URL)"
                ),
                name="system",
            ),
        )

    configurable = Configuration.from_runnable_config(config)
    if configurable.enable_context_compression:
        try:
            model_name = get_model_name_for_agent(agent_name)
            override_limit = (
                configurable.max_context_tokens
                if configurable.max_context_tokens != DEFAULT_MAX_CONTEXT_TOKENS
                else None
            )
            compressor = SmartContextCompressor(model_name=model_name, override_token_limit=override_limit)
            agent_input["messages"] = await compressor.compress(agent_input["messages"])
        except ValueError as e:
            logger.warning(f"Failed to initialize context compressor: {e}. Skipping compression.")

    default_recursion_limit = 25
    try:
        env_value_str = os.getenv("AGENT_RECURSION_LIMIT", str(default_recursion_limit))
        parsed_limit = int(env_value_str)

        if parsed_limit > 0:
            recursion_limit = parsed_limit
            logger.info(f"Recursion limit set to: {recursion_limit}")
        else:
            logger.warning(
                f"AGENT_RECURSION_LIMIT value '{env_value_str}' (parsed as {parsed_limit}) is not positive. "
                f"Using default value {default_recursion_limit}.",
            )
            recursion_limit = default_recursion_limit
    except ValueError:
        raw_env_value = os.getenv("AGENT_RECURSION_LIMIT")
        logger.warning(
            f"Invalid AGENT_RECURSION_LIMIT value: '{raw_env_value}'. Using default value {default_recursion_limit}.",
        )
        recursion_limit = default_recursion_limit

    logger.info(f"Agent input: {agent_input}")
    result = await agent.ainvoke(input=agent_input, config={"recursion_limit": recursion_limit})

    response_content = result["messages"][-1].content
    logger.debug(f"{agent_name.capitalize()} full response: {response_content}")

    current_step.execution_res = response_content
    logger.info(f"Step '{current_step.title}' execution completed by {agent_name}")

    return Command(
        update={
            "messages": [
                HumanMessage(
                    content=response_content,
                    name=agent_name,
                ),
            ],
            "observations": [*observations, response_content],
        },
        goto="research_team",
    )


async def _setup_and_execute_agent_step(
    state: State,
    config: RunnableConfig,
    agent_type: str,
    default_tools: list[Any],
) -> Command[Literal["research_team"]]:
    """Helper function to set up an agent with appropriate tools and execute a step.

    This function handles the common logic for both researcher_node and coder_node:
    1. Configures MCP servers and tools based on agent type
    2. Creates an agent with the appropriate tools or uses the default agent
    3. Executes the agent on the current step

    Args:
        state: The current state
        config: The runnable config
        agent_type: The type of agent ("researcher" or "coder")
        default_tools: The default tools to add to the agent

    Returns:
        Command to update state and go to research_team

    """
    configurable = Configuration.from_runnable_config(config)
    mcp_servers = {}
    enabled_tools = {}

    # Extract MCP server configuration for this agent type
    if configurable.mcp_settings:
        for server_name, server_config in configurable.mcp_settings["servers"].items():
            if server_config["enabled_tools"] and agent_type in server_config["add_to_agents"]:
                mcp_servers[server_name] = {
                    k: v for k, v in server_config.items() if k in ("transport", "command", "args", "url", "env")
                }
                for tool_name in server_config["enabled_tools"]:
                    enabled_tools[tool_name] = server_name

    # Create and execute agent with MCP tools if available
    if mcp_servers:
        async with MultiServerMCPClient(mcp_servers) as client:
            loaded_tools = default_tools[:]
            for tool in client.get_tools():
                if tool.name in enabled_tools:
                    tool.description = f"Powered by '{enabled_tools[tool.name]}'.\n{tool.description}"
                    loaded_tools.append(tool)
            agent = create_agent(agent_type, agent_type, loaded_tools, agent_type)
            return await _execute_agent_step(state, agent, agent_type, config)
    else:
        # Use default tools if no MCP servers are configured
        agent = create_agent(agent_type, agent_type, default_tools, agent_type)
        return await _execute_agent_step(state, agent, agent_type, config)

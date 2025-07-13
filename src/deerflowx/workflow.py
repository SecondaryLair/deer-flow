# Copyright (c) 2025 Bytedance Ltd. and/or its affiliates
# SPDX-License-Identifier: MIT
"""Workflow module for running agent workflows asynchronously."""

import logging

from deerflowx.config.report_style import ReportStyle
from deerflowx.utils.workflow_executor import workflow_executor

# Configure logging
logging.basicConfig(
    level=logging.INFO,  # Default level is INFO
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)


def enable_debug_logging() -> None:
    """Enable debug level logging for more detailed execution information."""
    logging.getLogger("src").setLevel(logging.DEBUG)


logger = logging.getLogger(__name__)


async def run_agent_workflow_async(  # noqa: C901
    user_input: str,
    *,
    debug: bool = False,
    max_plan_iterations: int = 1,
    max_step_num: int = 3,
    enable_background_investigation: bool = True,
) -> None:
    """Run the agent workflow asynchronously with the given user input.

    Args:
        user_input: The user's query or request
        debug: If True, enables debug level logging
        max_plan_iterations: Maximum number of plan iterations
        max_step_num: Maximum number of steps in a plan
        enable_background_investigation: If True, performs web search before planning to enhance context

    Returns:
        The final state after the workflow completes

    """
    if not user_input:
        _msg = "Input could not be empty"
        raise ValueError(_msg)

    if debug:
        enable_debug_logging()

    logger.info(f"Starting async workflow with user input: {user_input}")

    # Use the unified workflow executor
    mcp_settings = {
        "servers": {
            "mcp-github-trending": {
                "transport": "stdio",
                "command": "uvx",
                "args": ["mcp-github-trending"],
                "enabled_tools": ["get_github_trending_repositories"],
                "add_to_agents": ["researcher"],
            },
        },
    }

    async for event in workflow_executor.execute_workflow(
        messages=[{"role": "user", "content": user_input}],
        thread_id="cli-session",
        resources=[],
        max_plan_iterations=max_plan_iterations,
        max_step_num=max_step_num,
        max_search_results=3,
        auto_accepted_plan=True,
        interrupt_feedback="",
        mcp_settings=mcp_settings,
        enable_background_investigation=enable_background_investigation,
        report_style=ReportStyle.ACADEMIC,
        enable_deep_thinking=False,
        user_id="cli-user",
        tags=["cli", "research", "langgraph"],
    ):
        try:
            # Process events from the unified executor
            if event.get("type") == "message_chunk":
                data = event.get("data", {})
                content = data.get("content", "")
                if content:
                    logger.info(f"[{data.get('agent', 'unknown')}] {content}")
            elif event.get("type") == "tool_calls":
                data = event.get("data", {})
                tool_calls = data.get("tool_calls", [])
                for tool_call in tool_calls:
                    logger.info(f"[tool_call] {tool_call.get('name', 'unknown')}: {tool_call.get('args', {})}")
            elif event.get("type") == "tool_call_result":
                data = event.get("data", {})
                logger.info(f"[tool_result] {data.get('content', '')}")
            elif event.get("type") == "interrupt":
                data = event.get("data", {})
                logger.info(f"[interrupt] {data.get('content', '')}")
        except (AttributeError, TypeError, ValueError):
            logger.exception("Error processing stream output")

    logger.info("Async workflow completed successfully")


if __name__ == "__main__":
    print(workflow_executor.graph.get_graph(xray=True).draw_mermaid())  # noqa: T201

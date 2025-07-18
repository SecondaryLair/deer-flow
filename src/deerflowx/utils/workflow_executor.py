# Copyright (c) 2025 Bytedance Ltd. and/or its affiliates
# SPDX-License-Identifier: MIT
"""Unified workflow executor with Langfuse tracing support."""

import logging
from collections.abc import AsyncGenerator
from typing import Any, cast
from uuid import uuid4

from langchain_core.messages import AIMessageChunk, BaseMessage, ToolMessage
from langchain_core.runnables import RunnableConfig
from langgraph.types import Command

from deerflowx.config.report_style import ReportStyle
from deerflowx.graphs.research.graph.builder import build_graph_with_memory
from deerflowx.libs.rag.retriever import Resource
from deerflowx.utils.langfuse_utils import (
    create_langfuse_callback_handler,
    get_langfuse_client,
    is_langfuse_enabled,
)

logger = logging.getLogger(__name__)


class WorkflowExecutor:
    """Unified workflow executor with Langfuse tracing support."""

    def __init__(self) -> None:
        """Initialize the workflow executor."""
        self.graph = build_graph_with_memory()

    async def execute_workflow(  # noqa: PLR0913
        self,
        messages: list[dict],
        thread_id: str | None = None,
        resources: list[Resource] | None = None,
        max_plan_iterations: int = 1,
        max_step_num: int = 3,
        max_search_results: int = 3,
        auto_accepted_plan: bool = False,
        interrupt_feedback: str = "",
        mcp_settings: dict | None = None,
        enable_background_investigation: bool = True,
        report_style: ReportStyle = ReportStyle.ACADEMIC,
        enable_deep_thinking: bool = False,
        user_id: str = "deerflow-user",
        tags: list[str] | None = None,
    ) -> AsyncGenerator[dict[str, Any], None]:
        """Execute workflow with optional Langfuse tracing.

        Args:
            messages: List of messages to process
            thread_id: Thread ID for the session
            resources: List of resources for RAG
            max_plan_iterations: Maximum number of plan iterations
            max_step_num: Maximum number of steps in a plan
            max_search_results: Maximum number of search results
            auto_accepted_plan: Whether to auto-accept plans
            interrupt_feedback: Feedback for interrupts
            mcp_settings: MCP server settings
            enable_background_investigation: Whether to enable background investigation
            report_style: Report style to use
            enable_deep_thinking: Whether to enable deep thinking
            user_id: User ID for tracing
            tags: Tags for tracing

        Yields:
            Workflow events as dictionaries
        """
        if thread_id is None:
            thread_id = str(uuid4())

        if resources is None:
            resources = []

        if mcp_settings is None:
            mcp_settings = {}

        if tags is None:
            tags = ["research", "langgraph", "deepresearch"]

        # Create Langfuse trace if enabled
        langfuse_client = get_langfuse_client() if is_langfuse_enabled() else None

        if langfuse_client:
            # Determine trace phase
            is_report_phase = auto_accepted_plan or (
                interrupt_feedback and interrupt_feedback.upper().startswith("[ACCEPTED]")
            )
            trace_name = f"report-{thread_id}" if is_report_phase else f"survey-{thread_id}"

            with langfuse_client.start_as_current_span(name=trace_name) as span:
                span.update_trace(
                    input={
                        "messages": messages,
                        "enable_deep_thinking": enable_deep_thinking,
                        "report_style": report_style.value,
                        "enable_background_investigation": enable_background_investigation,
                    },
                    session_id=thread_id,
                    user_id=user_id,
                    tags=tags,
                )

                async for event in self._execute_workflow_core(
                    messages=messages,
                    thread_id=thread_id,
                    resources=resources,
                    max_plan_iterations=max_plan_iterations,
                    max_step_num=max_step_num,
                    max_search_results=max_search_results,
                    auto_accepted_plan=auto_accepted_plan,
                    interrupt_feedback=interrupt_feedback,
                    mcp_settings=mcp_settings,
                    enable_background_investigation=enable_background_investigation,
                    report_style=report_style,
                    enable_deep_thinking=enable_deep_thinking,
                ):
                    yield event

                span.update_trace(output={"status": "completed"})
        else:
            async for event in self._execute_workflow_core(
                messages=messages,
                thread_id=thread_id,
                resources=resources,
                max_plan_iterations=max_plan_iterations,
                max_step_num=max_step_num,
                max_search_results=max_search_results,
                auto_accepted_plan=auto_accepted_plan,
                interrupt_feedback=interrupt_feedback,
                mcp_settings=mcp_settings,
                enable_background_investigation=enable_background_investigation,
                report_style=report_style,
                enable_deep_thinking=enable_deep_thinking,
            ):
                yield event

    async def _execute_workflow_core(  # noqa: C901, PLR0912, PLR0913
        self,
        messages: list[dict],
        thread_id: str,
        resources: list[Resource],
        max_plan_iterations: int,
        max_step_num: int,
        max_search_results: int,
        auto_accepted_plan: bool,
        interrupt_feedback: str,
        mcp_settings: dict,
        enable_background_investigation: bool,
        report_style: ReportStyle,
        enable_deep_thinking: bool,
    ) -> AsyncGenerator[dict[str, Any], None]:
        """Core workflow execution logic."""
        input_ = {
            "messages": messages,
            "plan_iterations": 0,
            "final_report": "",
            "current_plan": None,
            "observations": [],
            "auto_accepted_plan": auto_accepted_plan,
            "enable_background_investigation": enable_background_investigation,
            "research_topic": messages[-1]["content"] if messages else "",
        }

        if not auto_accepted_plan and interrupt_feedback:
            resume_msg = f"[{interrupt_feedback}]"
            # add the last message to the resume message
            if messages:
                resume_msg += f" {messages[-1]['content']}"
            input_ = Command(resume=resume_msg)

        graph_stream_config = {
            "thread_id": thread_id,
            "resources": resources,
            "max_plan_iterations": max_plan_iterations,
            "max_step_num": max_step_num,
            "max_search_results": max_search_results,
            "mcp_settings": mcp_settings,
            "report_style": report_style.value,
            "enable_deep_thinking": enable_deep_thinking,
        }

        # Create Langfuse CallbackHandler if enabled
        langfuse_handler = create_langfuse_callback_handler()

        config: RunnableConfig = {"configurable": graph_stream_config}
        if langfuse_handler:
            config["callbacks"] = [langfuse_handler]

        async for agent, _, event_data in self.graph.astream(
            input_,
            config=config,
            stream_mode=["messages", "updates"],
            subgraphs=True,
        ):
            if isinstance(event_data, dict):
                if "__interrupt__" in event_data:
                    yield {
                        "type": "interrupt",
                        "data": {
                            "thread_id": thread_id,
                            "id": event_data["__interrupt__"][0].ns[0],
                            "role": "assistant",
                            "content": event_data["__interrupt__"][0].value,
                            "finish_reason": "interrupt",
                            "options": [
                                {"text": "Edit plan", "value": "edit_plan"},
                                {"text": "Start research", "value": "accepted"},
                            ],
                        },
                    }
                continue

            message_chunk, message_metadata = cast("tuple[BaseMessage, dict[str, Any]]", event_data)
            event_stream_message: dict[str, Any] = {
                "thread_id": thread_id,
                "agent": agent[0].split(":")[0],
                "id": message_chunk.id,
                "role": "assistant",
                "content": message_chunk.content,
            }

            if message_chunk.additional_kwargs.get("reasoning_content"):
                event_stream_message["reasoning_content"] = message_chunk.additional_kwargs["reasoning_content"]

            if message_chunk.response_metadata.get("finish_reason"):
                event_stream_message["finish_reason"] = message_chunk.response_metadata.get("finish_reason")

            if isinstance(message_chunk, ToolMessage):
                # Tool Message - Return the result of the tool call
                event_stream_message["tool_call_id"] = message_chunk.tool_call_id
                yield {"type": "tool_call_result", "data": event_stream_message}
            elif isinstance(message_chunk, AIMessageChunk):
                # AI Message - Raw message tokens
                if message_chunk.tool_calls:
                    # AI Message - Tool Call
                    event_stream_message["tool_calls"] = message_chunk.tool_calls
                    event_stream_message["tool_call_chunks"] = message_chunk.tool_call_chunks
                    yield {"type": "tool_calls", "data": event_stream_message}
                elif message_chunk.tool_call_chunks:
                    # AI Message - Tool Call Chunks
                    event_stream_message["tool_call_chunks"] = message_chunk.tool_call_chunks
                    yield {"type": "tool_call_chunks", "data": event_stream_message}
                else:
                    # AI Message - Raw message tokens
                    yield {"type": "message_chunk", "data": event_stream_message}


# Create a global instance for reuse
workflow_executor = WorkflowExecutor()

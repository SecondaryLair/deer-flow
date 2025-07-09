# Copyright (c) 2025 Bytedance Ltd. and/or its affiliates
# SPDX-License-Identifier: MIT
"""FastAPI server application for deer-flow research assistant."""

import json
import logging
from collections.abc import AsyncGenerator
from typing import Annotated, Any, cast
from uuid import uuid4

from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from langchain_core.messages import AIMessageChunk, BaseMessage, ToolMessage
from langgraph.types import Command

from deerflowx.config.report_style import ReportStyle
from deerflowx.config.tools import SELECTED_RAG_PROVIDER
from deerflowx.graph.builder import build_graph_with_memory
from deerflowx.llms.llm import get_configured_llm_models
from deerflowx.prompt_enhancer.graph.builder import build_graph as build_prompt_enhancer_graph
from deerflowx.prose.graph.builder import build_graph as build_prose_graph
from deerflowx.rag.builder import build_retriever
from deerflowx.rag.retriever import Resource
from deerflowx.server.chat_request import (
    DEFAULT_CHAT_REQUEST_THREAD_ID_VALUE,
    ChatRequest,
    EnhancePromptRequest,
    GenerateProseRequest,
)
from deerflowx.server.config_request import ConfigResponse
from deerflowx.server.mcp_request import MCPServerMetadataRequest, MCPServerMetadataResponse
from deerflowx.server.mcp_utils import MCPServerConfig, load_mcp_tools
from deerflowx.server.rag_request import (
    RAGConfigResponse,
    RAGResourceRequest,
    RAGResourcesResponse,
)

logger = logging.getLogger(__name__)

INTERNAL_SERVER_ERROR_DETAIL = "Internal Server Error"

app = FastAPI(
    title="DeerFlow API",
    description="API for Deer",
    version="0.1.0",
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allows all origins
    allow_credentials=True,
    allow_methods=["*"],  # Allows all methods
    allow_headers=["*"],  # Allows all headers
)

graph = build_graph_with_memory()


@app.post("/api/chat/stream")
async def chat_stream(request: ChatRequest) -> StreamingResponse:
    thread_id = request.thread_id
    if thread_id == DEFAULT_CHAT_REQUEST_THREAD_ID_VALUE:
        thread_id = str(uuid4())
    return StreamingResponse(
        _astream_workflow_generator(
            request.model_dump()["messages"],
            thread_id,
            request.resources,
            request.max_plan_iterations,
            request.max_step_num,
            request.max_search_results,
            request.auto_accepted_plan,
            request.interrupt_feedback,
            request.mcp_settings,
            request.enable_background_investigation,
            request.report_style,
            request.enable_deep_thinking,
        ),
        media_type="text/event-stream",
    )


async def _astream_workflow_generator(  # noqa: PLR0913
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
) -> AsyncGenerator[str, None]:
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
    async for agent, _, event_data in graph.astream(
        input_,
        config={"configurable": graph_stream_config},
        stream_mode=["messages", "updates"],
        subgraphs=True,
    ):
        if isinstance(event_data, dict):
            if "__interrupt__" in event_data:
                yield _make_event(
                    "interrupt",
                    {
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
                )
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
            yield _make_event("tool_call_result", event_stream_message)
        elif isinstance(message_chunk, AIMessageChunk):
            # AI Message - Raw message tokens
            if message_chunk.tool_calls:
                # AI Message - Tool Call
                event_stream_message["tool_calls"] = message_chunk.tool_calls
                event_stream_message["tool_call_chunks"] = message_chunk.tool_call_chunks
                yield _make_event("tool_calls", event_stream_message)
            elif message_chunk.tool_call_chunks:
                # AI Message - Tool Call Chunks
                event_stream_message["tool_call_chunks"] = message_chunk.tool_call_chunks
                yield _make_event("tool_call_chunks", event_stream_message)
            else:
                # AI Message - Raw message tokens
                yield _make_event("message_chunk", event_stream_message)


def _make_event(event_type: str, data: dict[str, Any]) -> str:
    if data.get("content") == "":
        data.pop("content")
    return f"event: {event_type}\ndata: {json.dumps(data, ensure_ascii=False)}\n\n"


@app.post("/api/prose/generate")
async def generate_prose(request: GenerateProseRequest) -> StreamingResponse:
    try:
        sanitized_prompt = request.prompt.replace("\r\n", "").replace("\n", "")
        logger.info(f"Generating prose for prompt: {sanitized_prompt}")
        workflow = build_prose_graph()
        events = workflow.astream(
            {
                "content": request.prompt,
                "option": request.option,
                "command": request.command,
            },
            stream_mode="messages",
            subgraphs=True,
        )
        return StreamingResponse(
            (f"data: {event[0].content}\n\n" async for _, event in events),
            media_type="text/event-stream",
        )
    except (ValueError, TypeError, RuntimeError) as e:
        logger.exception("Error occurred during prose generation")
        raise HTTPException(status_code=500, detail=INTERNAL_SERVER_ERROR_DETAIL) from e


@app.post("/api/prompt/enhance")
async def enhance_prompt(request: EnhancePromptRequest) -> dict[str, str]:
    try:
        sanitized_prompt = request.prompt.replace("\r\n", "").replace("\n", "")
        logger.info(f"Enhancing prompt: {sanitized_prompt}")

        # Convert string report_style to ReportStyle enum
        report_style = None
        if request.report_style:
            try:
                # Handle both uppercase and lowercase input
                style_mapping = {
                    "ACADEMIC": ReportStyle.ACADEMIC,
                    "POPULAR_SCIENCE": ReportStyle.POPULAR_SCIENCE,
                    "NEWS": ReportStyle.NEWS,
                    "SOCIAL_MEDIA": ReportStyle.SOCIAL_MEDIA,
                }
                report_style = style_mapping.get(request.report_style.upper(), ReportStyle.ACADEMIC)
            except (AttributeError, KeyError):
                # If invalid style, default to ACADEMIC
                report_style = ReportStyle.ACADEMIC
        else:
            report_style = ReportStyle.ACADEMIC

        workflow = build_prompt_enhancer_graph()
        final_state = workflow.invoke(
            {
                "prompt": request.prompt,
                "context": request.context,
                "report_style": report_style,
            },
        )
        return {"result": final_state["output"]}
    except (ValueError, TypeError, RuntimeError) as e:
        logger.exception("Error occurred during prompt enhancement")
        raise HTTPException(status_code=500, detail=INTERNAL_SERVER_ERROR_DETAIL) from e


@app.post("/api/mcp/server/metadata")
async def mcp_server_metadata(request: MCPServerMetadataRequest) -> MCPServerMetadataResponse:
    """Get information about an MCP server."""
    try:
        # Set default timeout with a longer value for this endpoint
        timeout = 300  # Default to 300 seconds for this endpoint

        # Use custom timeout from request if provided
        if request.timeout_seconds is not None:
            timeout = request.timeout_seconds

        # Load tools from the MCP server using the utility function
        config = MCPServerConfig(
            server_type=request.transport,
            command=request.command,
            args=request.args,
            url=request.url,
            env=request.env,
            timeout_seconds=timeout,
        )
        tools = await load_mcp_tools(config)

        # Create the response with tools
        return MCPServerMetadataResponse(
            transport=request.transport,
            command=request.command,
            args=request.args,
            url=request.url,
            env=request.env,
            tools=tools,
        )

    except (ValueError, TypeError, RuntimeError, ConnectionError) as e:
        logger.exception("Error in MCP server metadata endpoint")
        raise HTTPException(status_code=500, detail=INTERNAL_SERVER_ERROR_DETAIL) from e


@app.get("/api/rag/config")
async def rag_config() -> RAGConfigResponse:
    """Get the config of the RAG."""
    return RAGConfigResponse(provider=SELECTED_RAG_PROVIDER)


@app.get("/api/rag/resources")
async def rag_resources(request: Annotated[RAGResourceRequest, Query()]) -> RAGResourcesResponse:
    """Get the resources of the RAG."""
    retriever = build_retriever()
    if retriever:
        return RAGResourcesResponse(resources=retriever.list_resources(request.query))
    return RAGResourcesResponse(resources=[])


@app.get("/api/config")
async def config() -> ConfigResponse:
    """Get the config of the server."""
    return ConfigResponse(
        rag=RAGConfigResponse(provider=SELECTED_RAG_PROVIDER),
        models=get_configured_llm_models(),
    )

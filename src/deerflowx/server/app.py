# Copyright (c) 2025 Bytedance Ltd. and/or its affiliates
# SPDX-License-Identifier: MIT
"""FastAPI server application for deer-flow research assistant."""

import importlib.metadata
import json
import logging
from collections.abc import AsyncGenerator
from typing import Annotated, Any
from uuid import uuid4

from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse

from deerflowx.config.report_style import ReportStyle
from deerflowx.config.tools import SELECTED_RAG_PROVIDER
from deerflowx.graphs.prompt_enhancer.graph.builder import build_graph as build_prompt_enhancer_graph
from deerflowx.graphs.prose.graph.builder import build_graph as build_prose_graph
from deerflowx.libs.rag.builder import build_retriever
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
from deerflowx.utils.llms.llm import get_configured_llm_models
from deerflowx.utils.workflow_executor import workflow_executor

logger = logging.getLogger(__name__)

INTERNAL_SERVER_ERROR_DETAIL = "Internal Server Error"

app = FastAPI(
    title="DeerFlow API",
    description="API for Deer",
    version=importlib.metadata.version("deerflowx"),
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allows all origins
    allow_credentials=True,
    allow_methods=["*"],  # Allows all methods
    allow_headers=["*"],  # Allows all headers
)


@app.post("/api/chat/stream")
async def chat_stream(request: ChatRequest) -> StreamingResponse:
    thread_id = request.thread_id
    if thread_id == DEFAULT_CHAT_REQUEST_THREAD_ID_VALUE:
        thread_id = str(uuid4())

    return StreamingResponse(
        _execute_workflow_with_unified_executor(request, thread_id),
        media_type="text/event-stream",
    )


async def _execute_workflow_with_unified_executor(
    request: ChatRequest,
    thread_id: str,
) -> AsyncGenerator[str, None]:
    """Execute workflow using the unified executor with Langfuse tracing."""
    async for event in workflow_executor.execute_workflow(
        messages=request.model_dump()["messages"],
        thread_id=thread_id,
        resources=request.resources,
        max_plan_iterations=request.max_plan_iterations,
        max_step_num=request.max_step_num,
        max_search_results=request.max_search_results,
        auto_accepted_plan=request.auto_accepted_plan,
        interrupt_feedback=request.interrupt_feedback or "",
        mcp_settings=request.mcp_settings or {},
        enable_background_investigation=request.enable_background_investigation,
        report_style=request.report_style,
        enable_deep_thinking=request.enable_deep_thinking,
    ):
        # Convert unified executor event format to server event format
        if event.get("type") == "interrupt":
            yield _make_event("interrupt", event["data"])
        elif event.get("type") == "tool_call_result":
            yield _make_event("tool_call_result", event["data"])
        elif event.get("type") == "tool_calls":
            yield _make_event("tool_calls", event["data"])
        elif event.get("type") == "tool_call_chunks":
            yield _make_event("tool_call_chunks", event["data"])
        elif event.get("type") == "message_chunk":
            yield _make_event("message_chunk", event["data"])


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
            (f"data: {getattr(event[0], 'content', str(event[0]))}\n\n" async for _, event in events),
            media_type="text/event-stream",
        )
    except BaseException as e:
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
    except BaseException as e:
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

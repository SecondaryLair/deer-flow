# Copyright (c) 2025 Bytedance Ltd. and/or its affiliates
# SPDX-License-Identifier: MIT

from typing import List, Optional, Union

from pydantic import BaseModel, Field

from src.rag.retriever import Resource
from src.config.report_style import ReportStyle


class ContentItem(BaseModel):
    type: str = Field(..., description="The type of content (text, image, etc.)")
    text: Optional[str] = Field(None, description="The text content if type is 'text'")
    image_url: Optional[str] = Field(
        None, description="The image URL if type is 'image'"
    )


class ChatMessage(BaseModel):
    role: str = Field(
        ..., description="The role of the message sender (user or assistant)"
    )
    content: Union[str, List[ContentItem]] = Field(
        ...,
        description="The content of the message, either a string or a list of content items",
    )


DEFAULT_CHAT_REQUEST_THREAD_ID_VALUE = "__default__"


class ChatRequest(BaseModel):
    messages: Optional[List[ChatMessage]] = Field(
        [], description="History of messages between the user and the assistant"
    )
    resources: List[Resource] = Field(
        [], description="Resources to be used for the research"
    )
    debug: Optional[bool] = Field(False, description="Whether to enable debug logging")
    thread_id: str = Field(
        DEFAULT_CHAT_REQUEST_THREAD_ID_VALUE,
        description="A specific conversation identifier",
    )
    max_plan_iterations: int = Field(
        1, description="The maximum number of plan iterations"
    )
    max_step_num: int = Field(3, description="The maximum number of steps in a plan")
    max_search_results: int = Field(
        3, description="The maximum number of search results"
    )
    auto_accepted_plan: bool = Field(
        False, description="Whether to automatically accept the plan"
    )
    interrupt_feedback: Optional[str] = Field(
        None, description="Interrupt feedback from the user on the plan"
    )
    mcp_settings: Optional[dict] = Field(
        None, description="MCP settings for the chat request"
    )
    enable_background_investigation: bool = Field(
        True, description="Whether to get background investigation before plan"
    )
    report_style: ReportStyle = Field(
        ReportStyle.ACADEMIC, description="The style of the report"
    )
    enable_deep_thinking: bool = Field(
        False, description="Whether to enable deep thinking"
    )


class GeneratePPTRequest(BaseModel):
    content: str = Field(..., description="The content of the ppt")


class GenerateProseRequest(BaseModel):
    prompt: str = Field(..., description="The content of the prose")
    option: str = Field(..., description="The option of the prose writer")
    command: Optional[str] = Field(
        "", description="The user custom command of the prose writer"
    )


class EnhancePromptRequest(BaseModel):
    prompt: str = Field(..., description="The original prompt to enhance")
    context: Optional[str] = Field(
        "", description="Additional context about the intended use"
    )
    report_style: Optional[str] = Field(
        "academic", description="The style of the report"
    )

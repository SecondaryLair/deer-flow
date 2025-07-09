# Copyright (c) 2025 Bytedance Ltd. and/or its affiliates
# SPDX-License-Identifier: MIT
"""Configuration request models and responses."""

from pydantic import BaseModel, Field

from deerflowx.server.rag_request import RAGConfigResponse


class ConfigResponse(BaseModel):
    """Response model for server config."""

    rag: RAGConfigResponse = Field(..., description="The config of the RAG")
    models: dict[str, list[str]] = Field(..., description="The configured models")

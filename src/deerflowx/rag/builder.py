# Copyright (c) 2025 Bytedance Ltd. and/or its affiliates
# SPDX-License-Identifier: MIT

from deerflowx.config.tools import SELECTED_RAG_PROVIDER, RAGProvider
from deerflowx.rag.ragflow import RAGFlowProvider
from deerflowx.rag.retriever import Retriever
from deerflowx.rag.vikingdb_knowledge_base import VikingDBKnowledgeBaseProvider


def build_retriever() -> Retriever | None:
    if RAGProvider.RAGFLOW.value == SELECTED_RAG_PROVIDER:
        return RAGFlowProvider()
    if RAGProvider.VIKINGDB_KNOWLEDGE_BASE.value == SELECTED_RAG_PROVIDER:
        return VikingDBKnowledgeBaseProvider()
    if SELECTED_RAG_PROVIDER:
        msg = f"Unsupported RAG provider: {SELECTED_RAG_PROVIDER}"
        raise ValueError(msg)
    return None

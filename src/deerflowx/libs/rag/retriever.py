# Copyright (c) 2025 Bytedance Ltd. and/or its affiliates
# SPDX-License-Identifier: MIT

import abc

from pydantic import BaseModel, Field


class Chunk:
    content: str
    similarity: float

    def __init__(self, content: str, similarity: float) -> None:
        self.content = content
        self.similarity = similarity


class Document:
    """Document is a class that represents a document."""

    id: str
    url: str | None = None
    title: str | None = None
    chunks: list[Chunk] | None = None

    def __init__(
        self,
        doc_id: str,
        url: str | None = None,
        title: str | None = None,
        chunks: list[Chunk] | None = None,
    ) -> None:
        if chunks is None:
            chunks = []
        self.id = doc_id
        self.url = url
        self.title = title
        self.chunks = chunks

    def to_dict(self) -> dict:
        chunks = self.chunks or []
        d = {
            "id": self.id,
            "content": "\n\n".join([chunk.content for chunk in chunks]),
        }
        if self.url:
            d["url"] = self.url
        if self.title:
            d["title"] = self.title
        return d


class Resource(BaseModel):
    """Resource is a class that represents a resource."""

    uri: str = Field(..., description="The URI of the resource")
    title: str = Field(..., description="The title of the resource")
    description: str | None = Field("", description="The description of the resource")


class Retriever(abc.ABC):
    """Define a RAG provider, which can be used to query documents and resources."""

    @abc.abstractmethod
    def list_resources(self, query: str | None = None) -> list[Resource]:
        """List resources from the rag provider."""

    @abc.abstractmethod
    def query_relevant_documents(self, query: str, resources: list[Resource] | None = None) -> list[Document]:
        """Query relevant documents from the resources."""

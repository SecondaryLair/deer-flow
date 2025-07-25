# Copyright (c) 2025 Bytedance Ltd. and/or its affiliates
# SPDX-License-Identifier: MIT

import os
from urllib.parse import urlparse

import requests

from deerflowx.libs.rag.retriever import Chunk, Document, Resource, Retriever

# HTTP status codes
HTTP_OK = 200


class RAGFlowProvider(Retriever):
    """RAGFlowProvider is a provider that uses RAGFlow to retrieve documents."""

    api_url: str
    api_key: str
    page_size: int = 10

    def __init__(self) -> None:
        api_url = os.getenv("RAGFLOW_API_URL")
        if not api_url:
            msg = "RAGFLOW_API_URL is not set"
            raise ValueError(msg)
        self.api_url = api_url

        api_key = os.getenv("RAGFLOW_API_KEY")
        if not api_key:
            msg = "RAGFLOW_API_KEY is not set"
            raise ValueError(msg)
        self.api_key = api_key

        page_size = os.getenv("RAGFLOW_PAGE_SIZE")
        if page_size:
            self.page_size = int(page_size)

    def query_relevant_documents(self, query: str, resources: list[Resource] | None = None) -> list[Document]:
        if resources is None:
            resources = []
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }

        dataset_ids: list[str] = []
        document_ids: list[str] = []

        for resource in resources:
            dataset_id, document_id = parse_uri(resource.uri)
            dataset_ids.append(dataset_id)
            if document_id:
                document_ids.append(document_id)

        payload = {
            "question": query,
            "dataset_ids": dataset_ids,
            "document_ids": document_ids,
            "page_size": self.page_size,
        }

        response = requests.post(f"{self.api_url}/api/v1/retrieval", headers=headers, json=payload, timeout=30)

        if response.status_code != HTTP_OK:
            msg = f"Failed to query documents: {response.text}"
            raise RuntimeError(msg)

        result = response.json()
        data = result.get("data", {})
        doc_aggs = data.get("doc_aggs", [])
        docs: dict[str, Document] = {
            doc.get("doc_id"): Document(
                doc_id=doc.get("doc_id"),
                title=doc.get("doc_name"),
                chunks=[],
            )
            for doc in doc_aggs
        }

        for chunk in data.get("chunks", []):
            doc = docs.get(chunk.get("document_id"))
            if doc and doc.chunks is not None:
                doc.chunks.append(
                    Chunk(
                        content=chunk.get("content"),
                        similarity=chunk.get("similarity"),
                    ),
                )

        return list(docs.values())

    def list_resources(self, query: str | None = None) -> list[Resource]:
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }

        params = {}
        if query:
            params["name"] = query

        response = requests.get(f"{self.api_url}/api/v1/datasets", headers=headers, params=params, timeout=30)

        if response.status_code != HTTP_OK:
            msg = f"Failed to list resources: {response.text}"
            raise RuntimeError(msg)

        result = response.json()
        resources = []

        for item_data in result.get("data", []):
            item = Resource(
                uri=f"rag://dataset/{item_data.get('id')}",
                title=item_data.get("name", ""),
                description=item_data.get("description", ""),
            )
            resources.append(item)

        return resources


def parse_uri(uri: str) -> tuple[str, str]:
    parsed = urlparse(uri)
    if parsed.scheme != "rag":
        msg = f"Invalid URI: {uri}"
        raise ValueError(msg)
    return parsed.path.split("/")[1], parsed.fragment

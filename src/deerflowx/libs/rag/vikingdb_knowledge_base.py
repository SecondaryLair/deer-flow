# Copyright (c) 2025 Bytedance Ltd. and/or its affiliates
# SPDX-License-Identifier: MIT

import json
import os
from urllib.parse import urlparse

import requests
from volcengine.auth.SignerV4 import SignerV4
from volcengine.base.Request import Request
from volcengine.Credentials import Credentials

from deerflowx.libs.rag.retriever import Chunk, Document, Resource, Retriever


class VikingDBKnowledgeBaseProvider(Retriever):
    """VikingDBKnowledgeBaseProvider is a provider that uses VikingDB Knowledge base API to retrieve documents."""

    api_url: str
    api_ak: str
    api_sk: str
    retrieval_size: int = 10

    def __init__(self) -> None:
        api_url = os.getenv("VIKINGDB_KNOWLEDGE_BASE_API_URL")
        if not api_url:
            msg = "VIKINGDB_KNOWLEDGE_BASE_API_URL is not set"
            raise ValueError(msg)
        self.api_url = api_url

        api_ak = os.getenv("VIKINGDB_KNOWLEDGE_BASE_API_AK")
        if not api_ak:
            msg = "VIKINGDB_KNOWLEDGE_BASE_API_AK is not set"
            raise ValueError(msg)
        self.api_ak = api_ak

        api_sk = os.getenv("VIKINGDB_KNOWLEDGE_BASE_API_SK")
        if not api_sk:
            msg = "VIKINGDB_KNOWLEDGE_BASE_API_SK is not set"
            raise ValueError(msg)
        self.api_sk = api_sk

        retrieval_size = os.getenv("VIKINGDB_KNOWLEDGE_BASE_RETRIEVAL_SIZE")
        if retrieval_size:
            self.retrieval_size = int(retrieval_size)

    def prepare_request(
        self,
        method: str,
        path: str,
        params: dict | None = None,
        data: dict | None = None,
        doseq: int = 0,
    ) -> Request:
        """Prepare signed request using volcengine auth."""
        if params:
            for key in params:
                if isinstance(params[key], (int, float, bool)):
                    params[key] = str(params[key])
                elif isinstance(params[key], list) and not doseq:
                    params[key] = ",".join(params[key])

        r = Request()
        r.set_shema("https")
        r.set_method(method)
        r.set_connection_timeout(10)
        r.set_socket_timeout(10)
        mheaders = {
            "Accept": "application/json",
            "Content-Type": "application/json",
        }
        r.set_headers(mheaders)
        if params:
            r.set_query(params)
        r.set_path(path)
        if data is not None:
            r.set_body(json.dumps(data))

        credentials = Credentials(self.api_ak, self.api_sk, "air", "cn-north-1")
        SignerV4.sign(r, credentials)
        return r

    def query_relevant_documents(self, query: str, resources: list[Resource] | None = None) -> list[Document]:  # noqa: C901
        """Query relevant documents from the knowledge base."""
        if resources is None:
            resources = []
        if not resources:
            return []

        all_documents = {}
        for resource in resources:
            resource_id, document_id = parse_uri(resource.uri)
            request_params = {
                "resource_id": resource_id,
                "query": query,
                "limit": self.retrieval_size,
                "dense_weight": 0.5,
                "pre_processing": {
                    "need_instruction": True,
                    "rewrite": False,
                    "return_token_usage": True,
                },
                "post_processing": {
                    "rerank_switch": True,
                    "chunk_diffusion_count": 0,
                    "chunk_group": True,
                    "get_attachment_link": True,
                },
            }
            if document_id:
                doc_filter = {"op": "must", "field": "doc_id", "conds": [document_id]}
                query_param = {"doc_filter": doc_filter}
                request_params["query_param"] = query_param

            method = "POST"
            path = "/api/knowledge/collection/search_knowledge"
            info_req = self.prepare_request(method=method, path=path, data=request_params)
            rsp = requests.request(
                method=info_req.method,
                url=f"http://{self.api_url}{info_req.path}",
                headers=info_req.headers,
                data=info_req.body,
                timeout=30,
            )

            try:
                response = json.loads(rsp.text)
            except json.JSONDecodeError as e:
                msg = f"Failed to parse JSON response: {e}"
                raise ValueError(msg) from e

            if response["code"] != 0:
                msg = f"Failed to query documents from resource: {response['message']}"
                raise ValueError(msg)

            rsp_data = response.get("data", {})

            if "result_list" not in rsp_data:
                continue

            result_list = rsp_data["result_list"]

            for item in result_list:
                doc_info = item.get("doc_info", {})
                doc_id = doc_info.get("doc_id")

                if not doc_id:
                    continue

                if doc_id not in all_documents:
                    all_documents[doc_id] = Document(doc_id=doc_id, title=doc_info.get("doc_name"), chunks=[])

                chunk = Chunk(content=item.get("content", ""), similarity=item.get("score", 0.0))
                all_documents[doc_id].chunks.append(chunk)

        return list(all_documents.values())

    def list_resources(self, query: str | None = None) -> list[Resource]:
        """List resources (knowledge bases) from the knowledge base service."""
        method = "POST"
        path = "/api/knowledge/collection/list"
        info_req = self.prepare_request(method=method, path=path)
        rsp = requests.request(
            method=info_req.method,
            url=f"http://{self.api_url}{info_req.path}",
            headers=info_req.headers,
            data=info_req.body,
            timeout=30,
        )
        try:
            response = json.loads(rsp.text)
        except json.JSONDecodeError as e:
            msg = f"Failed to parse JSON response: {e}"
            raise ValueError(msg) from e

        if response["code"] != 0:
            msg = f"Failed to list resources: {response['message']}"
            raise RuntimeError(msg)

        resources = []
        rsp_data = response.get("data", {})
        collection_list = rsp_data.get("collection_list", [])
        for item in collection_list:
            collection_name = item.get("collection_name", "")
            description = item.get("description", "")

            if query and query.lower() not in collection_name.lower():
                continue

            resource_id = item.get("resource_id", "")
            resource = Resource(
                uri=f"rag://dataset/{resource_id}",
                title=collection_name,
                description=description,
            )
            resources.append(resource)

        return resources


def parse_uri(uri: str) -> tuple[str, str]:
    parsed = urlparse(uri)
    if parsed.scheme != "rag":
        msg = f"Invalid URI: {uri}"
        raise ValueError(msg)
    return parsed.path.split("/")[1], parsed.fragment

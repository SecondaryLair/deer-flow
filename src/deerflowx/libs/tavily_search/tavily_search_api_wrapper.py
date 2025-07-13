# Copyright (c) 2025 Bytedance Ltd. and/or its affiliates
# Copyright (c) 2025 Bytedance Ltd. and/or its affiliates
# SPDX-License-Identifier: MIT

import json
from dataclasses import dataclass

import aiohttp
import requests
from langchain_community.utilities.tavily_search import (
    TavilySearchAPIWrapper as OriginalTavilySearchAPIWrapper,
)

TAVILY_API_URL = "https://api.tavily.com"
HTTP_OK = 200


@dataclass
class SearchParams:
    """Parameters for Tavily search."""

    max_results: int | None = 5
    search_depth: str | None = "advanced"
    include_domains: list[str] | None = None
    exclude_domains: list[str] | None = None
    include_answer: bool | None = False
    include_raw_content: bool | None = False
    include_images: bool | None = False
    include_image_descriptions: bool | None = False


class EnhancedTavilySearchAPIWrapper(OriginalTavilySearchAPIWrapper):
    def raw_results(  # noqa: PLR0913
        self,
        query: str,
        max_results: int | None = 5,
        search_depth: str | None = "advanced",
        include_domains: list[str] | None = None,
        exclude_domains: list[str] | None = None,
        include_answer: bool | None = False,
        include_raw_content: bool | None = False,
        include_images: bool | None = False,
        include_image_descriptions: bool | None = False,
    ) -> dict:
        # Convert parameters to SearchParams for internal use
        params = SearchParams(
            max_results=max_results,
            search_depth=search_depth,
            include_domains=include_domains,
            exclude_domains=exclude_domains,
            include_answer=include_answer,
            include_raw_content=include_raw_content,
            include_images=include_images,
            include_image_descriptions=include_image_descriptions,
        )

        return self._raw_results_internal(query, params)

    def _raw_results_internal(
        self,
        query: str,
        params: SearchParams,
    ) -> dict:
        exclude_domains = params.exclude_domains or []
        include_domains = params.include_domains or []

        request_params = {
            "api_key": self.tavily_api_key.get_secret_value(),
            "query": query,
            "max_results": params.max_results,
            "search_depth": params.search_depth,
            "include_domains": include_domains,
            "exclude_domains": exclude_domains,
            "include_answer": params.include_answer,
            "include_raw_content": params.include_raw_content,
            "include_images": params.include_images,
            "include_image_descriptions": params.include_image_descriptions,
        }
        response = requests.post(
            # type: ignore[arg-type]
            f"{TAVILY_API_URL}/search",
            json=request_params,
            timeout=30,
        )
        response.raise_for_status()
        return response.json()

    async def raw_results_async(
        self,
        query: str,
        params: SearchParams | None = None,
    ) -> dict:
        """Get results from the Tavily Search API asynchronously."""
        if params is None:
            params = SearchParams()

        return await self._raw_results_async_internal(query, params)

    async def _raw_results_async_internal(
        self,
        query: str,
        params: SearchParams,
    ) -> dict:
        """Get results from the Tavily Search API asynchronously."""
        exclude_domains = params.exclude_domains or []
        include_domains = params.include_domains or []

        # Function to perform the API call
        async def fetch() -> str:
            request_params = {
                "api_key": self.tavily_api_key.get_secret_value(),
                "query": query,
                "max_results": params.max_results,
                "search_depth": params.search_depth,
                "include_domains": include_domains,
                "exclude_domains": exclude_domains,
                "include_answer": params.include_answer,
                "include_raw_content": params.include_raw_content,
                "include_images": params.include_images,
                "include_image_descriptions": params.include_image_descriptions,
            }
            async with (
                aiohttp.ClientSession(trust_env=True) as session,
                session.post(f"{TAVILY_API_URL}/search", json=request_params) as res,
            ):
                if res.status == HTTP_OK:
                    return await res.text()
                msg = f"Error {res.status}: {res.reason}"
                raise RuntimeError(msg)

        results_json_str = await fetch()
        return json.loads(results_json_str)

    def clean_results_with_images(self, raw_results: dict[str, list[dict]]) -> list[dict]:
        results = raw_results["results"]
        """Clean results from Tavily Search API."""
        clean_results = []
        for result in results:
            clean_result = {
                "type": "page",
                "title": result["title"],
                "url": result["url"],
                "content": result["content"],
                "score": result["score"],
            }
            if raw_content := result.get("raw_content"):
                clean_result["raw_content"] = raw_content
            clean_results.append(clean_result)
        images = raw_results["images"]
        for image in images:
            clean_result = {
                "type": "image",
                "image_url": image["url"],
                "image_description": image["description"],
            }
            clean_results.append(clean_result)
        return clean_results

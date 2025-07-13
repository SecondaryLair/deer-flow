# Copyright (c) 2025 Bytedance Ltd. and/or its affiliates
# SPDX-License-Identifier: MIT
"""Web search tools and utilities for different search engines."""

import logging
import os

from langchain_community.tools import BraveSearch, DuckDuckGoSearchResults
from langchain_community.tools.arxiv import ArxivQueryRun
from langchain_community.utilities import ArxivAPIWrapper, BraveSearchWrapper
from langchain_core.tools import BaseTool

from deerflowx.config import SELECTED_SEARCH_ENGINE, SearchEngine
from deerflowx.libs.tavily_search.tavily_search_results_with_images import (
    TavilySearchResultsWithImages,
)
from deerflowx.tools.decorators import create_logged_tool

logger = logging.getLogger(__name__)

# Create logged versions of the search tools with proper type annotations
LoggedTavilySearch: type[TavilySearchResultsWithImages] = create_logged_tool(TavilySearchResultsWithImages)
LoggedDuckDuckGoSearch: type[DuckDuckGoSearchResults] = create_logged_tool(DuckDuckGoSearchResults)
LoggedBraveSearch: type[BraveSearch] = create_logged_tool(BraveSearch)
LoggedArxivSearch: type[ArxivQueryRun] = create_logged_tool(ArxivQueryRun)


# Get the selected search tool
def get_web_search_tool(max_search_results: int, /) -> BaseTool:
    if SearchEngine.TAVILY.value == SELECTED_SEARCH_ENGINE:
        return LoggedTavilySearch(
            name="web_search",
            max_results=max_search_results,
            include_raw_content=True,
            include_images=True,
            include_image_descriptions=True,
        )
    if SearchEngine.DUCKDUCKGO.value == SELECTED_SEARCH_ENGINE:
        return LoggedDuckDuckGoSearch(
            name="web_search",
            num_results=max_search_results,
        )
    if SearchEngine.BRAVE_SEARCH.value == SELECTED_SEARCH_ENGINE:
        return LoggedBraveSearch(
            name="web_search",
            search_wrapper=BraveSearchWrapper(
                api_key=os.getenv("BRAVE_SEARCH_API_KEY", ""),
                search_kwargs={"count": max_search_results},
            ),
        )
    if SearchEngine.ARXIV.value == SELECTED_SEARCH_ENGINE:
        return LoggedArxivSearch(
            name="web_search",
            api_wrapper=ArxivAPIWrapper(
                top_k_results=max_search_results,
                load_max_docs=max_search_results,
                load_all_available_meta=True,
            ),
        )
    msg = f"Unsupported search engine: {SELECTED_SEARCH_ENGINE}"
    raise ValueError(msg)

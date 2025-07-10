# Copyright (c) 2025 Bytedance Ltd. and/or its affiliates
# SPDX-License-Identifier: MIT

import os
from unittest.mock import patch

import pytest

from deerflowx.config import SearchEngine
from deerflowx.tools.search import get_web_search_tool


class TestGetWebSearchTool:
    @patch("deerflowx.tools.search.SELECTED_SEARCH_ENGINE", SearchEngine.TAVILY.value)
    @patch("deerflowx.tools.search.LoggedTavilySearch")
    def test_get_web_search_tool_tavily(self, mock_tavily):
        mock_tool = mock_tavily.return_value
        tool = get_web_search_tool(5)  # Use positional argument

        # Verify correct class was called with correct parameters
        mock_tavily.assert_called_once_with(
            name="web_search",
            max_results=5,
            include_raw_content=True,
            include_images=True,
            include_image_descriptions=True,
        )
        assert tool == mock_tool

    @patch("deerflowx.tools.search.SELECTED_SEARCH_ENGINE", SearchEngine.DUCKDUCKGO.value)
    @patch("deerflowx.tools.search.LoggedDuckDuckGoSearch")
    def test_get_web_search_tool_duckduckgo(self, mock_duckduckgo):
        mock_tool = mock_duckduckgo.return_value
        tool = get_web_search_tool(3)  # Use positional argument

        # Verify correct class was called with correct parameters
        mock_duckduckgo.assert_called_once_with(
            name="web_search",
            num_results=3,
        )
        assert tool == mock_tool

    @patch("deerflowx.tools.search.SELECTED_SEARCH_ENGINE", SearchEngine.BRAVE_SEARCH.value)
    @patch("deerflowx.tools.search.LoggedBraveSearch")
    @patch("deerflowx.tools.search.BraveSearchWrapper")
    @patch.dict(os.environ, {"BRAVE_SEARCH_API_KEY": "test_api_key"})
    def test_get_web_search_tool_brave(self, mock_wrapper_class, mock_brave):
        mock_wrapper = mock_wrapper_class.return_value
        mock_tool = mock_brave.return_value
        tool = get_web_search_tool(4)  # Use positional argument

        # Verify wrapper was created correctly
        mock_wrapper_class.assert_called_once_with(
            api_key="test_api_key",
            search_kwargs={"count": 4},
        )

        # Verify tool was created correctly
        mock_brave.assert_called_once_with(
            name="web_search",
            search_wrapper=mock_wrapper,
        )
        assert tool == mock_tool

    @patch("deerflowx.tools.search.SELECTED_SEARCH_ENGINE", SearchEngine.ARXIV.value)
    @patch("deerflowx.tools.search.LoggedArxivSearch")
    @patch("deerflowx.tools.search.ArxivAPIWrapper")
    def test_get_web_search_tool_arxiv(self, mock_wrapper_class, mock_arxiv):
        mock_wrapper = mock_wrapper_class.return_value
        mock_tool = mock_arxiv.return_value
        tool = get_web_search_tool(2)  # Use positional argument

        # Verify wrapper was created correctly
        mock_wrapper_class.assert_called_once_with(
            top_k_results=2,
            load_max_docs=2,
            load_all_available_meta=True,
        )

        # Verify tool was created correctly
        mock_arxiv.assert_called_once_with(
            name="web_search",
            api_wrapper=mock_wrapper,
        )
        assert tool == mock_tool

    @patch("deerflowx.tools.search.SELECTED_SEARCH_ENGINE", "unsupported_engine")
    def test_get_web_search_tool_unsupported_engine(self):
        with pytest.raises(ValueError, match="Unsupported search engine: unsupported_engine"):
            get_web_search_tool(1)  # Use positional argument

    @patch("deerflowx.tools.search.SELECTED_SEARCH_ENGINE", SearchEngine.BRAVE_SEARCH.value)
    @patch("deerflowx.tools.search.LoggedBraveSearch")
    @patch("deerflowx.tools.search.BraveSearchWrapper")
    @patch.dict(os.environ, {}, clear=True)
    def test_get_web_search_tool_brave_no_api_key(self, mock_wrapper_class, mock_brave):
        mock_wrapper = mock_wrapper_class.return_value
        mock_tool = mock_brave.return_value
        tool = get_web_search_tool(1)  # Use positional argument

        # Verify wrapper was created with empty API key
        mock_wrapper_class.assert_called_once_with(
            api_key="",
            search_kwargs={"count": 1},
        )

        # Verify tool was created correctly
        mock_brave.assert_called_once_with(
            name="web_search",
            search_wrapper=mock_wrapper,
        )
        assert tool == mock_tool

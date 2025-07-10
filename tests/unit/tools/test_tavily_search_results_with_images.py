# Copyright (c) 2025 Bytedance Ltd. and/or its affiliates
# SPDX-License-Identifier: MIT

import pytest

from deerflowx.tools.tavily_search.tavily_search_results_with_images import (
    TavilySearchResultsWithImages,
)


def test_tavily_search_results_with_images_initialization():
    """Test that TavilySearchResultsWithImages can be initialized properly."""
    tool = TavilySearchResultsWithImages()
    assert tool.max_results == 5  # default value
    assert tool.include_answer is False  # default value
    assert tool.include_images is False  # default value


def test_tavily_search_results_with_images_custom_params():
    """Test that TavilySearchResultsWithImages can be initialized with custom parameters."""
    tool = TavilySearchResultsWithImages(
        max_results=10, include_answer=True, include_images=True, include_image_descriptions=True
    )
    assert tool.max_results == 10
    assert tool.include_answer is True
    assert tool.include_images is True
    assert tool.include_image_descriptions is True

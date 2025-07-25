# Copyright (c) 2025 Bytedance Ltd. and/or its affiliates
# SPDX-License-Identifier: MIT
"""Web crawling tools for extracting content from URLs."""

import logging
from typing import Annotated

from langchain_core.tools import tool

from deerflowx.libs.crawler import Crawler

from .decorators import log_io

logger = logging.getLogger(__name__)


@tool
@log_io
def crawl_tool(
    url: Annotated[str, "The url to crawl."],
) -> str:
    """Use this to crawl a url and get a readable content in markdown format."""
    try:
        crawler = Crawler()
        article = crawler.crawl(url)
        return {"url": url, "crawled_content": article.to_markdown()[:1000]}
    except BaseException as e:
        error_msg = f"Failed to crawl. Error: {e!r}"
        logger.exception(error_msg)
        return error_msg

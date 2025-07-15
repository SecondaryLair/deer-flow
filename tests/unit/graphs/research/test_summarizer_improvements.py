"""Test improvements for summarizer functionality."""

from unittest.mock import MagicMock, patch

import pytest
from langchain_text_splitters import TokenTextSplitter

from deerflowx.graphs.research.graph.nodes.summarizer import (
    split_text_into_chunks,
)


class TestSummarizerImprovements:
    """测试摘要器的改进功能."""

    def test_split_text_into_chunks_with_langchain_splitter(self):
        """测试使用 LangChain TokenTextSplitter 的文本分块."""

        text = "This is a test text. " * 100  # 重复文本以确保分块
        chunk_size = 50
        overlap = 10

        chunks = split_text_into_chunks(text, chunk_size, overlap)

        assert len(chunks) > 1
        assert all(isinstance(chunk, str) for chunk in chunks)
        assert all(chunk.strip() for chunk in chunks)

    def test_split_text_empty_input(self):
        """测试空输入的处理."""
        chunks = split_text_into_chunks("", 100, 10)
        assert chunks == []

    def test_split_text_whitespace_only(self):
        """测试只包含空白字符的输入."""
        chunks = split_text_into_chunks("   \n\t  ", 100, 10)
        assert chunks == []

    def test_split_text_short_content(self):
        """测试短内容（小于chunk_size）的处理."""
        short_text = "Short text"
        chunks = split_text_into_chunks(short_text, 1000, 100)

        assert len(chunks) >= 1
        if len(chunks) == 1:
            assert chunks[0] == short_text

    @patch("deerflowx.graphs.research.graph.nodes.summarizer.TokenTextSplitter")
    def test_split_text_with_mocked_splitter(self, mock_splitter_class):
        """测试使用模拟的 TokenTextSplitter."""

        mock_splitter = MagicMock()
        mock_splitter.split_text.return_value = ["chunk1", "chunk2", "chunk3"]
        mock_splitter_class.return_value = mock_splitter

        text = "Test text for splitting"
        chunk_size = 100
        overlap = 20

        result = split_text_into_chunks(text, chunk_size, overlap)

        mock_splitter_class.assert_called_once_with(chunk_size=chunk_size, chunk_overlap=overlap)
        mock_splitter.split_text.assert_called_once_with(text)
        assert result == ["chunk1", "chunk2", "chunk3"]

    @patch("deerflowx.graphs.research.graph.nodes.summarizer.TokenTextSplitter")
    def test_split_text_fallback_for_empty_result(self, mock_splitter_class):
        """测试当 TokenTextSplitter 返回空结果时的回退逻辑."""

        mock_splitter = MagicMock()
        mock_splitter.split_text.return_value = []
        mock_splitter_class.return_value = mock_splitter

        text = "Test text"
        result = split_text_into_chunks(text, 100, 20)

        assert result == [text]

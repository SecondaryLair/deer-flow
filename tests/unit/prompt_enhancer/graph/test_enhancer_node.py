# Copyright (c) 2025 Bytedance Ltd. and/or its affiliates
# SPDX-License-Identifier: MIT

from unittest.mock import MagicMock, patch

import pytest
from langchain.schema import HumanMessage, SystemMessage

from deerflowx.config.report_style import ReportStyle
from deerflowx.prompt_enhancer.graph.enhancer_node import prompt_enhancer_node
from deerflowx.prompt_enhancer.graph.state import PromptEnhancerState


@pytest.fixture
def mock_llm():
    """Mock LLM that returns a test response."""
    llm = MagicMock()
    llm.invoke.return_value = MagicMock(content="Enhanced test prompt")
    return llm


@pytest.fixture
def mock_messages():
    """Mock messages returned by apply_prompt_template."""
    return [
        SystemMessage(content="System prompt template"),
        HumanMessage(content="Test human message"),
    ]


class TestPromptEnhancerNode:
    """Test cases for prompt_enhancer_node function."""

    @pytest.mark.asyncio
    @patch("deerflowx.prompt_enhancer.graph.enhancer_node.get_llm_by_type")
    @patch("deerflowx.prompt_enhancer.graph.enhancer_node.AGENT_LLM_MAP", {"prompt_enhancer": "basic"})
    async def test_basic_prompt_enhancement(self, mock_get_llm, mock_llm, mock_messages):
        """Test basic prompt enhancement without context or report style."""
        mock_get_llm.return_value = mock_llm

        state = PromptEnhancerState(prompt="Write about AI", context=None, report_style=None, output=None)

        result = await prompt_enhancer_node(state)

        # Verify LLM was called
        mock_get_llm.assert_called_once_with("basic")
        mock_llm.invoke.assert_called_once()

        # Verify result
        assert result == {"enhanced_prompt": "Enhanced test prompt"}

    @pytest.mark.asyncio
    @patch("deerflowx.prompt_enhancer.graph.enhancer_node.get_llm_by_type")
    @patch(
        "deerflowx.prompt_enhancer.graph.enhancer_node.AGENT_LLM_MAP",
        {"prompt_enhancer": "basic"},
    )
    async def test_prompt_enhancement_with_report_style(self, mock_get_llm, mock_llm):
        """Test prompt enhancement with report style."""
        mock_get_llm.return_value = mock_llm

        state = PromptEnhancerState(
            prompt="Write about AI", context=None, report_style=ReportStyle.ACADEMIC, output=None
        )

        result = await prompt_enhancer_node(state)

        # Verify LLM was called
        mock_get_llm.assert_called_once_with("basic")
        mock_llm.invoke.assert_called_once()

        assert result == {"enhanced_prompt": "Enhanced test prompt"}

    @pytest.mark.asyncio
    @patch("deerflowx.prompt_enhancer.graph.enhancer_node.get_llm_by_type")
    @patch(
        "deerflowx.prompt_enhancer.graph.enhancer_node.AGENT_LLM_MAP",
        {"prompt_enhancer": "basic"},
    )
    async def test_prompt_enhancement_with_context(self, mock_get_llm, mock_llm):
        """Test prompt enhancement with additional context."""
        mock_get_llm.return_value = mock_llm

        state = PromptEnhancerState(
            prompt="Write about AI", context="Focus on machine learning applications", report_style=None, output=None
        )

        result = await prompt_enhancer_node(state)

        # Verify LLM was called
        mock_get_llm.assert_called_once_with("basic")
        mock_llm.invoke.assert_called_once()

        # Verify context was included in the message
        call_args = mock_llm.invoke.call_args
        message_content = call_args[0][0][0].content
        assert "Focus on machine learning applications" in message_content

        assert result == {"enhanced_prompt": "Enhanced test prompt"}

    @pytest.mark.asyncio
    @patch("deerflowx.prompt_enhancer.graph.enhancer_node.get_llm_by_type")
    @patch(
        "deerflowx.prompt_enhancer.graph.enhancer_node.AGENT_LLM_MAP",
        {"prompt_enhancer": "basic"},
    )
    async def test_error_handling(self, mock_get_llm, mock_llm):
        """Test error handling when LLM call fails."""
        mock_get_llm.return_value = mock_llm

        # Mock LLM to raise an exception
        mock_llm.invoke.side_effect = Exception("LLM error")

        state = PromptEnhancerState(prompt="Test prompt", context=None, report_style=None, output=None)
        result = await prompt_enhancer_node(state)

        # Should return original prompt on error
        assert result == {"enhanced_prompt": "Test prompt"}

    @pytest.mark.asyncio
    @patch("deerflowx.prompt_enhancer.graph.enhancer_node.get_llm_by_type")
    @patch(
        "deerflowx.prompt_enhancer.graph.enhancer_node.AGENT_LLM_MAP",
        {"prompt_enhancer": "basic"},
    )
    async def test_template_error_handling(self, mock_get_llm, mock_llm):
        """Test error handling when template application fails."""
        mock_get_llm.return_value = mock_llm

        # Mock LLM to raise an exception
        mock_llm.invoke.side_effect = Exception("Template error")

        state = PromptEnhancerState(prompt="Test prompt", context=None, report_style=None, output=None)
        result = await prompt_enhancer_node(state)

        # Should return original prompt on error
        assert result == {"enhanced_prompt": "Test prompt"}

    @pytest.mark.asyncio
    @patch("deerflowx.prompt_enhancer.graph.enhancer_node.get_llm_by_type")
    @patch(
        "deerflowx.prompt_enhancer.graph.enhancer_node.AGENT_LLM_MAP",
        {"prompt_enhancer": "basic"},
    )
    async def test_prefix_removal(self, mock_get_llm, mock_llm):
        """Test that common prefixes are removed from LLM response."""
        mock_get_llm.return_value = mock_llm

        # Test different prefixes that should be removed
        test_cases = [
            "Enhanced Prompt: This is the enhanced prompt",
            "Enhanced prompt: This is the enhanced prompt",
            "Here's the enhanced prompt: This is the enhanced prompt",
            "Here is the enhanced prompt: This is the enhanced prompt",
            "**Enhanced Prompt**: This is the enhanced prompt",
            "**Enhanced prompt**: This is the enhanced prompt",
        ]

        for response_with_prefix in test_cases:
            mock_llm.invoke.return_value = MagicMock(content=response_with_prefix)

            state = PromptEnhancerState(prompt="Test prompt", context=None, report_style=None, output=None)
            result = await prompt_enhancer_node(state)

            assert result == {"enhanced_prompt": "This is the enhanced prompt"}

    @pytest.mark.asyncio
    @patch("deerflowx.prompt_enhancer.graph.enhancer_node.get_llm_by_type")
    @patch(
        "deerflowx.prompt_enhancer.graph.enhancer_node.AGENT_LLM_MAP",
        {"prompt_enhancer": "basic"},
    )
    async def test_whitespace_handling(self, mock_get_llm, mock_llm):
        """Test that whitespace is properly handled in responses."""
        mock_get_llm.return_value = mock_llm

        # Test response with extra whitespace
        mock_llm.invoke.return_value = MagicMock(content="   Enhanced prompt with whitespace   ")

        state = PromptEnhancerState(prompt="Test prompt", context=None, report_style=None, output=None)
        result = await prompt_enhancer_node(state)

        # Should strip whitespace
        assert result == {"enhanced_prompt": "Enhanced prompt with whitespace"}

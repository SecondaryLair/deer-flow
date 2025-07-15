# Copyright (c) 2025 Bytedance Ltd. and/or its affiliates
# SPDX-License-Identifier: MIT

from typing import TYPE_CHECKING, cast
from unittest.mock import AsyncMock, patch

import pytest

from deerflowx.config.configuration import Configuration
from deerflowx.graphs.research.graph.nodes.summarizer import ChunkState, map_summarize_chunk, reduce_summaries
from deerflowx.graphs.research.graph.nodes.tokens_evaluator import token_evaluator_node
from deerflowx.prompts.planner_model import Plan

if TYPE_CHECKING:
    from deerflowx.graphs.research.graph.state import State


@pytest.fixture
def mock_config():
    """创建模拟配置."""
    return {
        "configurable": {
            "max_observations_tokens": 120000,
            "compression_safety_margin": 0.8,
            "summarizer_chunk_size": 10000,
            "summarizer_chunk_overlap": 500,
            "summarizer_enable_second_pass": True,
        }
    }


@pytest.fixture
def test_plan():
    """创建测试用的Plan对象."""
    return Plan(
        locale="zh-CN",
        has_enough_context=True,
        thought="研究人工智能在教育领域的应用",
        title="AI教育应用研究",
        steps=[],
    )


@pytest.fixture
def small_observations():
    """小型observations，不需要压缩."""
    return ["这是一个简短的观察结果"]


@pytest.fixture
def large_observations():
    """大型observations，需要压缩."""

    long_text = "这是一个很长的研究观察结果。" * 6000  # 重复足够多次以超过阈值
    return [long_text]


class TestTokenEstimator:
    """测试Token估算器节点."""

    @pytest.mark.asyncio
    @patch("deerflowx.graphs.research.graph.nodes.tokens_evaluator.get_llm_by_type")
    async def test_small_observations_direct_route(self, mock_llm_get, mock_config, small_observations):
        """测试小型observations直接路由到reporter."""

        from unittest.mock import MagicMock

        mock_llm = MagicMock()
        mock_llm.get_num_tokens.return_value = 50
        mock_llm_get.return_value = mock_llm

        state = {
            "observations": small_observations,
        }

        result = await token_evaluator_node(cast("State", state), mock_config)

        assert result["compression_decision"] == "direct_to_reporter"
        assert result["estimated_tokens"] == 50
        assert "below threshold" in result["decision_reason"]

    @pytest.mark.asyncio
    @patch("deerflowx.graphs.research.graph.nodes.tokens_evaluator.get_llm_by_type")
    async def test_large_observations_compression_route(self, mock_llm_get, mock_config, large_observations):
        """测试大型observations路由到压缩."""

        from unittest.mock import MagicMock

        mock_llm = MagicMock()
        mock_llm.get_num_tokens.return_value = 100000
        mock_llm_get.return_value = mock_llm

        state = {
            "observations": large_observations,
        }

        result = await token_evaluator_node(cast("State", state), mock_config)

        assert result["compression_decision"] == "compress_first"
        assert result["estimated_tokens"] == 100000
        assert "exceeds threshold" in result["decision_reason"]

    @pytest.mark.asyncio
    @patch("deerflowx.graphs.research.graph.nodes.tokens_evaluator.get_llm_by_type")
    async def test_empty_observations(self, mock_llm_get, mock_config):
        """测试空observations的处理."""
        from unittest.mock import MagicMock

        mock_llm = MagicMock()
        mock_llm_get.return_value = mock_llm

        state = {
            "observations": [],
        }

        result = await token_evaluator_node(cast("State", state), mock_config)

        assert result["compression_decision"] == "direct_to_reporter"
        assert result["estimated_tokens"] == 0
        assert "No observations" in result["decision_reason"]

        mock_llm.get_num_tokens.assert_not_called()


class TestSummarizer:
    """测试摘要器组件."""

    @pytest.mark.asyncio
    @patch("deerflowx.graphs.research.graph.nodes.summarizer.get_llm_by_type")
    async def test_map_summarize_chunk(self, mock_llm, mock_config):
        """测试单个块的摘要处理."""

        mock_response = AsyncMock()
        mock_response.content = "这是摘要结果"
        mock_llm.return_value.ainvoke = AsyncMock(return_value=mock_response)

        chunk_state = {
            "chunk_text": "这是一段需要摘要的文本",
            "task_context": "研究任务上下文",
            "chunk_index": 0,
        }

        result = await map_summarize_chunk(cast("ChunkState", chunk_state), mock_config)

        assert "summaries" in result
        assert len(result["summaries"]) == 1
        assert result["summaries"][0] == "这是摘要结果"

        mock_llm.return_value.ainvoke.assert_called_once()
        call_args = mock_llm.return_value.ainvoke.call_args[0][0]
        assert len(call_args) == 2

    @pytest.mark.asyncio
    @patch("deerflowx.graphs.research.graph.nodes.summarizer.get_llm_by_type")
    async def test_reduce_summaries_no_second_pass(self, mock_llm, mock_config, test_plan):
        """测试不进行二次压缩的摘要合并."""

        mock_config["configurable"]["summarizer_enable_second_pass"] = False

        state = {
            "summaries": ["摘要1", "摘要2", "摘要3"],
            "current_plan": test_plan,
        }

        result = await reduce_summaries(cast("State", state), mock_config)

        assert "summarized_observations" in result
        assert "摘要1\n\n摘要2\n\n摘要3" == result["summarized_observations"]

        mock_llm.return_value.ainvoke.assert_not_called()

    @pytest.mark.asyncio
    @patch("deerflowx.graphs.research.graph.nodes.summarizer.get_llm_by_type")
    async def test_reduce_summaries_with_second_pass(self, mock_llm, mock_config, test_plan):
        """测试进行二次压缩的摘要合并."""

        mock_response = AsyncMock()
        mock_response.content = "最终整合的摘要"
        mock_llm_instance = AsyncMock()
        mock_llm_instance.ainvoke = AsyncMock(return_value=mock_response)

        from unittest.mock import MagicMock

        mock_llm_instance.get_num_tokens = MagicMock(return_value=80000)
        mock_llm.return_value = mock_llm_instance

        long_summaries = ["很长的摘要内容 " * 100] * 3

        state = {
            "summaries": long_summaries,
            "current_plan": test_plan,
        }

        result = await reduce_summaries(cast("State", state), mock_config)

        assert "summarized_observations" in result
        assert result["summarized_observations"] == "最终整合的摘要"

        mock_llm_instance.get_num_tokens.assert_called_once()
        mock_llm_instance.ainvoke.assert_called_once()

    @pytest.mark.asyncio
    @patch("deerflowx.graphs.research.graph.nodes.summarizer.get_llm_by_type")
    async def test_reduce_summaries_empty(self, mock_llm, mock_config, test_plan):
        """测试空摘要列表的处理."""
        state = {
            "summaries": [],
            "current_plan": test_plan,
        }

        result = await reduce_summaries(cast("State", state), mock_config)

        assert result["summarized_observations"] == ""

        mock_llm.return_value.get_num_tokens.assert_not_called()


class TestGraphRouting:
    """测试图路由逻辑."""

    def test_route_after_token_estimation_direct(self):
        """测试token估算后的直接路由."""
        from deerflowx.graphs.research.graph.builder import route_after_token_estimation

        state = {"compression_decision": "direct_to_reporter"}
        result = route_after_token_estimation(cast("State", state))
        assert result == "reporter"

    def test_route_after_token_estimation_compress(self):
        """测试token估算后的压缩路由."""
        from deerflowx.graphs.research.graph.builder import route_after_token_estimation

        state = {"compression_decision": "compress_first"}
        result = route_after_token_estimation(cast("State", state))
        assert result == "summarizer"

    def test_route_after_token_estimation_default(self):
        """测试token估算后的默认路由."""
        from deerflowx.graphs.research.graph.builder import route_after_token_estimation

        state = {}
        result = route_after_token_estimation(cast("State", state))
        assert result == "reporter"  # 默认路由

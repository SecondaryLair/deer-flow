# Copyright (c) 2025 Bytedance Ltd. and/or its affiliates
# SPDX-License-Identifier: MIT

import logging
from typing import Any

from langchain_core.messages.utils import count_tokens_approximately
from langchain_core.runnables import RunnableConfig

from deerflowx.config.agents import AGENT_LLM_MAP
from deerflowx.config.configuration import Configuration
from deerflowx.graphs.research.graph.state import State
from deerflowx.utils.llms.llm import get_llm_by_type
from deerflowx.utils.node_base import NodeBase

logger = logging.getLogger(__name__)


async def token_evaluator_node(state: State, config: RunnableConfig) -> dict[str, Any]:
    """Token estimator node that estimates token count and decides routing strategy."""
    logger.info("Token estimator analyzing observations size")

    configurable = Configuration.from_runnable_config(config)
    observations = state.get("observations", [])

    if not observations:
        logger.info("No observations found, routing directly to reporter")
        return {
            "compression_decision": "direct_to_reporter",
            "estimated_tokens": 0,
            "decision_reason": "No observations to process",
        }

    valid_observations = [obs.strip() for obs in observations if obs.strip()]

    if not valid_observations:
        logger.info("No valid observations found after filtering, routing directly to reporter")
        return {
            "compression_decision": "direct_to_reporter",
            "estimated_tokens": 0,
            "decision_reason": "No valid texts to process",
        }

    llm = get_llm_by_type(AGENT_LLM_MAP["researcher"])

    combined_text = "\n".join(valid_observations)

    try:
        token_count = llm.get_num_tokens(combined_text)
    except Exception as e:
        logger.warning(f"Error calculating tokens with LLM: {e}, using approximate calculation")

        token_count = count_tokens_approximately(combined_text)

    threshold = configurable.max_observations_tokens
    safety_margin = configurable.compression_safety_margin
    effective_threshold = int(threshold * safety_margin)

    if token_count <= effective_threshold:
        decision = "direct_to_reporter"
        reason = f"Token count ({token_count}) below threshold ({effective_threshold}), no compression needed"
        logger.info(f"Direct routing: {reason}")
    else:
        decision = "compress_first"
        reason = f"Token count ({token_count}) exceeds threshold ({effective_threshold}), compression required"
        logger.info(f"Compression routing: {reason}")

    return {
        "compression_decision": decision,
        "estimated_tokens": token_count,
        "decision_reason": reason,
    }


class TokensEvaluatorNode(NodeBase):
    """Token evaluator node that estimates token count and decides routing strategy."""

    @classmethod
    def name(cls) -> str:
        return "tokens_evaluator"

    @classmethod
    async def action(cls, state: State, config: RunnableConfig) -> dict[str, Any]:
        """Tokens evaluator node action."""
        return await token_evaluator_node(state, config)

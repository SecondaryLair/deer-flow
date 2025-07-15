# Copyright (c) 2025 Bytedance Ltd. and/or its affiliates
# SPDX-License-Identifier: MIT

import logging
import operator
from typing import Annotated, Any

from langchain_core.messages import HumanMessage, SystemMessage
from langchain_core.messages.utils import count_tokens_approximately
from langchain_core.runnables import RunnableConfig
from langchain_text_splitters import TokenTextSplitter
from langgraph.types import Send
from typing_extensions import TypedDict

from deerflowx.config.agents import AGENT_LLM_MAP
from deerflowx.config.configuration import Configuration
from deerflowx.graphs.research.graph.state import State
from deerflowx.prompts.planner_model import Plan
from deerflowx.utils.llms.llm import get_llm_by_type
from deerflowx.utils.node_base import NodeBase

logger = logging.getLogger(__name__)


class ChunkState(TypedDict):
    """State for individual chunk processing."""

    chunk_text: str
    task_context: str
    chunk_index: int
    summaries: Annotated[list[str], operator.add]


def split_text_into_chunks(text: str, chunk_size: int, overlap: int) -> list[str]:
    """Split text into overlapping chunks using LangChain's TokenTextSplitter."""
    if not text.strip():
        return []

    splitter = TokenTextSplitter(chunk_size=chunk_size, chunk_overlap=overlap)

    chunks = splitter.split_text(text)

    if not chunks:
        return [text]

    return chunks


async def map_summarize_chunk(state: ChunkState, config: RunnableConfig) -> dict[str, Any]:  # noqa: ARG001
    """Map phase: Process individual text chunk and generate summary."""
    try:
        chunk_index = state.get("chunk_index", 0)
        logger.info(f"Processing chunk {chunk_index}")

        chunk_text = state.get("chunk_text", "").strip()
        if not chunk_text:
            logger.warning(f"Chunk {chunk_index} is empty, skipping")
            return {"summaries": [""]}

        task_context = state.get("task_context", "")

        messages = [
            SystemMessage(
                content=(
                    "You are a professional information extraction assistant. Please extract all key facts, data, opinions and citations from the following text based on the given research task. "  # noqa: E501
                    "Ignore marketing rhetoric, navigation links and generic descriptions unrelated to the task. Output in bullet points, maintaining accuracy and completeness."  # noqa: E501
                )
            ),
            HumanMessage(
                content=(
                    f"Research task:{task_context}\n\nPlease extract key information related to the above task from:\n\n{chunk_text}"  # noqa: E501
                )
            ),
        ]

        llm = get_llm_by_type(AGENT_LLM_MAP["researcher"])
        response = await llm.ainvoke(messages)
        summary = response.content
        if isinstance(summary, str):
            summary = summary.strip()
        else:
            summary = str(summary).strip()

        logger.debug(f"Chunk {chunk_index} summarized: {len(summary)} characters")

    except Exception as e:
        chunk_index = state.get("chunk_index", 0)
        logger.exception(f"Error processing chunk {chunk_index}: {e}")

        fallback_text = state.get("chunk_text", "")
        return {"summaries": [fallback_text]}

    else:
        return {"summaries": [summary]}


async def reduce_summaries(state: State, config: RunnableConfig) -> dict[str, Any]:
    """Reduce phase: Combine all summaries and perform second-pass compression."""
    logger.info("Reducing and combining summaries")

    configurable = Configuration.from_runnable_config(config)
    summaries = state.get("summaries", [])
    current_plan = state.get("current_plan")

    if not summaries:
        logger.warning("No summaries to reduce")
        return {"summarized_observations": ""}

    combined_summaries = "\n\n".join(summaries)

    if configurable.summarizer_enable_second_pass:
        try:
            llm = get_llm_by_type(AGENT_LLM_MAP["researcher"])

            try:
                combined_tokens = llm.get_num_tokens(combined_summaries)
            except Exception as e:
                logger.warning(f"Error calculating tokens with LLM: {e}, using approximate calculation")

                combined_tokens = count_tokens_approximately(combined_summaries)

            if combined_tokens > configurable.max_observations_tokens // 2:
                logger.info(f"Performing second-pass compression (current: {combined_tokens} tokens)")

                if isinstance(current_plan, Plan) and current_plan.thought:
                    task_context = current_plan.thought
                else:
                    task_context = str(current_plan)

                messages = [
                    SystemMessage(
                        content=(
                            "You are a professional information integration assistant. Please consolidate the following fragmented summaries into a coherent, concise report. "  # noqa: E501
                            "Retain all key facts, data and opinions, remove duplicate content, and ensure logical flow and completeness."  # noqa: E501
                        )
                    ),
                    HumanMessage(
                        content=(
                            f"Research task: {task_context}\n\nPlease consolidate the following summaries: \n\n{combined_summaries}"  # noqa: E501
                        )
                    ),
                ]

                response = await llm.ainvoke(messages)
                final_summary = response.content
                if isinstance(final_summary, str):
                    final_summary = final_summary.strip()
                else:
                    final_summary = str(final_summary).strip()

                logger.info(f"Second-pass compression completed: {len(final_summary)} characters")
            else:
                logger.info(f"Skipping second-pass compression: {combined_tokens} tokens below threshold")
                final_summary = combined_summaries
        except Exception as e:
            logger.exception(f"Error during second-pass compression: {e}, using combined summaries")
            final_summary = combined_summaries
    else:
        final_summary = combined_summaries

    logger.info(f"Final summarized content: {len(final_summary)} characters")

    return {"summarized_observations": final_summary}


async def summarizer_node(state: State, config: RunnableConfig) -> list[Send]:
    """Summarizer node that orchestrates the Map-Reduce summarization process."""
    logger.info("Summarizer node starting Map-Reduce process")

    configurable = Configuration.from_runnable_config(config)
    observations = state.get("observations", [])
    current_plan = state.get("current_plan")

    if not observations:
        logger.warning("No observations to summarize, creating empty task for reduce phase")

        return [
            Send(
                "map_summarize_chunk",
                {
                    "chunk_text": "",
                    "task_context": "",
                    "chunk_index": 0,
                },
            )
        ]

    combined_text = "\n\n".join(observations)

    if isinstance(current_plan, Plan) and current_plan.thought:
        task_context = current_plan.thought
    else:
        task_context = str(current_plan)

    chunks = split_text_into_chunks(
        combined_text, configurable.summarizer_chunk_size, configurable.summarizer_chunk_overlap
    )

    logger.info(f"Split content into {len(chunks)} chunks for parallel processing")

    chunk_tasks = []
    for i, chunk in enumerate(chunks):
        chunk_tasks.append(
            Send(
                "map_summarize_chunk",
                {
                    "chunk_text": chunk,
                    "task_context": task_context,
                    "chunk_index": i,
                },
            )
        )

    return chunk_tasks


class SummarizerNode(NodeBase):
    """Summarizer node that orchestrates Map-Reduce summarization."""

    @classmethod
    def name(cls) -> str:
        return "summarizer"

    @classmethod
    async def action(cls, state: State, config: RunnableConfig) -> list[Send]:
        """Summarizer node action."""
        return await summarizer_node(state, config)


class MapSummarizeChunkNode(NodeBase):
    """Map node for processing individual chunks."""

    @classmethod
    def name(cls) -> str:
        return "map_summarize_chunk"

    @classmethod
    async def action(cls, state: ChunkState, config: RunnableConfig) -> dict[str, Any]:
        """Map summarize chunk action."""
        return await map_summarize_chunk(state, config)


class ReduceSummariesNode(NodeBase):
    """Reduce node for combining summaries."""

    @classmethod
    def name(cls) -> str:
        return "reduce_summaries"

    @classmethod
    async def action(cls, state: State, config: RunnableConfig) -> dict[str, Any]:
        """Reduce summaries action."""
        return await reduce_summaries(state, config)

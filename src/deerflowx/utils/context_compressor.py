# Copyright (c) 2025 Bytedance Ltd. and/or its affiliates
# SPDX-License-Identifier: MIT
import logging

import litellm
from langchain_core.messages import AIMessage, AnyMessage, BaseMessage, HumanMessage, ToolMessage

from deerflowx.config.agents import AGENT_LLM_MAP
from deerflowx.utils.llms.llm import get_llm_by_type

logger = logging.getLogger(__name__)

# Model name mapping for litellm compatibility
MODEL_NAME_MAPPING = {
    # DeepSeek models
    "deepseek-chat-lite": "deepseek/deepseek-chat",
    "deepseek-chat": "deepseek/deepseek-chat",
    "deepseek-v2": "deepseek/deepseek-v2",
    # Doubao models (use OpenAI-compatible format as fallback)
    "doubao-1-5-pro-32k-250115": "gpt-3.5-turbo",  # Fallback to similar size model
    "doubao-pro-4k": "gpt-3.5-turbo",
    "doubao-pro-32k": "gpt-3.5-turbo",
    "doubao-pro-128k": "gpt-4-turbo",
}

# Default context windows for models not in litellm
DEFAULT_CONTEXT_WINDOWS = {
    "deepseek-chat-lite": 32768,
    "doubao-1-5-pro-32k-250115": 32000,
    "doubao-pro-4k": 4000,
    "doubao-pro-32k": 32000,
    "doubao-pro-128k": 128000,
}


class SmartContextCompressor:
    """A class to intelligently compress conversation history to fit within a model's token limit."""

    def __init__(
        self,
        model_name: str,
        override_token_limit: int | None = None,
        safety_margin: float = 0.8,
    ) -> None:
        """
        Initializes the SmartContextCompressor.

        Args:
            model_name: The name of the LLM model to be used, for token counting and summarization.
            override_token_limit: If provided, this value will be used as the token limit,
                                  ignoring the model's default and the safety margin.
            safety_margin: A factor to reduce the model's max tokens for a safer limit.
                           For example, 0.8 means using 80% of the model's context window.
        """
        self.model_name = model_name
        # Get the litellm-compatible model name for token counting
        self.litellm_model_name = MODEL_NAME_MAPPING.get(model_name, model_name)
        self.summarizer_llm = get_llm_by_type(AGENT_LLM_MAP.get("basic", "basic"))  # Use a basic model for summaries

        if override_token_limit:
            self.token_limit = override_token_limit
            logger.info(f"Using override token limit: {self.token_limit}")
        else:
            self.token_limit = self._get_model_token_limit(model_name, safety_margin)

    def _get_model_token_limit(self, model_name: str, safety_margin: float) -> int:
        """Get the token limit for a model, with fallbacks for unsupported models."""
        try:
            # Try to get from litellm using the mapped model name
            max_tokens = litellm.get_max_tokens(self.litellm_model_name)  # type: ignore[attr-defined]
            if max_tokens:
                token_limit = int(max_tokens * safety_margin)
                logger.info(
                    f"Model '{model_name}' (mapped to '{self.litellm_model_name}') max tokens: {max_tokens}. "
                    f"Using {safety_margin * 100}% safety margin -> limit: {token_limit}"
                )
                return token_limit
        except Exception:
            logger.debug(f"litellm.get_max_tokens failed for model '{self.litellm_model_name}'")

        # Fallback to our predefined context windows
        if model_name in DEFAULT_CONTEXT_WINDOWS:
            max_tokens = DEFAULT_CONTEXT_WINDOWS[model_name]
            token_limit = int(max_tokens * safety_margin)
            logger.info(
                f"Using predefined context window for '{model_name}': {max_tokens} tokens. "
                f"Using {safety_margin * 100}% safety margin -> limit: {token_limit}"
            )
            return token_limit

        # Final fallback
        logger.warning(f"Could not determine max tokens for model '{model_name}'. Defaulting to 28000 tokens.")
        return 28000

    def get_total_tokens(self, messages: list[AnyMessage]) -> int:
        """Calculate the total token count for a list of messages."""
        try:
            litellm_messages = []
            for msg in messages:
                if hasattr(msg, "content") and hasattr(msg, "type"):
                    match msg.type:
                        case "human":
                            role = "user"
                        case "ai":
                            role = "assistant"
                        case "system":
                            role = "system"
                        case "tool":
                            role = "tool"
                        case _:
                            role = "user"

                    litellm_messages.append({"role": role, "content": str(msg.content) if msg.content else ""})

            return litellm.token_counter(model=self.litellm_model_name, messages=litellm_messages)  # type: ignore[attr-defined]
        except Exception:
            logger.debug(f"litellm.token_counter failed for model {self.litellm_model_name}. Text-based approx.")
            text_content = " ".join([str(msg.content) for msg in messages if hasattr(msg, "content")])
            return len(text_content) // 4

    async def compress(self, messages: list[AnyMessage]) -> list[AnyMessage]:
        """
        Compresses the list of messages if its total token count exceeds the limit.

        The method iteratively finds the longest ToolMessage and replaces it with a summary
        until the total token count is within the specified limit.

        Args:
            messages: A list of messages to be compressed.

        Returns:
            A list of messages that is within the token limit.
        """
        if not messages:
            return []

        total_tokens = self.get_total_tokens(messages)
        logger.info(f"Initial token count: {total_tokens}, Token limit: {self.token_limit}")

        while total_tokens > self.token_limit:
            longest_message_index, longest_message = self._find_longest_tool_message(messages)

            if longest_message_index == -1 or not longest_message:
                logger.warning(
                    "Token limit exceeded, but no compressible ToolMessage found. "
                    "The conversation history might be too long."
                )
                break

            # Replace the longest message with a summary
            summary_message = await self._create_summary_message(longest_message, longest_message_index, messages)

            max_tokens = self.get_total_tokens([longest_message])
            logger.info(
                f"Compressing message at index {longest_message_index} "
                f"from {max_tokens} tokens to {self.get_total_tokens([summary_message])} tokens."
            )
            messages[longest_message_index] = summary_message

            total_tokens = self.get_total_tokens(messages)
            logger.info(f"New token count: {total_tokens}")

        logger.info("Compression finished or was not needed.")
        return messages

    def _find_longest_tool_message(self, messages: list[AnyMessage]) -> tuple[int, ToolMessage | None]:
        """Find the longest ToolMessage in the message list."""
        longest_message_index, longest_message = -1, None
        max_tokens = 0

        for i, message in enumerate(messages):
            if isinstance(message, ToolMessage):
                message_tokens = self.get_total_tokens([message])
                if message_tokens > max_tokens:
                    max_tokens = message_tokens
                    longest_message_index = i
                    longest_message = message

        return longest_message_index, longest_message

    async def _create_summary_message(
        self, longest_message: ToolMessage, longest_message_index: int, messages: list[AnyMessage]
    ) -> HumanMessage:
        """Create a summary message to replace the longest message."""
        # Summarize the content of the longest message
        summary_prompt = f"Please summarize the following content concisely:\n\n{longest_message.content}"
        summary_response = await self.summarizer_llm.ainvoke(summary_prompt)

        # Create a summary message to replace the original one
        summary_content = ""
        if isinstance(summary_response, BaseMessage):
            summary_content = str(summary_response.content)
        else:
            summary_content = str(summary_response)

        tool_call_id = longest_message.tool_call_id
        preceding_ai_message_info = self._get_tool_call_context(tool_call_id, longest_message_index, messages)

        return HumanMessage(
            content=(
                f"[Content summary from tool call "
                f"`{tool_call_id}`{preceding_ai_message_info}, "
                f"original length: {self.get_total_tokens([longest_message])} tokens]:\n{summary_content}"
            ),
            name="system",
        )

    def _get_tool_call_context(self, tool_call_id: str, message_index: int, messages: list[AnyMessage]) -> str:
        """Get context information about the tool call that generated the message."""
        preceding_ai_message_info = ""
        for i in range(message_index - 1, -1, -1):
            msg = messages[i]
            if isinstance(msg, AIMessage) and msg.tool_calls:
                for tc in msg.tool_calls:
                    if tc["id"] == tool_call_id:
                        preceding_ai_message_info = f" (in response to `{tc['name']}` call)"
                        break
            if preceding_ai_message_info:
                break
        return preceding_ai_message_info

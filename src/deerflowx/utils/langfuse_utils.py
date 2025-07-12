"""Langfuse utility functions for observability and tracing."""

import logging

from langfuse import Langfuse, get_client
from langfuse.langchain import CallbackHandler

from deerflowx.config.settings import settings

logger = logging.getLogger(__name__)


def get_langfuse_client() -> Langfuse | None:
    """Get configured Langfuse client if settings are valid.

    Returns:
        Langfuse client instance if properly configured, None otherwise
    """
    if not settings.langfuse.is_enabled:
        logger.debug("Langfuse is not enabled - missing required configuration")
        return None

    try:
        client = get_client()

        if client.auth_check():
            logger.info("Langfuse client authenticated successfully")
            return client
        logger.warning("Langfuse authentication failed - check your credentials")
    except Exception:
        logger.exception("Failed to initialize Langfuse client")
        return None
    else:
        return None


def create_langfuse_callback_handler() -> CallbackHandler | None:
    """Create Langfuse CallbackHandler for LangChain integration.

    Returns:
        CallbackHandler instance if Langfuse is enabled, None otherwise
    """
    if not settings.langfuse.is_enabled:
        logger.debug("Langfuse is not enabled - skipping callback handler creation")
        return None

    try:
        handler = CallbackHandler()
        logger.debug("Langfuse CallbackHandler created successfully")
    except Exception:
        logger.exception("Failed to create Langfuse callback handler")
        return None
    else:
        return handler


def is_langfuse_enabled() -> bool:
    """Check if Langfuse is properly configured and enabled.

    Returns:
        True if Langfuse is enabled and configured, False otherwise
    """
    return settings.langfuse.is_enabled

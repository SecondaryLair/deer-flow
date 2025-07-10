# Copyright (c) 2025 Bytedance Ltd. and/or its affiliates
# SPDX-License-Identifier: MIT
"""MCP (Model Context Protocol) utility functions and client management."""

import logging
from dataclasses import dataclass
from datetime import timedelta
from typing import Any, AsyncContextManager

from fastapi import HTTPException
from mcp import ClientSession, StdioServerParameters
from mcp.client.sse import sse_client
from mcp.client.stdio import stdio_client


@dataclass
class MCPServerConfig:
    """Configuration for MCP server connection."""

    server_type: str
    command: str | None = None
    args: list[str] | None = None
    url: str | None = None
    env: dict[str, str] | None = None
    timeout_seconds: int = 60


logger = logging.getLogger(__name__)


async def _get_tools_from_client_session(
    client_context_manager: AsyncContextManager[tuple[Any, Any]],
    timeout_seconds: int = 10,
) -> list:
    """Helper function to get tools from a client session.

    Args:
        client_context_manager: A context manager that returns (read, write) functions
        timeout_seconds: Timeout in seconds for the read operation

    Returns:
        List of available tools from the MCP server

    Raises:
        Exception: If there's an error during the process

    """
    async with (
        client_context_manager as (read, write),
        ClientSession(read, write, read_timeout_seconds=timedelta(seconds=timeout_seconds)) as session,
    ):
        # Initialize the connection
        await session.initialize()
        # List available tools
        listed_tools = await session.list_tools()
        return listed_tools.tools


async def load_mcp_tools(
    config: MCPServerConfig,
) -> list:
    """Load tools from an MCP server.

    Args:
        config: MCP server configuration

    Returns:
        List of available tools from the MCP server

    Raises:
        HTTPException: If there's an error loading the tools

    """
    try:
        if config.server_type == "stdio":
            if not config.command:
                raise HTTPException(status_code=400, detail="Command is required for stdio type")

            server_params = StdioServerParameters(
                command=config.command,  # Executable
                args=config.args,  # Optional command line arguments
                env=config.env,  # Optional environment variables
            )

            return await _get_tools_from_client_session(stdio_client(server_params), config.timeout_seconds)

        if config.server_type == "sse":
            if not config.url:
                raise HTTPException(status_code=400, detail="URL is required for sse type")

            return await _get_tools_from_client_session(sse_client(url=config.url), config.timeout_seconds)

        raise HTTPException(status_code=400, detail=f"Unsupported server type: {config.server_type}")

    except BaseException as e:
        if not isinstance(e, HTTPException):
            logger.exception("Error loading MCP tools")
            raise HTTPException(status_code=500, detail=str(e)) from e
        raise

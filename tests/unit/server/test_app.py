# Copyright (c) 2025 Bytedance Ltd. and/or its affiliates
# SPDX-License-Identifier: MIT

from unittest.mock import MagicMock, patch

import pytest
from fastapi import HTTPException
from fastapi.testclient import TestClient
from langchain_core.messages import AIMessageChunk, ToolMessage
from langgraph.types import Command

from deerflowx.config.report_style import ReportStyle
from deerflowx.server.app import _make_event, app


@pytest.fixture
def client():
    return TestClient(app)


class TestMakeEvent:
    def test_make_event_with_content(self):
        event_type = "message_chunk"
        data = {"content": "Hello", "role": "assistant"}
        result = _make_event(event_type, data)
        expected = 'event: message_chunk\ndata: {"content": "Hello", "role": "assistant"}\n\n'
        assert result == expected

    def test_make_event_with_empty_content(self):
        event_type = "message_chunk"
        data = {"content": "", "role": "assistant"}
        result = _make_event(event_type, data)
        expected = 'event: message_chunk\ndata: {"role": "assistant"}\n\n'
        assert result == expected

    def test_make_event_without_content(self):
        event_type = "tool_calls"
        data = {"role": "assistant", "tool_calls": []}
        result = _make_event(event_type, data)
        expected = 'event: tool_calls\ndata: {"role": "assistant", "tool_calls": []}\n\n'
        assert result == expected


class TestEnhancePromptEndpoint:
    @patch("deerflowx.server.app.build_prompt_enhancer_graph")
    def test_enhance_prompt_success(self, mock_build_graph, client):
        mock_workflow = MagicMock()
        mock_build_graph.return_value = mock_workflow
        mock_workflow.invoke.return_value = {"output": "Enhanced prompt"}

        request_data = {
            "prompt": "Original prompt",
            "context": "Some context",
            "report_style": "academic",
        }

        response = client.post("/api/prompt/enhance", json=request_data)

        assert response.status_code == 200
        assert response.json()["result"] == "Enhanced prompt"

    @patch("deerflowx.server.app.build_prompt_enhancer_graph")
    def test_enhance_prompt_with_different_styles(self, mock_build_graph, client):
        mock_workflow = MagicMock()
        mock_build_graph.return_value = mock_workflow
        mock_workflow.invoke.return_value = {"output": "Enhanced prompt"}

        styles = [
            "ACADEMIC",
            "popular_science",
            "NEWS",
            "social_media",
            "invalid_style",
        ]

        for style in styles:
            request_data = {"prompt": "Test prompt", "report_style": style}

            response = client.post("/api/prompt/enhance", json=request_data)
            assert response.status_code == 200

    @patch("deerflowx.server.app.build_prompt_enhancer_graph")
    def test_enhance_prompt_error(self, mock_build_graph, client):
        mock_build_graph.side_effect = Exception("Enhancement failed")

        request_data = {"prompt": "Test prompt"}

        response = client.post("/api/prompt/enhance", json=request_data)

        assert response.status_code == 500
        assert response.json()["detail"] == "Internal Server Error"


class TestMCPEndpoint:
    @patch("deerflowx.server.app.load_mcp_tools")
    def test_mcp_server_metadata_success(self, mock_load_tools, client):
        mock_load_tools.return_value = [{"name": "test_tool", "description": "Test tool"}]

        request_data = {
            "transport": "stdio",
            "command": "test_command",
            "args": ["arg1", "arg2"],
            "env": {"ENV_VAR": "value"},
        }

        response = client.post("/api/mcp/server/metadata", json=request_data)

        assert response.status_code == 200
        response_data = response.json()
        assert response_data["transport"] == "stdio"
        assert response_data["command"] == "test_command"
        assert len(response_data["tools"]) == 1

    @patch("deerflowx.server.app.load_mcp_tools")
    def test_mcp_server_metadata_with_custom_timeout(self, mock_load_tools, client):
        mock_load_tools.return_value = []

        request_data = {
            "transport": "stdio",
            "command": "test_command",
            "timeout_seconds": 600,
        }

        response = client.post("/api/mcp/server/metadata", json=request_data)

        assert response.status_code == 200
        mock_load_tools.assert_called_once()

    @patch("deerflowx.server.app.load_mcp_tools")
    def test_mcp_server_metadata_with_exception(self, mock_load_tools, client):
        mock_load_tools.side_effect = HTTPException(status_code=400, detail="MCP Server Error")

        request_data = {
            "transport": "stdio",
            "command": "test_command",
            "args": ["arg1", "arg2"],
            "env": {"ENV_VAR": "value"},
        }

        response = client.post("/api/mcp/server/metadata", json=request_data)

        assert response.status_code == 400
        assert response.json()["detail"] == "MCP Server Error"


class TestRAGEndpoints:
    @patch("deerflowx.server.app.SELECTED_RAG_PROVIDER", "test_provider")
    def test_rag_config(self, client):
        response = client.get("/api/rag/config")

        assert response.status_code == 200
        assert response.json()["provider"] == "test_provider"

    @patch("deerflowx.server.app.build_retriever")
    def test_rag_resources_with_retriever(self, mock_build_retriever, client):
        mock_retriever = MagicMock()
        mock_retriever.list_resources.return_value = [
            {
                "uri": "test_uri",
                "title": "Test Resource",
                "description": "Test Description",
            }
        ]
        mock_build_retriever.return_value = mock_retriever

        response = client.get("/api/rag/resources?query=test")

        assert response.status_code == 200
        assert len(response.json()["resources"]) == 1

    @patch("deerflowx.server.app.build_retriever")
    def test_rag_resources_without_retriever(self, mock_build_retriever, client):
        mock_build_retriever.return_value = None

        response = client.get("/api/rag/resources")

        assert response.status_code == 200
        assert response.json()["resources"] == []


class TestChatStreamEndpoint:
    @patch("deerflowx.server.app.workflow_executor")
    def test_chat_stream_with_default_thread_id(self, mock_executor, client):
        # Mock the async stream
        async def mock_execute_workflow(*args, **kwargs):
            yield {"type": "message_chunk", "data": {"content": "Hello", "agent": "test"}}

        mock_executor.execute_workflow = mock_execute_workflow

        request_data = {
            "thread_id": "__default__",
            "messages": [{"role": "user", "content": "Hello"}],
            "resources": [],
            "max_plan_iterations": 3,
            "max_step_num": 10,
            "max_search_results": 5,
            "auto_accepted_plan": True,
            "interrupt_feedback": "",
            "mcp_settings": {},
            "enable_background_investigation": False,
            "report_style": "academic",
        }

        response = client.post("/api/chat/stream", json=request_data)

        assert response.status_code == 200
        assert response.headers["content-type"] == "text/event-stream; charset=utf-8"


class TestGenerateProseEndpoint:
    @patch("deerflowx.server.app.build_prose_graph")
    def test_generate_prose_success(self, mock_build_graph, client):
        # Mock the workflow and its astream method
        mock_workflow = MagicMock()
        mock_build_graph.return_value = mock_workflow

        class MockEvent:
            def __init__(self, content):
                self.content = content

        async def mock_astream(*args, **kwargs):
            yield (None, [MockEvent("Generated prose 1")])
            yield (None, [MockEvent("Generated prose 2")])

        mock_workflow.astream.return_value = mock_astream()
        request_data = {
            "prompt": "Write a story.",
            "option": "default",
            "command": "generate",
        }

        response = client.post("/api/prose/generate", json=request_data)

        assert response.status_code == 200
        assert response.headers["content-type"].startswith("text/event-stream")

        # Read the streaming response content
        content = b"".join(response.iter_bytes())
        assert b"Generated prose 1" in content or b"Generated prose 2" in content

    @patch("deerflowx.server.app.build_prose_graph")
    def test_generate_prose_error(self, mock_build_graph, client):
        mock_build_graph.side_effect = Exception("Prose generation failed")
        request_data = {
            "prompt": "Write a story.",
            "option": "default",
            "command": "generate",
        }
        response = client.post("/api/prose/generate", json=request_data)
        assert response.status_code == 500
        assert response.json()["detail"] == "Internal Server Error"

# Copyright (c) 2025 Bytedance Ltd. and/or its affiliates
# SPDX-License-Identifier: MIT
"""Global pytest configuration and fixtures."""

import os
from unittest.mock import patch

import pytest


@pytest.fixture(autouse=True, scope="session")
def mock_environment_variables():
    """Auto-use session-scoped fixture to mock necessary environment variables for tests."""
    test_env_vars = {
        # Tavily API
        "TAVILY_API_KEY": "mock-tavily-key",
    }

    with patch.dict(os.environ, test_env_vars):
        yield

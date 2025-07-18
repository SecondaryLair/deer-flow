# Copyright (c) 2025 Bytedance Ltd. and/or its affiliates
# SPDX-License-Identifier: MIT

import sys
import types

from deerflowx.config.configuration import Configuration

# Patch sys.path so relative import works

# Patch Resource for import
mock_resource = type("Resource", (), {})

# Patch deerflowx.libs.rag.retriever.Resource for import

module_name = "deerflowx.libs.rag.retriever"
if module_name not in sys.modules:
    retriever_mod = types.ModuleType(module_name)
    retriever_mod.Resource = mock_resource
    sys.modules[module_name] = retriever_mod

# Relative import of Configuration


def test_default_configuration():
    config = Configuration()
    assert config.resources == []
    assert config.max_plan_iterations == 1
    assert config.max_step_num == 3
    assert config.max_search_results == 3
    assert config.mcp_settings is None
    assert config.max_observations_tokens == 45000
    assert config.compression_safety_margin == 0.8
    assert config.summarizer_chunk_size == 8000
    assert config.summarizer_chunk_overlap == 400
    assert config.summarizer_enable_second_pass is True


def test_from_runnable_config_with_config_dict():
    config_dict = {
        "configurable": {
            "max_plan_iterations": 5,
            "max_step_num": 7,
            "max_search_results": 10,
            "mcp_settings": {"foo": "bar"},
            "max_observations_tokens": 60000,
            "compression_safety_margin": 0.9,
        }
    }
    config = Configuration.from_runnable_config(config_dict)
    assert config.max_plan_iterations == 5
    assert config.max_step_num == 7
    assert config.max_search_results == 10
    assert config.mcp_settings == {"foo": "bar"}
    assert config.max_observations_tokens == 60000
    assert config.compression_safety_margin == 0.9


def test_from_runnable_config_with_none_and_falsy():
    config_dict = {
        "configurable": {
            "max_plan_iterations": None,
            "max_step_num": 0,
            "max_search_results": "",
        }
    }
    config = Configuration.from_runnable_config(config_dict)
    # None and falsy values should use defaults
    assert config.max_plan_iterations == 1
    assert config.max_step_num == 3
    assert config.max_search_results == 3


def test_from_runnable_config_with_no_config():
    config = Configuration.from_runnable_config()
    assert config.max_plan_iterations == 1
    assert config.max_step_num == 3
    assert config.max_search_results == 3
    assert config.resources == []
    assert config.mcp_settings is None

# Copyright (c) 2025 Bytedance Ltd. and/or its affiliates
# SPDX-License-Identifier: MIT

from abc import ABC, abstractmethod
from typing import Any


class NodeBase(ABC):
    """Base class for all LangGraph nodes."""

    @classmethod
    @abstractmethod
    def name(cls) -> str:
        """Return the name of the node."""
        ...

    @classmethod
    @abstractmethod
    async def action(cls, *args, **kwargs) -> Any:
        """Execute the node action asynchronously."""
        ...

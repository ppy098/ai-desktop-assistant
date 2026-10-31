"""工具层的公共基础类型，独立成模块以避免循环导入。"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class ToolResult:
    """所有工具统一的返回结构。"""

    success: bool
    message: str
    data: dict[str, Any] = field(default_factory=dict)

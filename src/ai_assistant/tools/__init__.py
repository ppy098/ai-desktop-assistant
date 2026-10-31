"""工具层：每个模块实现一个可被 AI 调用的能力，并统一通过 ToolResult 返回结果。

工具注册表（TOOL_SPECS）同时提供：
1. 给在线大模型使用的 function-calling JSON Schema；
2. 名称到本地执行函数的映射，供 agent.dispatch 调用。
"""

from __future__ import annotations

from typing import Any, Callable

from .base import ToolResult
from . import files, launcher, web


# 名称 -> 执行函数；每个函数接收关键字参数，返回 ToolResult
TOOL_HANDLERS: dict[str, Callable[..., ToolResult]] = {
    "open_app": launcher.open_app,
    "create_file": files.create_file,
    "web_search": web.search,
}


# 提供给大模型的函数描述（OpenAI 兼容 function-calling 格式）
TOOL_SPECS: list[dict[str, Any]] = [
    {
        "type": "function",
        "function": {
            "name": "open_app",
            "description": "在 Windows 上启动一个应用程序，例如记事本、计算器、浏览器等。",
            "parameters": {
                "type": "object",
                "properties": {
                    "app_name": {
                        "type": "string",
                        "description": "应用程序的中文或英文名称，例如：记事本、计算器、notepad、chrome",
                    }
                },
                "required": ["app_name"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "create_file",
            "description": "创建一个文本文件并写入内容。",
            "parameters": {
                "type": "object",
                "properties": {
                    "filename": {
                        "type": "string",
                        "description": "文件名，需要包含扩展名，例如 todo.txt",
                    },
                    "content": {
                        "type": "string",
                        "description": "要写入文件的文本内容",
                    },
                    "directory": {
                        "type": "string",
                        "description": "可选，保存目录。支持“桌面/文档/下载”，留空则保存到桌面。",
                    },
                },
                "required": ["filename", "content"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "web_search",
            "description": "用默认浏览器在搜索引擎中搜索关键词。",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {"type": "string", "description": "搜索关键词"},
                },
                "required": ["query"],
            },
        },
    },
]


def dispatch(tool_name: str, arguments: dict[str, Any] | None = None) -> ToolResult:
    """按名称执行工具，集中处理未知工具与参数异常。"""
    handler = TOOL_HANDLERS.get(tool_name)
    if handler is None:
        return ToolResult(success=False, message=f"未知工具：{tool_name}")
    try:
        return handler(**(arguments or {}))
    except TypeError as exc:
        return ToolResult(success=False, message=f"工具参数错误：{exc}")
    except Exception as exc:  # noqa: BLE001 - 边界层兜底，避免异常直接抛到界面
        return ToolResult(success=False, message=f"工具执行失败：{exc}")


__all__ = ["ToolResult", "TOOL_SPECS", "TOOL_HANDLERS", "dispatch"]

"""工具层：每个模块实现一个可被 AI 调用的能力，并统一通过 ToolResult 返回结果。

工具注册表（TOOL_SPECS）同时提供：
1. 给在线大模型使用的 function-calling JSON Schema；
2. 名称到本地执行函数的映射，供 agent.dispatch 调用。
"""

from __future__ import annotations

from typing import Any, Callable

from .base import ToolResult
from . import desktop, files, launcher, web


# 名称 -> 执行函数；每个函数接收关键字参数，返回 ToolResult
TOOL_HANDLERS: dict[str, Callable[..., ToolResult]] = {
    "open_app": launcher.open_app,
    "create_file": files.create_file,
    "web_search": web.search,
    "open_url": desktop.open_url,
    "get_time": desktop.get_time,
    "get_clipboard": desktop.get_clipboard,
    "set_clipboard": desktop.set_clipboard,
    "take_screenshot": desktop.take_screenshot,
    "system_status": desktop.system_status,
    "open_folder": desktop.open_folder,
    "optimize_memory": desktop.optimize_memory,
    "clean_disk": desktop.clean_disk,
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
    {
        "type": "function",
        "function": {
            "name": "open_url",
            "description": "用默认浏览器打开一个明确的网址（不是搜索）。",
            "parameters": {
                "type": "object",
                "properties": {
                    "url": {"type": "string", "description": "网址，例如 https://www.baidu.com"},
                },
                "required": ["url"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_time",
            "description": "回答当前日期、星期和时间。用户问“现在几点”“今天几号”“星期几”时使用。",
            "parameters": {"type": "object", "properties": {}},
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_clipboard",
            "description": "读取当前剪贴板里的文本内容。",
            "parameters": {"type": "object", "properties": {}},
        },
    },
    {
        "type": "function",
        "function": {
            "name": "set_clipboard",
            "description": "把一段文本复制到剪贴板，方便用户随后粘贴。",
            "parameters": {
                "type": "object",
                "properties": {
                    "text": {"type": "string", "description": "要复制的文本内容"},
                },
                "required": ["text"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "take_screenshot",
            "description": "全屏截图并保存到桌面，返回保存路径。",
            "parameters": {
                "type": "object",
                "properties": {
                    "filename": {
                        "type": "string",
                        "description": "可选，截图文件名（.png），留空自动按时间命名",
                    }
                },
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "system_status",
            "description": "查看电脑状态：内存占用、磁盘使用、处理器和电池信息。",
            "parameters": {"type": "object", "properties": {}},
        },
    },
    {
        "type": "function",
        "function": {
            "name": "open_folder",
            "description": "打开桌面、文档或下载文件夹。",
            "parameters": {
                "type": "object",
                "properties": {
                    "name": {
                        "type": "string",
                        "description": "要打开的文件夹：桌面 / 文档 / 下载",
                    }
                },
                "required": ["name"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "optimize_memory",
            "description": "一键内存优化：整理进程工作集、写出已修改页、清空待机内存列表与系统文件缓存。",
            "parameters": {"type": "object", "properties": {}},
        },
    },
    {
        "type": "function",
        "function": {
            "name": "clean_disk",
            "description": "一键清理磁盘垃圾：临时文件、Windows 更新缓存、回收站、缩略图缓存、错误报告。",
            "parameters": {"type": "object", "properties": {}},
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

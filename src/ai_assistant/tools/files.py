"""创建文件工具。

安全约束：只允许在当前用户目录（%USERPROFILE%）之下创建文件，
防止指令误写 C:\\Windows 等系统目录。
"""

from __future__ import annotations

import os
from pathlib import Path

from .base import ToolResult

# 中文目录名 -> 实际路径
_DIRECTORY_ALIASES: dict[str, Path] = {
    "桌面": Path.home() / "Desktop",
    "desktop": Path.home() / "Desktop",
    "文档": Path.home() / "Documents",
    "documents": Path.home() / "Documents",
    "下载": Path.home() / "Downloads",
    "downloads": Path.home() / "Downloads",
}


def _resolve_directory(directory: str | None) -> Path:
    """把目录参数解析为实际路径，未指定时默认桌面。"""
    if not directory:
        return Path.home() / "Desktop"
    key = directory.strip().lower()
    if key in _DIRECTORY_ALIASES:
        return _DIRECTORY_ALIASES[key]
    return Path(os.path.expandvars(os.path.expanduser(directory)))


def create_file(filename: str, content: str, directory: str | None = None) -> ToolResult:
    """在指定目录创建文本文件并写入内容（UTF-8 编码）。"""
    name = (filename or "").strip()
    if not name:
        return ToolResult(False, "文件名不能为空")
    # 不允许文件名里带路径分隔符，避免绕过目录约束
    if "/" in name or "\\" in name or name in (".", ".."):
        return ToolResult(False, "文件名不能包含路径分隔符，请通过 directory 参数指定目录")

    base_dir = _resolve_directory(directory)
    file_path = base_dir / name

    # 安全校验：最终路径必须位于用户主目录之下
    user_home = Path.home().resolve()
    try:
        resolved = file_path.resolve()
        resolved.relative_to(user_home)
    except (OSError, ValueError):
        return ToolResult(False, "出于安全考虑，只允许在用户主目录下创建文件")

    base_dir.mkdir(parents=True, exist_ok=True)
    resolved.write_text(content or "", encoding="utf-8")
    return ToolResult(
        success=True,
        message=f"已创建文件：{resolved}",
        data={"path": str(resolved), "bytes": len((content or "").encode("utf-8"))},
    )

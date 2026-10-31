"""打开应用程序工具。

解析顺序：
1. 内置别名（Windows 自带程序，直接按可执行文件名启动）；
2. 扫描“开始菜单”中的快捷方式（.lnk），按名称模糊匹配；
3. 都找不到则返回失败结果。
"""

from __future__ import annotations

import os
import subprocess
from pathlib import Path

from .base import ToolResult

# Windows 自带程序与常见说法的别名表
_BUILTIN_ALIASES: dict[str, str] = {
    "记事本": "notepad.exe",
    "notepad": "notepad.exe",
    "计算器": "calc.exe",
    "calc": "calc.exe",
    "画图": "mspaint.exe",
    "mspaint": "mspaint.exe",
    "命令提示符": "cmd.exe",
    "cmd": "cmd.exe",
    "powershell": "powershell.exe",
    "资源管理器": "explorer.exe",
    "explorer": "explorer.exe",
    "文件资源管理器": "explorer.exe",
    "控制面板": "control.exe",
    "control": "control.exe",
    "任务管理器": "taskmgr.exe",
    "taskmgr": "taskmgr.exe",
    "注册表编辑器": "regedit.exe",
    "regedit": "regedit.exe",
    "写字板": "write.exe",
    "write": "write.exe",
}


def _start_menu_dirs() -> list[Path]:
    """返回当前用户与所有用户的开始菜单“程序”目录。"""
    appdata = os.environ.get("APPDATA")
    programdata = os.environ.get("ProgramData")
    candidates = []
    if appdata:
        candidates.append(Path(appdata) / "Microsoft" / "Windows" / "Start Menu" / "Programs")
    if programdata:
        candidates.append(Path(programdata) / "Microsoft" / "Windows" / "Start Menu" / "Programs")
    return [p for p in candidates if p.is_dir()]


def _find_shortcut(app_name: str) -> Path | None:
    """在开始菜单中按名称查找快捷方式，优先精确匹配，其次包含匹配。"""
    target = app_name.strip().lower()
    partial: Path | None = None
    for menu_dir in _start_menu_dirs():
        for lnk in menu_dir.rglob("*.lnk"):
            stem = lnk.stem.lower()
            if stem == target:
                return lnk
            if partial is None and target in stem:
                partial = lnk
    return partial


def open_app(app_name: str) -> ToolResult:
    """启动指定的应用程序。"""
    name = (app_name or "").strip()
    if not name:
        return ToolResult(success=False, message="应用名称不能为空")

    key = name.lower()
    if key in _BUILTIN_ALIASES:
        exe = _BUILTIN_ALIASES[key]
        try:
            subprocess.Popen(["cmd", "/c", "start", "", exe], shell=False)
            return ToolResult(True, f"已打开 {name}", {"executable": exe})
        except OSError as exc:
            return ToolResult(False, f"启动 {name} 失败：{exc}")

    shortcut = _find_shortcut(name)
    if shortcut is not None:
        try:
            os.startfile(str(shortcut))  # type: ignore[attr-defined]
            return ToolResult(True, f"已打开 {shortcut.stem}", {"shortcut": str(shortcut)})
        except OSError as exc:
            return ToolResult(False, f"启动 {name} 失败：{exc}")

    return ToolResult(False, f"没有找到名为“{name}”的程序")

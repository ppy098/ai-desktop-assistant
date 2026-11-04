"""桌面能力工具：时间、网址、剪贴板、截屏、系统状态、常用文件夹。

全部使用 Windows 原生能力（ctypes / PowerShell），不引入额外依赖，
打包后体积不增加。
"""

from __future__ import annotations

import base64
import ctypes
import datetime as _dt
import os
import platform
import shutil
import subprocess
import webbrowser
from pathlib import Path

from .base import ToolResult

# PowerShell 子进程不弹黑框
_CREATE_NO_WINDOW = 0x08000000 if os.name == "nt" else 0

_WEEKDAYS = "一二三四五六日"

_FOLDER_ALIASES: dict[str, str] = {
    "桌面": "Desktop",
    "desktop": "Desktop",
    "文档": "Documents",
    "documents": "Documents",
    "下载": "Downloads",
    "downloads": "Downloads",
}


def _run_ps(script: str, timeout: int = 25) -> tuple[bool, str]:
    """执行 PowerShell（无窗口），返回 (是否成功, 输出文本)。"""
    cmd = [
        "powershell.exe",
        "-NoProfile",
        "-NonInteractive",
        "-ExecutionPolicy",
        "Bypass",
        "-Command",
        "[Console]::OutputEncoding=[Text.Encoding]::UTF8;" + script,
    ]
    try:
        proc = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=timeout,
            creationflags=_CREATE_NO_WINDOW,
        )
    except (OSError, subprocess.TimeoutExpired) as exc:
        return False, f"PowerShell 调用失败：{exc}"
    out = (proc.stdout or "").strip()
    if proc.returncode != 0:
        return False, (proc.stderr or out or "PowerShell 执行失败").strip()
    return True, out


# ----------------------------------------------------------------------
# 时间
# ----------------------------------------------------------------------


def get_time() -> ToolResult:
    """回答当前日期、星期与时间。"""
    now = _dt.datetime.now()
    text = (
        f"现在是 {now.year}年{now.month}月{now.day}日 "
        f"星期{_WEEKDAYS[now.weekday()]} {now.hour:02d}:{now.minute:02d}"
    )
    return ToolResult(True, text, {"iso": now.isoformat(timespec="seconds")})


# ----------------------------------------------------------------------
# 网址
# ----------------------------------------------------------------------


def open_url(url: str) -> ToolResult:
    """用系统默认浏览器打开指定网址。"""
    target = (url or "").strip().strip('"“”')
    if not target:
        return ToolResult(False, "网址不能为空")
    if not target.lower().startswith(("http://", "https://")):
        target = "https://" + target
    if not webbrowser.open(target):
        return ToolResult(False, "无法调用系统浏览器")
    return ToolResult(True, f"已在浏览器打开：{target}", {"url": target})


# ----------------------------------------------------------------------
# 剪贴板
# ----------------------------------------------------------------------


def get_clipboard() -> ToolResult:
    """读取当前剪贴板文本。"""
    ok, out = _run_ps("Get-Clipboard -Raw", timeout=15)
    if not ok:
        return ToolResult(False, f"读取剪贴板失败：{out}")
    if not out:
        return ToolResult(True, "剪贴板里没有文本", {"text": ""})
    preview = out if len(out) <= 500 else out[:500] + "……"
    return ToolResult(True, f"剪贴板内容：{preview}", {"text": preview})


def set_clipboard(text: str) -> ToolResult:
    """把文本写入剪贴板。"""
    content = text or ""
    if not content.strip():
        return ToolResult(False, "要复制的内容不能为空")
    b64 = base64.b64encode(content.encode("utf-8")).decode("ascii")
    script = (
        "Set-Clipboard -Value ([Text.Encoding]::UTF8.GetString("
        f"[Convert]::FromBase64String('{b64}')))"
    )
    ok, out = _run_ps(script, timeout=15)
    if not ok:
        return ToolResult(False, f"写入剪贴板失败：{out}")
    return ToolResult(True, "已复制到剪贴板", {"chars": len(content)})


# ----------------------------------------------------------------------
# 截屏
# ----------------------------------------------------------------------


def take_screenshot(filename: str | None = None) -> ToolResult:
    """全屏截图并保存到桌面，返回文件路径。"""
    name = (filename or "").strip()
    if not name:
        name = _dt.datetime.now().strftime("截图_%Y%m%d_%H%M%S.png")
    if not name.lower().endswith(".png"):
        name += ".png"
    if "/" in name or "\\" in name or name in (".", ".."):
        return ToolResult(False, "文件名不能包含路径分隔符")

    target = Path.home() / "Desktop" / name
    script = (
        "Add-Type -AssemblyName System.Windows.Forms;"
        "Add-Type -AssemblyName System.Drawing;"
        "$b=[System.Windows.Forms.Screen]::PrimaryScreen.Bounds;"
        "$bmp=New-Object System.Drawing.Bitmap $b.Width,$b.Height;"
        "$g=[System.Drawing.Graphics]::FromImage($bmp);"
        "$g.CopyFromScreen($b.Location,[System.Drawing.Point]::Empty,$b.Size);"
        f"$bmp.Save('{target}',[System.Drawing.Imaging.ImageFormat]::Png);"
        "$g.Dispose();$bmp.Dispose()"
    )
    ok, out = _run_ps(script, timeout=25)
    if not ok:
        return ToolResult(False, f"截屏失败：{out}")
    if not target.exists():
        return ToolResult(False, "截屏失败：文件没有生成")
    return ToolResult(
        True,
        f"已截屏并保存到桌面：{name}",
        {"path": str(target), "bytes": target.stat().st_size},
    )


# ----------------------------------------------------------------------
# 系统状态
# ----------------------------------------------------------------------


class _MEMORYSTATUSEX(ctypes.Structure):
    _fields_ = [
        ("dwLength", ctypes.c_ulong),
        ("dwMemoryLoad", ctypes.c_ulong),
        ("ullTotalPhys", ctypes.c_ulonglong),
        ("ullAvailPhys", ctypes.c_ulonglong),
        ("ullTotalPageFile", ctypes.c_ulonglong),
        ("ullAvailPageFile", ctypes.c_ulonglong),
        ("ullTotalVirtual", ctypes.c_ulonglong),
        ("ullAvailVirtual", ctypes.c_ulonglong),
        ("ullAvailExtendedVirtual", ctypes.c_ulonglong),
    ]


class _SYSTEM_POWER_STATUS(ctypes.Structure):
    _fields_ = [
        ("ACLineStatus", ctypes.c_ubyte),
        ("BatteryFlag", ctypes.c_ubyte),
        ("BatteryLifePercent", ctypes.c_ubyte),
        ("SystemStatusFlag", ctypes.c_ubyte),
        ("BatteryLifeTime", ctypes.c_ulong),
        ("BatteryFullLifeTime", ctypes.c_ulong),
    ]


def _memory_status() -> tuple[float, float, int] | None:
    """返回 (总内存GB, 可用GB, 使用百分比)。"""
    try:
        stat = _MEMORYSTATUSEX()
        stat.dwLength = ctypes.sizeof(_MEMORYSTATUSEX)
        ctypes.windll.kernel32.GlobalMemoryStatusEx(ctypes.byref(stat))
    except (AttributeError, OSError):
        return None
    total = stat.ullTotalPhys / 1024 ** 3
    avail = stat.ullAvailPhys / 1024 ** 3
    return total, avail, int(stat.dwMemoryLoad)


def _battery_status() -> str | None:
    """返回电池状态描述，台式机或读取失败时返回 None。"""
    try:
        power = _SYSTEM_POWER_STATUS()
        if not ctypes.windll.kernel32.GetSystemPowerStatus(ctypes.byref(power)):
            return None
    except (AttributeError, OSError):
        return None
    if power.BatteryLifePercent == 255:
        return None  # 没有电池
    percent = int(power.BatteryLifePercent)
    if power.ACLineStatus == 1:
        return f"电池 {percent}%，已接电源"
    return f"电池 {percent}%，未接电源"


def system_status() -> ToolResult:
    """汇总内存、磁盘、处理器与电池信息。"""
    parts: list[str] = []

    memory = _memory_status()
    if memory is not None:
        total, avail, load = memory
        parts.append(f"内存 {load}%（可用 {avail:.1f}GB / 共 {total:.1f}GB）")

    try:
        disk = shutil.disk_usage(Path.home().anchor)
        parts.append(
            f"磁盘 {disk.used / 1024 ** 3:.1f}GB / {disk.total / 1024 ** 3:.1f}GB 已用"
        )
    except OSError:
        pass

    cpu = platform.processor() or "未知"
    parts.append(f"处理器 {cpu}")

    battery = _battery_status()
    if battery:
        parts.append(battery)

    if not parts:
        return ToolResult(False, "没有读取到系统信息")
    return ToolResult(True, "；".join(parts), {"parts": parts})


# ----------------------------------------------------------------------
# 常用文件夹
# ----------------------------------------------------------------------


def open_folder(name: str) -> ToolResult:
    """打开桌面 / 文档 / 下载文件夹。"""
    key = (name or "").strip().lower()
    folder = _FOLDER_ALIASES.get(key)
    if folder is None:
        return ToolResult(False, "只支持打开：桌面 / 文档 / 下载")
    path = Path.home() / folder
    if not path.is_dir():
        return ToolResult(False, f"文件夹不存在：{path}")
    try:
        os.startfile(str(path))  # type: ignore[attr-defined]
    except OSError as exc:
        return ToolResult(False, f"打开文件夹失败：{exc}")
    return ToolResult(True, f"已打开{folder}文件夹", {"path": str(path)})

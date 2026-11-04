"""桌面能力工具：时间、网址、剪贴板、截屏、系统状态、常用文件夹。

全部使用 Windows 原生能力（ctypes / PowerShell），不引入额外依赖，
打包后体积不增加。
"""

from __future__ import annotations

import base64
import ctypes
import datetime as _dt
import json
import os
import platform
import shutil
import subprocess
import sys
import time
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
            stdin=subprocess.DEVNULL,
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


# ----------------------------------------------------------------------
# 一键内存优化
# ----------------------------------------------------------------------

# 这些进程不整理工作集：系统关键进程或受保护进程
_SKIP_PROCESS_NAMES = {
    "system",
    "system idle process",
    "registry",
    "memory compression",
    "memcompression",
    "secure system",
    "csrss.exe",
    "wininit.exe",
    "winlogon.exe",
    "services.exe",
    "lsass.exe",
    "smss.exe",
    "msmpeng.exe",
    "dwm.exe",
    "audiodg.exe",
    "winlogon.exe",
}

_TH32CS_SNAPPROCESS = 0x00000002
_PROCESS_QUERY_INFORMATION = 0x0400
_PROCESS_SET_QUOTA = 0x0100


class _PROCESSENTRY32W(ctypes.Structure):
    _fields_ = [
        ("dwSize", ctypes.c_ulong),
        ("cntUsage", ctypes.c_ulong),
        ("th32ProcessID", ctypes.c_ulong),
        ("th32DefaultHeapID", ctypes.c_size_t),
        ("th32ModuleID", ctypes.c_ulong),
        ("cntThreads", ctypes.c_ulong),
        ("th32ParentProcessID", ctypes.c_ulong),
        ("pcPriClassBase", ctypes.c_long),
        ("dwFlags", ctypes.c_ulong),
        ("szExeFile", ctypes.c_wchar * 260),
    ]


class _PROCESS_MEMORY_COUNTERS(ctypes.Structure):
    _fields_ = [
        ("cb", ctypes.c_ulong),
        ("PageFaultCount", ctypes.c_ulong),
        ("PeakWorkingSetSize", ctypes.c_size_t),
        ("WorkingSetSize", ctypes.c_size_t),
        ("QuotaPeakPagedPoolUsage", ctypes.c_size_t),
        ("QuotaPagedPoolUsage", ctypes.c_size_t),
        ("QuotaPeakNonPagedPoolUsage", ctypes.c_size_t),
        ("QuotaNonPagedPoolUsage", ctypes.c_size_t),
        ("PagefileUsage", ctypes.c_size_t),
        ("PeakPagefileUsage", ctypes.c_size_t),
    ]


def _iter_processes() -> list[tuple[int, str]]:
    """枚举当前系统进程，返回 (pid, 进程名小写) 列表。"""
    kernel32 = ctypes.windll.kernel32
    snapshot = kernel32.CreateToolhelp32Snapshot(_TH32CS_SNAPPROCESS, 0)
    if not snapshot or snapshot == -1:  # 无效句柄
        return []

    entry = _PROCESSENTRY32W()
    entry.dwSize = ctypes.sizeof(_PROCESSENTRY32W)
    result: list[tuple[int, str]] = []
    try:
        ok = kernel32.Process32FirstW(snapshot, ctypes.byref(entry))
        while ok:
            result.append((int(entry.th32ProcessID), (entry.szExeFile or "").lower()))
            ok = kernel32.Process32NextW(snapshot, ctypes.byref(entry))
    finally:
        kernel32.CloseHandle(snapshot)
    return result


# ---- 权限提升所需结构（清理待机列表 / 文件缓存都需要特权） ----
_TOKEN_ADJUST_PRIVILEGES = 0x0020
_TOKEN_QUERY = 0x0008
_SE_PRIVILEGE_ENABLED = 0x0002
_ERROR_NOT_ALL_ASSIGNED = 1300

_SYSTEM_MEMORY_LIST_INFORMATION = 80
_MEMORY_EMPTY_WORKING_SETS = 2
_MEMORY_FLUSH_MODIFIED_LIST = 3
_MEMORY_PURGE_STANDBY_LIST = 4
_MEMORY_PURGE_LOW_PRIORITY_STANDBY = 5
_MEMORY_PURGE_STANDBY_LIST = 4


class _LUID(ctypes.Structure):
    _fields_ = [("LowPart", ctypes.c_ulong), ("HighPart", ctypes.c_long)]


class _LUID_AND_ATTRIBUTES(ctypes.Structure):
    _fields_ = [("Luid", _LUID), ("Attributes", ctypes.c_ulong)]


class _TOKEN_PRIVILEGES(ctypes.Structure):
    _fields_ = [
        ("PrivilegeCount", ctypes.c_ulong),
        ("Privileges", _LUID_AND_ATTRIBUTES * 1),
    ]


def _enable_privilege(name: str) -> bool:
    """在当前进程令牌里启用一个特权（如 SeProfileSingleProcessPrivilege）。"""
    try:
        kernel32 = ctypes.windll.kernel32
        advapi32 = ctypes.windll.advapi32
        kernel32.GetCurrentProcess.restype = ctypes.c_void_p
        advapi32.OpenProcessToken.argtypes = [
            ctypes.c_void_p,
            ctypes.c_ulong,
            ctypes.POINTER(ctypes.c_void_p),
        ]
        advapi32.OpenProcessToken.restype = ctypes.c_int

        token = ctypes.c_void_p()
        if not advapi32.OpenProcessToken(
            kernel32.GetCurrentProcess(),
            _TOKEN_ADJUST_PRIVILEGES | _TOKEN_QUERY,
            ctypes.byref(token),
        ):
            return False
    except (AttributeError, OSError):
        return False

    try:
        luid = _LUID()
        if not advapi32.LookupPrivilegeValueW(None, name, ctypes.byref(luid)):
            return False
        state = _TOKEN_PRIVILEGES()
        state.PrivilegeCount = 1
        state.Privileges[0].Luid = luid
        state.Privileges[0].Attributes = _SE_PRIVILEGE_ENABLED
        advapi32.AdjustTokenPrivileges(token, False, ctypes.byref(state), 0, None, None)
        # 令牌里没有该特权时 GetLastError 为 ERROR_NOT_ALL_ASSIGNED
        return kernel32.GetLastError() != _ERROR_NOT_ALL_ASSIGNED
    except (AttributeError, OSError):
        return False
    finally:
        try:
            ctypes.windll.kernel32.CloseHandle(ctypes.c_void_p(token.value))
        except (AttributeError, OSError):
            pass


def _memory_list_command(command: int) -> bool:
    """执行一个 SYSTEM_MEMORY_LIST_COMMAND（3=刷已修改页 4=清空待机 5=清低优先级待机）。

    需要 SeProfileSingleProcessPrivilege；拿不到时 NtSetSystemInformation 会返回错误码。
    """
    try:
        ntdll = ctypes.windll.ntdll
        ntdll.NtSetSystemInformation.argtypes = [ctypes.c_int, ctypes.c_void_p, ctypes.c_ulong]
        ntdll.NtSetSystemInformation.restype = ctypes.c_long
        value = ctypes.c_ulong(command)
        status = ntdll.NtSetSystemInformation(
            _SYSTEM_MEMORY_LIST_INFORMATION, ctypes.byref(value), ctypes.sizeof(value)
        )
        return status == 0
    except (AttributeError, OSError):
        return False


def _purge_standby_list() -> bool:
    """清空系统待机内存列表（RAMMap 的 Empty Standby List，PCL2 同款做法）。"""
    try:
        ntdll = ctypes.windll.ntdll
        ntdll.NtSetSystemInformation.restype = ctypes.c_long
        info = ctypes.c_ulong(_MEMORY_PURGE_STANDBY_LIST)
        status = ntdll.NtSetSystemInformation(
            _SYSTEM_MEMORY_LIST_INFORMATION, ctypes.byref(info), ctypes.sizeof(info)
        )
        return status == 0
    except (AttributeError, OSError):
        return False


def _flush_system_file_cache() -> bool:
    """清理系统文件缓存（等价 RAMMap 的 Empty System Working Set）。"""
    try:
        kernel32 = ctypes.windll.kernel32
        kernel32.SetSystemFileCacheSize.argtypes = [
            ctypes.c_size_t,
            ctypes.c_size_t,
            ctypes.c_ulong,
        ]
        kernel32.SetSystemFileCacheSize.restype = ctypes.c_int
        return bool(
            kernel32.SetSystemFileCacheSize(ctypes.c_size_t(-1), ctypes.c_size_t(-1), 0)
        )
    except (AttributeError, OSError):
        return False


def _empty_working_sets(min_mb: int) -> tuple[int, int, float]:
    """整理各进程工作集，返回 (整理数, 跳过数, 涉及工作集 MB)。"""
    kernel32 = ctypes.windll.kernel32
    psapi = ctypes.windll.psapi
    trimmed = 0
    skipped = 0
    touched_mb = 0.0

    for pid, name in _iter_processes():
        if pid == 0 or name in _SKIP_PROCESS_NAMES:
            continue
        handle = kernel32.OpenProcess(
            _PROCESS_QUERY_INFORMATION | _PROCESS_SET_QUOTA, False, pid
        )
        if not handle:
            skipped += 1  # 系统进程或无权限，跳过
            continue
        try:
            counters = _PROCESS_MEMORY_COUNTERS()
            counters.cb = ctypes.sizeof(_PROCESS_MEMORY_COUNTERS)
            if not psapi.GetProcessMemoryInfo(handle, ctypes.byref(counters), counters.cb):
                skipped += 1
                continue
            working_set_mb = counters.WorkingSetSize / 1024 ** 2
            if working_set_mb < min_mb:
                skipped += 1
                continue
            if psapi.EmptyWorkingSet(handle):
                trimmed += 1
                touched_mb += working_set_mb
            else:
                skipped += 1
        finally:
            kernel32.CloseHandle(handle)

    return trimmed, skipped, touched_mb



_ELEVATED_DIR = Path.home() / ".ai_desktop_assistant"
_ELEVATED_FILES = {
    "memory": _ELEVATED_DIR / "elevated_optimize.json",
    "disk": _ELEVATED_DIR / "elevated_clean_disk.json",
}


def _is_admin() -> bool:
    """当前进程是否拥有管理员令牌。"""
    try:
        return bool(ctypes.windll.shell32.IsUserAnAdmin())
    except (AttributeError, OSError):
        return False


def _run_elevated(mode: str = "memory", timeout: float = 60.0) -> ToolResult | None:
    """以管理员身份启动自身执行一次动作，读取它写回的结果。

    mode 为 "memory"（--optimize-memory）或 "disk"（--clean-disk）。
    用户在 UAC 里点“是”才会执行；点“否”（ShellExecute 返回 1223）时返回 None，调用方降级。
    """
    flag = {"memory": "--optimize-memory", "disk": "--clean-disk"}.get(mode)
    if flag is None:
        return None
    exe = sys.executable
    params = flag if getattr(sys, "frozen", False) else f"-m ai_assistant {flag}"

    result_file = _ELEVATED_FILES[mode]
    try:
        result_file.unlink()
    except OSError:
        pass

    try:
        ret = ctypes.windll.shell32.ShellExecuteW(None, "runas", exe, params, None, 0)
    except (AttributeError, OSError):
        return None
    if ret <= 32:  # 32 及以下都是失败
        return None

    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        if result_file.exists():
            try:
                payload = json.loads(result_file.read_text(encoding="utf-8"))
            except (OSError, ValueError):
                time.sleep(0.2)
                continue
            try:
                result_file.unlink()
            except OSError:
                pass
            return ToolResult(
                bool(payload.get("success")),
                str(payload.get("message", "")),
                dict(payload.get("data", {})),
            )
        time.sleep(0.2)
    return None


def _write_elevated_result(result: ToolResult, mode: str = "memory") -> None:
    """提权子进程把结果写回文件，供父进程读取。"""
    result_file = _ELEVATED_FILES.get(mode)
    if result_file is None:
        return
    try:
        result_file.parent.mkdir(parents=True, exist_ok=True)
        result_file.write_text(
            json.dumps(
                {
                    "success": result.success,
                    "message": result.message,
                    "data": result.data,
                },
                ensure_ascii=False,
            ),
            encoding="utf-8",
        )
    except OSError:
        pass


def optimize_memory(min_mb: int = 8, elevate: bool = True) -> ToolResult:
    """一键内存优化（PCL2 同款五步）：

    整理进程工作集 → 刷已修改页 → 清低优先级待机 → 清空待机列表 → 清系统文件缓存。
    后四项需要管理员令牌里的特权，普通权限下会自动跳过并如实说明。
    """
    if os.name != "nt":
        return ToolResult(False, "内存优化目前只支持 Windows 系统")

    if elevate and not _is_admin():
        elevated = _run_elevated("memory")
        if elevated is not None:
            return elevated

    before = _memory_status()
    steps: list[str] = []
    limited = False

    # 先整理工作集：页会转入待机/已修改列表，再由后面的步骤统一回收
    trimmed, _skipped, touched_mb = _empty_working_sets(min_mb)
    if trimmed:
        steps.append(f"整理 {trimmed} 个进程工作集")

    if _enable_privilege("SeProfileSingleProcessPrivilege"):
        if _memory_list_command(_MEMORY_FLUSH_MODIFIED_LIST):
            steps.append("写出已修改页")
        else:
            limited = True
        if _memory_list_command(_MEMORY_PURGE_LOW_PRIORITY_STANDBY):
            steps.append("清低优先级待机内存")
        if _memory_list_command(_MEMORY_PURGE_STANDBY_LIST):
            steps.append("清空待机内存列表")
        else:
            limited = True
    else:
        limited = True

    if _enable_privilege("SeIncreaseQuotaPrivilege") and _flush_system_file_cache():
        steps.append("清理系统文件缓存")
    else:
        limited = True

    time.sleep(0.8)  # 清空待机列表后系统需要一点时间把页转为空闲，等一下再统计更准
    after = _memory_status()

    if not steps:
        return ToolResult(False, "没有可整理的内存，可能需要以管理员身份运行")

    if before and after:
        gain_mb = (after[1] - before[1]) * 1024
        text = (
            f"内存优化完成（{'、'.join(steps)}）："
            f"可用内存 {before[1]:.1f}GB → {after[1]:.1f}GB"
            f"（释放约 {max(gain_mb, 0):.0f}MB，占用 {before[2]}% → {after[2]}%）"
        )
        if gain_mb < 50:
            text += "；系统内存本来就比较空闲，变化不大"
    else:
        text = f"内存优化完成（{'、'.join(steps)}）"

    if limited:
        text += "。清待机列表/系统缓存需要管理员权限，请在 UAC 弹窗里点“是”"

    return ToolResult(
        True,
        text,
        {
            "steps": steps,
            "trimmed": trimmed,
            "touched_mb": round(touched_mb),
            "gain_mb": round(max((after[1] - before[1]) * 1024, 0)) if before and after else None,
            "privileged": not limited,
        },
    )


# ----------------------------------------------------------------------
# 磁盘清理（临时文件 / 更新缓存 / 回收站 / 缩略图 / 错误报告）
# ----------------------------------------------------------------------

_DISK_TARGETS: tuple[tuple[str, str], ...] = (
    ("用户临时文件", os.environ.get("TEMP") or str(Path.home() / "AppData" / "Local" / "Temp")),
    ("系统临时文件", r"C:\Windows\Temp"),
    ("Windows 更新缓存", r"C:\Windows\SoftwareDistribution\Download"),
    ("错误报告缓存", r"C:\ProgramData\Microsoft\Windows\WER\ReportArchive"),
    ("错误报告缓存", r"C:\ProgramData\Microsoft\Windows\WER\ReportQueue"),
    ("传递优化缓存", r"C:\ProgramData\Microsoft\Windows\DeliveryOptimization\Cache"),
)

_DISK_KEEP_FILES = {"desktop.ini", "thumbs.db"}


def _folder_bytes(path: Path) -> int:
    """统计目录总字节数（不跟随符号链接，读不到的跳过）。"""
    total = 0
    if not path.is_dir():
        return total
    for root, _dirs, files in os.walk(path, followlinks=False, onerror=lambda exc: None):
        for name in files:
            try:
                total += os.path.getsize(os.path.join(root, name))
            except OSError:
                continue
    return total


def _clear_folder(path: Path) -> None:
    """清空目录内的文件（保留目录本身与正在占用/无权限删除的文件）。"""
    if not path.is_dir():
        return
    for root, _dirs, files in os.walk(path, followlinks=False, onerror=lambda exc: None):
        for name in files:
            if name.lower() in _DISK_KEEP_FILES:
                continue
            try:
                os.remove(os.path.join(root, name))
            except OSError:
                continue


def _clear_thumbnails() -> int:
    """删除资源管理器缩略图缓存（系统会自动重建）。"""
    folder = Path(os.environ.get("LOCALAPPDATA", "")) / "Microsoft" / "Windows" / "Explorer"
    if not folder.is_dir():
        return 0
    freed = 0
    try:
        for item in folder.glob("thumbcache_*.db"):
            try:
                size = item.stat().st_size
                item.unlink()
                freed += size
            except OSError:
                continue
    except OSError:
        pass
    return freed


def _empty_recycle_bin() -> bool:
    """清空回收站（不弹确认框、不显示进度、不出声）。"""
    try:
        flags = 0x1 | 0x2 | 0x4  # NOCONFIRMATION | NOPROGRESSUI | NOSOUND
        ctypes.windll.shell32.SHEmptyRecycleBinW(None, None, flags)
        return True
    except (AttributeError, OSError):
        return False


def _disk_free_gb(path: str = "C:\\") -> float:
    try:
        usage = shutil.disk_usage(path)
    except OSError:
        return 0.0
    return usage.free / 1024 ** 3


def clean_disk(elevate: bool = True) -> ToolResult:
    """一键清理磁盘垃圾：临时文件、Windows 更新缓存、回收站、缩略图、错误报告。"""
    if os.name != "nt":
        return ToolResult(False, "磁盘清理目前只支持 Windows 系统")

    if elevate and not _is_admin():
        elevated = _run_elevated("disk")
        if elevated is not None:
            return elevated

    before_free = _disk_free_gb()
    per_item: dict[str, int] = {}
    limited = False

    for label, raw in _DISK_TARGETS:
        folder = Path(raw)
        if not folder.is_dir():
            continue
        size_before = _folder_bytes(folder)
        _clear_folder(folder)
        got = max(size_before - _folder_bytes(folder), 0)
        if size_before and got < size_before * 0.5 and not _is_admin():
            limited = True  # 部分文件被系统占用/无权限
        per_item[label] = per_item.get(label, 0) + got

    thumb = _clear_thumbnails()
    if thumb:
        per_item["缩略图缓存"] = thumb

    steps = [
        f"{label} {size / 1024 ** 2:.0f}MB"
        for label, size in per_item.items()
        if size >= 1024 * 1024
    ]
    if _empty_recycle_bin():
        steps.append("清空回收站")

    time.sleep(0.3)
    after_free = _disk_free_gb()
    gained_gb = max(after_free - before_free, 0.0)

    text = (
        f"磁盘清理完成（{'、'.join(steps)}）："
        f"C 盘可用 {before_free:.1f}GB → {after_free:.1f}GB（释放约 {gained_gb * 1024:.0f}MB）"
    )
    if gained_gb < 0.05:
        text += "；垃圾本来就清得比较干净，变化不大"
    if limited:
        text += "。系统临时目录/更新缓存里的部分文件需要管理员权限，点按钮时在 UAC 弹窗里点“是”会更彻底"

    return ToolResult(
        True,
        text,
        {
            "steps": steps,
            "gained_mb": round(gained_gb * 1024),
            "free_before_gb": round(before_free, 2),
            "free_after_gb": round(after_free, 2),
            "privileged": _is_admin(),
        },
    )

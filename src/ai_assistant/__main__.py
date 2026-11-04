"""程序入口，支持三种启动方式：

1. 模块方式：python -m ai_assistant
2. 直接运行本文件：python src/ai_assistant/__main__.py
3. 提权子进程：AIDesktopAssistant.exe --optimize-memory / --clean-disk
   （由主程序用 UAC 拉起，执行一次动作后写回结果并退出，不启动界面）
"""

import sys
from pathlib import Path

if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
    from ai_assistant.main import main
    from ai_assistant.tools.desktop import (
        _write_elevated_result,
        clean_disk,
        optimize_memory,
    )
else:
    from .main import main
    from .tools.desktop import _write_elevated_result, clean_disk, optimize_memory


def _run_action() -> int:
    """提权模式：只做一次动作，把结果写回文件后退出（不启动界面）。"""
    if "--clean-disk" in sys.argv:
        _write_elevated_result(clean_disk(elevate=False), "disk")
    else:
        _write_elevated_result(optimize_memory(elevate=False), "memory")
    return 0


if __name__ == "__main__":
    if "--optimize-memory" in sys.argv or "--clean-disk" in sys.argv:
        sys.exit(_run_action())
    sys.exit(main())

"""程序入口，同时支持三种启动方式：

1. 模块方式：python -m ai_assistant
2. 直接运行本文件：python src/ai_assistant/__main__.py
3. 提权子进程：AIDesktopAssistant.exe --optimize-memory（由主程序用 UAC 拉起，执行一次内存优化后退出）
"""

import sys
from pathlib import Path

if __package__ in (None, ""):
    # 直接运行时没有包上下文，先把 src 目录加入搜索路径，再用绝对路径导入
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
    from ai_assistant.main import main
    from ai_assistant.tools.desktop import _write_elevated_result, optimize_memory
else:
    from .main import main
    from .tools.desktop import _write_elevated_result, optimize_memory


def _optimize_once() -> int:
    """提权模式：只做一次内存优化，把结果写回文件后退出（不启动界面）。"""
    _write_elevated_result(optimize_memory(elevate=False))
    return 0


if __name__ == "__main__":
    if "--optimize-memory" in sys.argv:
        sys.exit(_optimize_once())
    sys.exit(main())

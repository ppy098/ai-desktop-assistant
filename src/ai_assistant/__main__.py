"""程序入口，同时支持两种启动方式：

1. 模块方式：python -m ai_assistant
2. 直接运行本文件：python src/ai_assistant/__main__.py（或在资源管理器中双击）
"""

import sys
from pathlib import Path

if __package__ in (None, ""):
    # 直接运行时没有包上下文，先把 src 目录加入搜索路径，再用绝对路径导入
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
    from ai_assistant.main import main
else:
    from .main import main

if __name__ == "__main__":
    sys.exit(main())

"""支持 python -m ai_assistant 启动。"""

import sys

from .main import main

if __name__ == "__main__":
    sys.exit(main())

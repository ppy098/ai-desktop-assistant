"""程序启动入口。"""

from __future__ import annotations

import sys

from PySide6.QtWidgets import QApplication

from .core.config import load_settings
from .ui.main_window import MainWindow


def main() -> int:
    app = QApplication(sys.argv)
    app.setApplicationName("AI 桌面助手")
    window = MainWindow(load_settings())
    window.show()
    return app.exec()


if __name__ == "__main__":
    sys.exit(main())

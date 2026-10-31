"""程序启动入口：悬浮球 + 系统托盘常驻，主窗口按需唤起。"""

from __future__ import annotations

import sys

from PySide6.QtWidgets import QApplication

from .core.config import load_settings
from .ui.floating_ball import FloatingBall
from .ui.main_window import MainWindow
from .ui.tray import TrayIcon


class ApplicationController:
    """协调悬浮球、托盘与主窗口的显示和退出。"""

    def __init__(self) -> None:
        self._main_window = MainWindow(load_settings())

        self._ball = FloatingBall()
        self._ball.request_show_main.connect(self.toggle_main_window)
        self._ball.request_quit.connect(self.quit)
        self._ball.show()

        self._tray = TrayIcon(self.show_main_window, self.quit)
        self._tray.show()

    def show_main_window(self) -> None:
        self._main_window.show()
        self._main_window.raise_()
        self._main_window.activateWindow()

    def toggle_main_window(self) -> None:
        if self._main_window.isVisible():
            self._main_window.hide()
        else:
            self.show_main_window()

    def quit(self) -> None:
        self._tray.hide()
        self._ball.hide()
        QApplication.quit()


def main() -> int:
    app = QApplication(sys.argv)
    app.setApplicationName("AI 桌面助手")
    # 关闭最后一个窗口时不自动退出，保持常驻
    app.setQuitOnLastWindowClosed(False)
    ApplicationController()
    return app.exec()


if __name__ == "__main__":
    sys.exit(main())

"""系统托盘图标：双击或菜单唤起主窗口，也可退出程序。"""

from __future__ import annotations

from PySide6.QtGui import QAction
from PySide6.QtWidgets import QMenu, QSystemTrayIcon

from .floating_ball import create_ball_icon


class TrayIcon(QSystemTrayIcon):
    def __init__(self, on_show_main, on_quit) -> None:
        super().__init__()
        self.setIcon(create_ball_icon(48))
        self.setToolTip("AI 桌面助手 - 单击悬浮球唤起")

        menu = QMenu()
        show_action = QAction("打开主窗口", menu)
        show_action.triggered.connect(on_show_main)
        quit_action = QAction("退出", menu)
        quit_action.triggered.connect(on_quit)
        menu.addAction(show_action)
        menu.addAction(quit_action)
        self.setContextMenu(menu)

        # 双击托盘图标唤起主窗口
        self.activated.connect(
            lambda reason: on_show_main()
            if reason == QSystemTrayIcon.DoubleClick
            else None
        )

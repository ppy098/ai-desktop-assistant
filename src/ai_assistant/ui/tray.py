"""系统托盘图标：双击或菜单唤起面板，可打开设置或退出程序。"""

from __future__ import annotations

from PySide6.QtGui import QAction
from PySide6.QtWidgets import QMenu, QSystemTrayIcon

from .floating_ball import create_ball_icon
from .themes import Theme, get_theme


class TrayIcon(QSystemTrayIcon):
    def __init__(self, on_show_panel, on_settings, on_quit, theme: Theme | None = None) -> None:
        super().__init__()
        self._theme = theme or get_theme(None)
        self.setIcon(create_ball_icon(48, self._theme))
        self.setToolTip("AI 桌面助手 - 单击悬浮球唤起")

        menu = QMenu()
        show_action = QAction("展开面板", menu)
        show_action.triggered.connect(on_show_panel)
        settings_action = QAction("设置", menu)
        settings_action.triggered.connect(on_settings)
        quit_action = QAction("退出", menu)
        quit_action.triggered.connect(on_quit)
        menu.addAction(show_action)
        menu.addAction(settings_action)
        menu.addSeparator()
        menu.addAction(quit_action)
        self.setContextMenu(menu)

        # 双击托盘图标唤起面板
        self.activated.connect(
            lambda reason: on_show_panel()
            if reason == QSystemTrayIcon.DoubleClick
            else None
        )

    def apply_theme(self, theme: Theme) -> None:
        """换肤时同步托盘图标颜色。"""
        self._theme = theme
        self.setIcon(create_ball_icon(48, theme))

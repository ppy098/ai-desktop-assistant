"""程序启动入口：悬浮球 + 系统托盘常驻，点击球从球后面展开对话面板。

交互：
- 单击悬浮球：从球位置滑出/收起对话面板（非独立窗口）；
- 拖动悬浮球：面板若展开则跟随移动；
- 设置：球右键 / 托盘菜单 / 面板齿轮，可配置 API Key 与个性化皮肤。
"""

from __future__ import annotations

import sys

from PySide6.QtCore import QEasingCurve, QPoint, QVariantAnimation
from PySide6.QtWidgets import QApplication

from .core.config import load_settings, save_settings
from .ui.floating_ball import BALL_SIZE, FloatingBall, create_ball_icon
from .ui.main_window import PANEL_HEIGHT, PANEL_WIDTH, MainPanel
from .ui.settings_dialog import SettingsDialog
from .ui.themes import get_theme
from .ui.tray import TrayIcon


class ApplicationController:
    """协调悬浮球、托盘、对话面板与设置。"""

    def __init__(self) -> None:
        self._settings = load_settings()

        self._panel = MainPanel(self._settings)
        self._panel.request_collapse.connect(self.collapse_panel)
        self._panel.request_open_settings.connect(self.open_settings)

        self._ball = FloatingBall(get_theme(self._settings.theme))
        self._ball.request_toggle_panel.connect(self.toggle_panel)
        self._ball.request_open_settings.connect(self.open_settings)
        self._ball.request_quit.connect(self.quit)
        self._ball.position_changed.connect(self._on_ball_moved)
        self._ball.show()

        self._tray = TrayIcon(self.show_panel, self.open_settings, self.quit)
        self._tray.show()

        self._anim: QVariantAnimation | None = None

    # ------------------------------------------------------------------
    # 展开 / 收起
    # ------------------------------------------------------------------

    def toggle_panel(self) -> None:
        if self._panel.isVisible():
            self.collapse_panel()
        else:
            self.expand_panel()

    def show_panel(self) -> None:
        if self._panel.isVisible():
            self._panel.raise_()
            self._panel.activateWindow()
        else:
            self.expand_panel()

    def expand_panel(self) -> None:
        if self._anim is not None:
            self._anim.stop()
        target = self._panel_pos()
        self._panel.show()
        self._panel.raise_()
        # 从球的位置滑向最终位置，产生“从球后面展开”的效果
        self._animate(self._panel.pos(), target, 220, QEasingCurve.OutCubic)

    def collapse_panel(self) -> None:
        if self._anim is not None:
            self._anim.stop()
        start = self._panel.pos()
        target = QPoint(self._ball.x(), self._ball.y())

        def _finish() -> None:
            self._panel.hide()

        anim = QVariantAnimation(self._panel)
        anim.setDuration(180)
        anim.setStartValue(start)
        anim.setEndValue(target)
        anim.setEasingCurve(QEasingCurve.InCubic)
        anim.valueChanged.connect(lambda value: self._panel.move(value))
        anim.finished.connect(_finish)
        self._anim = anim
        anim.start()

    def _animate(self, start: QPoint, end: QPoint, duration: int, curve) -> None:
        anim = QVariantAnimation(self._panel)
        anim.setDuration(duration)
        anim.setStartValue(start)
        anim.setEndValue(end)
        anim.setEasingCurve(curve)
        anim.valueChanged.connect(lambda value: self._panel.move(value))
        self._anim = anim
        anim.start()

    def _panel_pos(self) -> QPoint:
        """计算面板位置：优先放在球正上方，空间不足时放球左侧。"""
        available = self._ball.screen().availableGeometry()
        bx, by = self._ball.x(), self._ball.y()
        margin = 8

        x = bx + BALL_SIZE // 2 - PANEL_WIDTH // 2
        x = max(available.left() + margin, min(x, available.right() - PANEL_WIDTH - margin))
        y = by - PANEL_HEIGHT - margin
        if y >= available.top() + margin:
            return QPoint(x, y)

        # 上方空间不足：放球左侧
        x = bx - PANEL_WIDTH - margin
        if x < available.left() + margin:
            x = bx + BALL_SIZE + margin
        y = by + BALL_SIZE // 2 - PANEL_HEIGHT // 2
        y = max(available.top() + margin, min(y, available.bottom() - PANEL_HEIGHT - margin))
        return QPoint(x, y)

    def _on_ball_moved(self) -> None:
        if self._panel.isVisible():
            if self._anim is not None:
                self._anim.stop()
            self._panel.move(self._panel_pos())

    # ------------------------------------------------------------------
    # 设置
    # ------------------------------------------------------------------

    def open_settings(self) -> None:
        dialog = SettingsDialog(self._settings, parent=self._panel)
        if dialog.exec():
            self._settings = dialog.saved_settings
            save_settings(self._settings)
            # 应用新皮肤、新模式与新 Key
            theme = get_theme(self._settings.theme)
            self._panel.update_settings(self._settings)
            self._panel.apply_theme(theme)
            self._ball.apply_theme(theme)
            self._tray.setIcon(create_ball_icon(48, theme))

    def quit(self) -> None:
        self._tray.hide()
        self._ball.hide()
        self._panel.hide()
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

"""右下角悬浮球：无边框圆形窗口，常驻桌面顶层。

交互：
- 左键单击：显示/隐藏主窗口；
- 按住拖动：改变位置；
- 右键：菜单（显示主窗口、退出）。
"""

from __future__ import annotations

from PySide6.QtCore import QPoint, Qt, Signal
from PySide6.QtGui import (
    QAction,
    QColor,
    QIcon,
    QLinearGradient,
    QPainter,
    QPen,
    QPixmap,
)
from PySide6.QtWidgets import QMenu, QWidget

BALL_SIZE = 64
# 点击与拖动的判定阈值（像素），小于该移动距离视为点击
_CLICK_THRESHOLD = 6


def create_ball_icon(size: int = 64) -> QIcon:
    """绘制蓝绿渐变圆形图标，悬浮球与系统托盘共用。"""
    pixmap = QPixmap(size, size)
    pixmap.fill(Qt.transparent)
    painter = QPainter(pixmap)
    painter.setRenderHint(QPainter.Antialiasing)

    gradient = QLinearGradient(0, 0, size, size)
    gradient.setColorAt(0.0, QColor("#2f80ed"))
    gradient.setColorAt(1.0, QColor("#12b886"))
    painter.setBrush(gradient)
    painter.setPen(QPen(QColor(255, 255, 255, 180), 2))
    painter.drawEllipse(2, 2, size - 4, size - 4)

    painter.setPen(QPen(QColor("white")))
    font = painter.font()
    font.setBold(True)
    font.setPixelSize(int(size * 0.32))
    painter.font()
    painter.setFont(font)
    painter.drawText(pixmap.rect(), Qt.AlignCenter, "AI")
    painter.end()
    return QIcon(pixmap)


class FloatingBall(QWidget):
    """悬浮球窗口。"""

    request_show_main = Signal()
    request_quit = Signal()

    def __init__(self) -> None:
        super().__init__()
        self.setWindowFlags(
            Qt.FramelessWindowHint
            | Qt.WindowStaysOnTopHint
            | Qt.Tool  # 不在任务栏显示按钮
        )
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setFixedSize(BALL_SIZE, BALL_SIZE)

        self._drag_offset = QPoint()
        self._press_pos = QPoint()
        self._moved = False

        self._menu = QMenu(self)
        show_action = QAction("打开主窗口", self)
        show_action.triggered.connect(self.request_show_main)
        quit_action = QAction("退出", self)
        quit_action.triggered.connect(self.request_quit)
        self._menu.addAction(show_action)
        self._menu.addAction(quit_action)

        self.move_to_bottom_right()

    def move_to_bottom_right(self) -> None:
        """定位到主屏幕可用区域（排除任务栏）的右下角。"""
        screen = self.screen().availableGeometry()
        x = screen.right() - BALL_SIZE - 12
        y = screen.bottom() - BALL_SIZE - 12
        self.move(x, y)

    def paintEvent(self, event) -> None:  # noqa: N802 - Qt 命名
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        gradient = QLinearGradient(0, 0, BALL_SIZE, BALL_SIZE)
        gradient.setColorAt(0.0, QColor("#2f80ed"))
        gradient.setColorAt(1.0, QColor("#12b866"))
        painter.setBrush(gradient)
        painter.setPen(QPen(QColor(255, 255, 255, 200), 2))
        painter.drawEllipse(3, 3, BALL_SIZE - 6, BALL_SIZE - 6)

        painter.setPen(QPen(QColor("white")))
        font = painter.font()
        font.setBold(True)
        font.setPixelSize(20)
        painter.setFont(font)
        painter.drawText(self.rect(), Qt.AlignCenter, "AI")

    def mousePressEvent(self, event) -> None:  # noqa: N802
        if event.button() == Qt.LeftButton:
            self._press_pos = event.globalPosition().toPoint()
            self._drag_offset = event.globalPosition().toPoint() - self.frameGeometry().topLeft()
            self._moved = False

    def mouseMoveEvent(self, event) -> None:  # noqa: N802
        if event.buttons() & Qt.LeftButton:
            distance = (event.globalPosition().toPoint() - self._press_pos).manhattanLength()
            if distance > _CLICK_THRESHOLD:
                self._moved = True
                self.move(event.globalPosition().toPoint() - self._drag_offset)

    def mouseReleaseEvent(self, event) -> None:  # noqa: N802
        if event.button() == Qt.LeftButton and not self._moved:
            self.request_show_main.emit()

    def contextMenuEvent(self, event) -> None:  # noqa: N802
        self._menu.exec(event.globalPos())

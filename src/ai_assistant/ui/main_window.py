"""展开面板：从悬浮球后面滑出的对话面板（无边框、圆角、非独立窗口）。

保留对话展示与指令输入；AI 调用放在独立线程中执行，避免网络请求阻塞界面。
"""

from __future__ import annotations

from html import escape

from PySide6.QtCore import QObject, QThread, Qt, Signal
from PySide6.QtWidgets import (
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QTextBrowser,
    QVBoxLayout,
    QWidget,
)

from ..core.agent import AgentResponse, Assistant
from ..core.config import Settings
from .themes import Theme, get_theme, panel_style

PANEL_WIDTH = 400
PANEL_HEIGHT = 480


class _Worker(QObject):
    finished = Signal(object)

    def __init__(self, assistant: Assistant, text: str):
        super().__init__()
        self._assistant = assistant
        self._text = text

    def run(self) -> None:
        self.finished.emit(self._assistant.handle(self._text))


class MainPanel(QWidget):
    """从悬浮球后面展开的对话面板。"""

    request_collapse = Signal()
    request_open_settings = Signal()

    def __init__(self, settings: Settings, theme: Theme | None = None):
        super().__init__()
        self._assistant = Assistant(settings)
        self._thread: QThread | None = None
        self._theme = theme or get_theme(settings.theme)

        self.setWindowFlags(
            Qt.FramelessWindowHint
            | Qt.WindowStaysOnTopHint
            | Qt.Tool  # 不在任务栏显示按钮
        )
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setFixedSize(PANEL_WIDTH, PANEL_HEIGHT)
        self.setObjectName("panel")
        self.apply_theme(self._theme)

        # 顶部栏：标题 + 模式 + 设置 + 收起
        title = QLabel("AI 桌面助手")
        title.setObjectName("title")
        self._mode_label = QLabel()
        self._mode_label.setObjectName("mode_label")

        settings_btn = QPushButton("⚙")
        settings_btn.setObjectName("close_btn")
        settings_btn.setToolTip("设置")
        settings_btn.clicked.connect(self.request_open_settings)
        close_btn = QPushButton("✕")
        close_btn.setObjectName("close_btn")
        close_btn.setToolTip("收起面板")
        close_btn.clicked.connect(self.request_collapse)

        head = QHBoxLayout()
        head.addWidget(title)
        head.addStretch(1)
        head.addWidget(self._mode_label)
        head.addWidget(settings_btn)
        head.addWidget(close_btn)

        self._chat = QTextBrowser()
        self._chat.setObjectName("chat")
        self._chat.setOpenExternalLinks(True)
        self._chat.append("你好，我是 AI 桌面助手，可以帮你打开软件、创建文件、浏览器搜索。<br>")

        self._input = QLineEdit()
        self._input.setObjectName("input")
        self._input.setPlaceholderText("输入指令，例如：打开记事本，再搜一下青岛天气")
        self._input.returnPressed.connect(self._on_send)

        self._send_button = QPushButton("发送")
        self._send_button.setObjectName("send")
        self._send_button.clicked.connect(self._on_send)

        bottom = QHBoxLayout()
        bottom.addWidget(self._input, stretch=1)
        bottom.addWidget(self._send_button)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 10, 12, 12)
        layout.addLayout(head)
        layout.addWidget(self._chat, stretch=1)
        layout.addLayout(bottom)

        self.update_mode(settings)

    # ------------------------------------------------------------------
    # 主题 / 模式
    # ------------------------------------------------------------------

    def apply_theme(self, theme: Theme) -> None:
        """应用皮肤（QSS），并同步模式标签颜色。"""
        self._theme = theme
        self.setStyleSheet(panel_style(theme))
        if hasattr(self, "_mode"):
            color = theme.mode_online if self._mode == "online" else theme.mode_local
            self._mode_label.setStyleSheet(f"color: {color}; font-size: 11px; background: transparent;")

    def update_mode(self, settings: Settings) -> None:
        """刷新模式标签：在线 / 本地规则。"""
        self._mode = "online" if settings.has_api_key else "local"
        text = "在线模式" if self._mode == "online" else "本地规则模式（未配置 API Key）"
        self._mode_label.setText(text)
        color = self._theme.mode_online if self._mode == "online" else self._theme.mode_local
        self._mode_label.setStyleSheet(f"color: {color}; font-size: 11px; background: transparent;")

    def update_settings(self, settings: Settings) -> None:
        """设置保存后刷新：替换 Assistant（新的 Key/模型）并更新模式。"""
        self._assistant = Assistant(settings)
        self.update_mode(settings)

    # ------------------------------------------------------------------
    # 对话逻辑
    # ------------------------------------------------------------------

    def _on_send(self) -> None:
        text = self._input.text().strip()
        if not text or self._thread is not None:
            return

        self._chat.append(f"<b>你：</b>{escape(text)}<br>")
        self._input.clear()
        self._set_busy(True)

        thread = QThread(self)
        worker = _Worker(self._assistant, text)
        worker.moveToThread(thread)
        thread.started.connect(worker.run)
        worker.finished.connect(self._on_finished)
        worker.finished.connect(thread.quit)
        thread.finished.connect(worker.deleteLater)
        thread.finished.connect(thread.deleteLater)
        self._thread = thread
        thread.start()

    def _on_finished(self, response: AgentResponse) -> None:
        self._thread = None
        self._set_busy(False)
        color = self._theme.mode_online if response.mode == "online" else self._theme.mode_local
        self._chat.append(
            f"<b style='color:{color}'>助手：</b>{escape(response.reply)}<br><br>"
        )
        self._input.setFocus()

    def _set_busy(self, busy: bool) -> None:
        self._input.setEnabled(not busy)
        self._send_button.setEnabled(not busy)
        self._send_button.setText("处理中…" if busy else "发送")

    def closeEvent(self, event) -> None:  # noqa: N802
        # 面板关闭等同收起，程序继续常驻
        event.ignore()
        self.hide()

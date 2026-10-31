"""主窗口：对话展示 + 指令输入。

AI 调用放在独立线程中执行，避免网络请求阻塞界面。
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


class _Worker(QObject):
    finished = Signal(object)

    def __init__(self, assistant: Assistant, text: str):
        super().__init__()
        self._assistant = assistant
        self._text = text

    def run(self) -> None:
        self.finished.emit(self._assistant.handle(self._text))


class MainWindow(QWidget):
    def __init__(self, settings: Settings):
        super().__init__()
        self._assistant = Assistant(settings)
        self._thread: QThread | None = None

        self.setWindowTitle("AI 桌面助手")
        self.resize(640, 520)

        mode_text = "在线模式" if settings.has_api_key else "本地规则模式（未配置 API Key）"
        self._mode_label = QLabel(mode_text)

        self._chat = QTextBrowser()
        self._chat.setOpenExternalLinks(True)
        self._chat.append("你好，我是 AI 桌面助手，可以帮你打开软件、创建文件、浏览器搜索。<br>")

        self._input = QLineEdit()
        self._input.setPlaceholderText("输入指令，例如：打开记事本，再搜一下青岛天气")
        self._input.returnPressed.connect(self._on_send)

        self._send_button = QPushButton("发送")
        self._send_button.clicked.connect(self._on_send)

        bottom = QHBoxLayout()
        bottom.addWidget(self._input)
        bottom.addWidget(self._send_button)

        layout = QVBoxLayout(self)
        layout.addWidget(self._mode_label)
        layout.addWidget(self._chat, stretch=1)
        layout.addLayout(bottom)

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
        color = "#1a7f37" if response.mode == "online" else "#8a6d00"
        self._chat.append(
            f"<b style='color:{color}'>助手：</b>{escape(response.reply)}<br><br>"
        )
        self._input.setFocus()

    def _set_busy(self, busy: bool) -> None:
        self._input.setEnabled(not busy)
        self._send_button.setEnabled(not busy)
        self._send_button.setText("处理中…" if busy else "发送")

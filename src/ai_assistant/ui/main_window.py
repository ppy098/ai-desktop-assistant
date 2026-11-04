"""展开面板：从悬浮球后面滑出的对话面板（无边框、圆角、非独立窗口）。

功能：
- 对话展示与指令输入，AI 调用在独立线程执行，避免阻塞界面；
- 快捷指令：截屏 / 时间 / 剪贴板 / 电脑状态 / 清空对话；
- 对话记录持久化到 ~/.ai_desktop_assistant/history.jsonl，重启后回显最近记录。
"""

from __future__ import annotations

import json
from datetime import datetime
from html import escape
from pathlib import Path

from PySide6.QtCore import QObject, QThread, Qt, Signal
from PySide6.QtGui import QColor, QPainter, QPen
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

_HISTORY_FILE = Path.home() / ".ai_desktop_assistant" / "history.jsonl"
_HISTORY_RESTORE_LIMIT = 20

_WELCOME = (
    "你好，我是 AI 桌面助手。可以帮你打开软件、创建文件、浏览器搜索、"
    "打开网址、截屏、读写剪贴板、查看电脑状态。<br>"
)

# 快捷按钮：显示文字 -> 提交的指令；指令为空表示特殊动作
_CHIPS: tuple[tuple[str, str], ...] = (
    ("截屏", "截屏"),
    ("时间", "现在几点"),
    ("剪贴板", "看看剪贴板"),
    ("电脑状态", "电脑状态"),
)


# ----------------------------------------------------------------------
# 对话记录持久化
# ----------------------------------------------------------------------


def _append_history(role: str, text: str) -> None:
    """追加一条对话记录（失败静默，不影响主流程）。"""
    if not text:
        return
    try:
        _HISTORY_FILE.parent.mkdir(parents=True, exist_ok=True)
        with _HISTORY_FILE.open("a", encoding="utf-8") as handle:
            handle.write(
                json.dumps(
                    {
                        "role": role,
                        "text": text,
                        "ts": datetime.now().isoformat(timespec="seconds"),
                    },
                    ensure_ascii=False,
                )
                + "\n"
            )
    except OSError:
        pass


def _load_history(limit: int = _HISTORY_RESTORE_LIMIT) -> list[dict]:
    """读取最近若干条对话记录。"""
    try:
        if not _HISTORY_FILE.exists():
            return []
        lines = _HISTORY_FILE.read_text(encoding="utf-8").splitlines()
    except (OSError, UnicodeDecodeError):
        return []
    records: list[dict] = []
    for line in lines[-limit:]:
        line = line.strip()
        if not line:
            continue
        try:
            record = json.loads(line)
        except json.JSONDecodeError:
            continue
        if (
            isinstance(record, dict)
            and record.get("role") in ("user", "assistant")
            and str(record.get("text", "")).strip()
        ):
            records.append(record)
    return records


def _clear_history() -> None:
    try:
        _HISTORY_FILE.unlink()
    except OSError:
        pass


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
        # 自定义 QWidget 子类默认不绘制 QSS 背景，需显式开启，否则面板下半部分透明
        self.setAttribute(Qt.WA_StyledBackground, True)
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
        self._chat.setMinimumHeight(80)
        self._chat.setOpenExternalLinks(True)
        self._chat.append(_WELCOME + "<br>")
        self._restore_history()

        # 快捷指令按钮行（独立容器固定高度，避免布局压缩后与输入框叠压）
        chips_host = QWidget()
        chips_host.setFixedHeight(28)
        chips = QHBoxLayout(chips_host)
        chips.setContentsMargins(0, 0, 0, 0)
        chips.setSpacing(6)
        for label, command in _CHIPS:
            chip = QPushButton(label)
            chip.setObjectName("chip")
            chip.setFixedHeight(24)
            chip.setCursor(Qt.PointingHandCursor)
            chip.clicked.connect(lambda _checked=False, cmd=command: self._send_text(cmd))
            chips.addWidget(chip)
        clear_chip = QPushButton("清空")
        clear_chip.setObjectName("chip")
        clear_chip.setFixedHeight(24)
        clear_chip.setCursor(Qt.PointingHandCursor)
        clear_chip.setToolTip("清空对话记录")
        clear_chip.clicked.connect(self._clear_chat)
        chips.addWidget(clear_chip)
        chips.addStretch(1)

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
        layout.addWidget(chips_host)
        layout.addLayout(bottom)

        self.update_mode(settings)

    # ------------------------------------------------------------------
    # 绘制 / 主题
    # ------------------------------------------------------------------

    def paintEvent(self, event) -> None:  # noqa: N802 - Qt 命名
        """自绘圆角面板背景，避免依赖 QSS 对自定义 QWidget 的背景支持。"""
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        painter.setBrush(QColor(self._theme.panel_bg))
        painter.setPen(QPen(QColor(self._theme.panel_border), 1))
        painter.drawRoundedRect(self.rect().adjusted(0, 0, -1, -1), 14, 14)

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
    # 对话记录
    # ------------------------------------------------------------------

    def _restore_history(self) -> None:
        """启动时回显最近对话。"""
        records = _load_history()
        if not records:
            return
        self._chat.append("<i>（已恢复上次的对话记录）</i><br><br>")
        for record in records:
            if record["role"] == "user":
                self._chat.append(f"<b>你：</b>{escape(str(record['text']))}<br>")
            else:
                self._chat.append(f"<b>助手：</b>{escape(str(record['text']))}<br><br>")

    def _clear_chat(self) -> None:
        """清空对话与历史记录。"""
        if self._thread is not None:
            return
        self._chat.clear()
        _clear_history()
        self._chat.append(_WELCOME + "<br>")

    # ------------------------------------------------------------------
    # 对话逻辑
    # ------------------------------------------------------------------

    def _send_text(self, text: str) -> None:
        """快捷按钮：填入指令并立即发送。"""
        if self._thread is not None or not text:
            return
        self._input.setText(text)
        self._on_send()

    def _on_send(self) -> None:
        text = self._input.text().strip()
        if not text or self._thread is not None:
            return

        self._chat.append(f"<b>你：</b>{escape(text)}<br>")
        _append_history("user", text)
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
        _append_history("assistant", response.reply)
        self._input.setFocus()

    def _set_busy(self, busy: bool) -> None:
        self._input.setEnabled(not busy)
        self._send_button.setEnabled(not busy)
        self._send_button.setText("处理中…" if busy else "发送")

    def closeEvent(self, event) -> None:  # noqa: N802
        # 面板关闭等同收起，程序继续常驻
        event.ignore()
        self.hide()

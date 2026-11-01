"""设置对话框：API Key 登录、接口地址/模型/搜索引擎、个性化皮肤。

保存后写入 settings.json，并通过 on_saved 回调通知主程序应用新设置。
"""

from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QDialog,
    QFormLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QVBoxLayout,
)

from ..core.config import Settings
from ..ui.themes import THEMES

_DIALOG_STYLE = """
QDialog { background: #f6f8fa; }
QLabel#tip { color: #57606a; font-size: 12px; }
QPushButton { border-radius: 8px; padding: 6px 14px; }
QPushButton#primary {
    background: #2f80ed; color: white; border: none;
}
QPushButton#primary:hover { background: #1f6fd0; }
QPushButton#secondary {
    background: #ffffff; border: 1px solid #d0d7de; color: #1f2328;
}
QPushButton#secondary:hover { background: #f0f1f3; }
QLineEdit, QComboBox {
    border: 1px solid #d0d7de; border-radius: 6px; padding: 5px 8px;
    background: #ffffff;
}
QCheckBox { color: #1f2328; }
"""


class SettingsDialog(QDialog):
    def __init__(self, settings: Settings, parent=None):
        super().__init__(parent)
        self.setWindowTitle("AI 桌面助手 - 设置")
        self.setMinimumWidth(460)
        self.setStyleSheet(_DIALOG_STYLE)

        self._api_key = QLineEdit(settings.api_key)
        self._api_key.setEchoMode(QLineEdit.Password)
        self._api_key.setPlaceholderText("粘贴 32 位 API Key")
        self._show_key = QCheckBox("显示")
        self._show_key.toggled.connect(
            lambda checked: self._api_key.setEchoMode(
                QLineEdit.Normal if checked else QLineEdit.Password
            )
        )

        self._base_url = QLineEdit(settings.base_url)
        self._base_url.setPlaceholderText("https://ark.cn-beijing.volces.com/api/v3")
        self._model = QLineEdit(settings.model)
        self._model.setPlaceholderText("如 doubao-seed-1-6-250615 或推理接入点 ep-xxx")

        self._engine = QComboBox()
        for name in ("bing", "baidu", "google", "sogou"):
            self._engine.addItem(name)
        self._engine.setCurrentText(settings.search_engine)

        self._theme = QComboBox()
        for name in THEMES:
            self._theme.addItem(name)
        self._theme.setCurrentText(settings.theme)

        form = QFormLayout()
        api_row = QHBoxLayout()
        api_row.addWidget(self._api_key, stretch=1)
        api_row.addWidget(self._show_key)
        form.addRow("API Key", api_row)
        form.addRow("接口地址", self._base_url)
        form.addRow("模型", self._model)
        form.addRow("搜索引擎", self._engine)
        form.addRow("皮肤", self._theme)

        tip = QLabel("Key 只保存在本机 settings.json，不会上传 GitHub。")
        tip.setObjectName("tip")

        test_btn = QPushButton("测试连接")
        test_btn.setObjectName("secondary")
        test_btn.clicked.connect(self._test_connection)
        save_btn = QPushButton("保存")
        save_btn.setObjectName("primary")
        save_btn.clicked.connect(self._on_save)
        cancel_btn = QPushButton("取消")
        cancel_btn.setObjectName("secondary")
        cancel_btn.clicked.connect(self.reject)

        buttons = QHBoxLayout()
        buttons.addWidget(test_btn)
        buttons.addStretch(1)
        buttons.addWidget(cancel_btn)
        buttons.addWidget(save_btn)

        layout = QVBoxLayout(self)
        layout.addLayout(form)
        layout.addWidget(tip)
        layout.addLayout(buttons)

    def _current_settings(self) -> Settings:
        return Settings(
            base_url=self._base_url.text().strip() or "https://ark.cn-beijing.volces.com/api/v3",
            api_key=self._api_key.text().strip(),
            model=self._model.text().strip() or "doubao-seed-1-6-250615",
            search_engine=self._engine.currentText().strip().lower(),
            theme=self._theme.currentText(),
        )

    def _test_connection(self) -> None:
        """用当前填写的 Key 发一个最小请求验证连通性。"""
        settings = self._current_settings()
        if not settings.has_api_key:
            QMessageBox.warning(self, "提示", "请先填写 API Key")
            return
        try:
            from openai import OpenAI

            client = OpenAI(base_url=settings.base_url, api_key=settings.api_key)
            response = client.chat.completions.create(
                model=settings.model,
                messages=[{"role": "user", "content": "你好"}],
                max_tokens=1,
                temperature=0,
            )
            text = (response.choices[0].message.content or "").strip() or "连接成功"
            QMessageBox.information(self, "测试连接", f"连接成功，模型回复：{text}")
        except Exception as exc:  # noqa: BLE001 - 给用户展示原始错误便于排查
            QMessageBox.critical(self, "测试连接", f"连接失败：{exc}")

    def _on_save(self) -> None:
        settings = self._current_settings()
        if not settings.has_api_key:
            QMessageBox.warning(self, "提示", "API Key 不能为空，请先填写后再保存。")
            return
        self.saved_settings = settings
        self.accept()

    # 供调用方读取
    saved_settings: Settings | None = None

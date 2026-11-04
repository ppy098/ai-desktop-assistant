"""皮肤主题：一套皮肤定义面板/悬浮球/按钮等全部配色。

新增皮肤只需在 THEMES 中增加一项，字段与现有项保持一致。
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Theme:
    name: str
    # 面板
    panel_bg: str
    panel_border: str
    title_color: str
    mode_label_color: str
    close_color: str
    close_hover_bg: str
    close_hover_color: str
    # 聊天区
    chat_bg: str
    chat_text: str
    # 输入框
    input_bg: str
    input_border: str
    input_text: str
    # 按钮
    button_bg: str
    button_hover: str
    button_text: str
    # 悬浮球渐变
    ball_start: str
    ball_end: str
    ball_border: str
    # 在线/本地模式提示颜色
    mode_online: str
    mode_local: str


THEMES: dict[str, Theme] = {
    "浅色": Theme(
        name="浅色",
        panel_bg="#ffffff",
        panel_border="rgba(47, 128, 237, 0.45)",
        title_color="#1f2328",
        mode_label_color="#8a6d00",
        close_color="#57606a",
        close_hover_bg="#f0f1f3",
        close_hover_color="#cf222e",
        chat_bg="#fafbfc",
        chat_text="#1f2328",
        input_bg="#ffffff",
        input_border="#d0d7de",
        input_text="#1f2328",
        button_bg="#2f80ed",
        button_hover="#1f6fd0",
        button_text="#ffffff",
        ball_start="#2f80ed",
        ball_end="#12b886",
        ball_border="rgba(255, 255, 255, 200)",
        mode_online="#1a7f37",
        mode_local="#8a6d00",
    ),
    "深色": Theme(
        name="深色",
        panel_bg="#1e2228",
        panel_border="rgba(88, 166, 255, 0.55)",
        title_color="#e6edf3",
        mode_label_color="#d29922",
        close_color="#9da7b3",
        close_hover_bg="#2d333b",
        close_hover_color="#ff7b72",
        chat_bg="#16181d",
        chat_text="#e6edf3",
        input_bg="#22262d",
        input_border="#444c56",
        input_text="#e6edf3",
        button_bg="#2f81f7",
        button_hover="#58a6ff",
        button_text="#ffffff",
        ball_start="#1f6feb",
        ball_end="#238636",
        ball_border="rgba(255, 255, 255, 160)",
        mode_online="#3fb950",
        mode_local="#d29922",
    ),
    "薄荷": Theme(
        name="薄荷",
        panel_bg="#f2fbf6",
        panel_border="rgba(18, 184, 134, 0.5)",
        title_color="#0f3d2e",
        mode_label_color="#8a6d00",
        close_color="#5c7a6e",
        close_hover_bg="#d8f3e6",
        close_hover_color="#b3261e",
        chat_bg="#ffffff",
        chat_text="#0f3d2e",
        input_bg="#ffffff",
        input_border="#a8dcc9",
        input_text="#0f3d2e",
        button_bg="#12b886",
        button_hover="#0ca678",
        button_text="#ffffff",
        ball_start="#12b886",
        ball_end="#38d9a9",
        ball_border="rgba(255, 255, 255, 200)",
        mode_online="#0ca678",
        mode_local="#8a6d00",
    ),
    "海洋": Theme(
        name="海洋",
        panel_bg="#eef6ff",
        panel_border="rgba(37, 99, 235, 0.5)",
        title_color="#10233f",
        mode_label_color="#8a6d00",
        close_color="#4c6a8f",
        close_hover_bg="#d6e8ff",
        close_hover_color="#c0252a",
        chat_bg="#ffffff",
        chat_text="#10233f",
        input_bg="#ffffff",
        input_border="#9cc2f0",
        input_text="#10233f",
        button_bg="#2563eb",
        button_hover="#1d4ed8",
        button_text="#ffffff",
        ball_start="#2563eb",
        ball_end="#06b6d4",
        ball_border="rgba(255, 255, 255, 200)",
        mode_online="#1d4ed8",
        mode_local="#8a6d00",
    ),
    "日落": Theme(
        name="日落",
        panel_bg="#fff7ed",
        panel_border="rgba(249, 115, 22, 0.5)",
        title_color="#431407",
        mode_label_color="#9a6700",
        close_color="#8a6a5a",
        close_hover_bg="#ffedd5",
        close_hover_color="#dc2626",
        chat_bg="#ffffff",
        chat_text="#431407",
        input_bg="#ffffff",
        input_border="#fdba74",
        input_text="#431407",
        button_bg="#f97316",
        button_hover="#ea580c",
        button_text="#ffffff",
        ball_start="#f97316",
        ball_end="#f43f5e",
        ball_border="rgba(255, 255, 255, 200)",
        mode_online="#ea580c",
        mode_local="#9a6700",
    ),
}

DEFAULT_THEME = "浅色"


def get_theme(name: str | None) -> Theme:
    if name in THEMES:
        return THEMES[name]
    return THEMES[DEFAULT_THEME]


def panel_style(theme: Theme) -> str:
    """按主题生成面板 QSS。"""
    return f"""
#panel {{
    background: {theme.panel_bg};
    border-radius: 14px;
    border: 1px solid {theme.panel_border};
}}
QLabel#title {{
    color: {theme.title_color};
    font-size: 14px;
    font-weight: bold;
    background: transparent;
}}
QLabel#mode_label {{
    color: {theme.mode_label_color};
    font-size: 11px;
    background: transparent;
}}
QPushButton#close_btn {{
    border: none;
    background: transparent;
    color: {theme.close_color};
    font-size: 14px;
    padding: 2px 8px;
}}
QPushButton#close_btn:hover {{
    background: {theme.close_hover_bg};
    border-radius: 6px;
    color: {theme.close_hover_color};
}}
QTextBrowser#chat {{
    border: none;
    background: {theme.chat_bg};
    border-radius: 10px;
    padding: 8px;
    font-size: 13px;
    color: {theme.chat_text};
}}
QLineEdit#input {{
    border: 1px solid {theme.input_border};
    border-radius: 8px;
    padding: 6px 10px;
    font-size: 13px;
    background: {theme.input_bg};
    color: {theme.input_text};
}}
QPushButton#send {{
    background: {theme.button_bg};
    color: {theme.button_text};
    border: none;
    border-radius: 8px;
    padding: 6px 16px;
    font-size: 13px;
}}
QPushButton#send:hover {{ background: {theme.button_hover}; }}
QPushButton#send:disabled {{ background: #a5b6cf; }}
QPushButton#chip {{
    background: transparent;
    border: 1px solid {theme.input_border};
    border-radius: 10px;
    color: {theme.close_color};
    font-size: 11px;
    padding: 2px 10px;
}}
QPushButton#chip:hover {{
    background: {theme.close_hover_bg};
    border: 1px solid {theme.panel_border};
    color: {theme.title_color};
}}
"""

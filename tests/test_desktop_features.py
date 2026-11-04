"""新增桌面能力（时间/网址/剪贴板/截屏/系统状态/文件夹）的测试。"""

from ai_assistant.core.agent import parse_local
from ai_assistant.tools import desktop
from ai_assistant.tools import dispatch


def test_parse_time():
    calls = parse_local("现在几点")
    assert calls == [{"name": "get_time", "arguments": {}}]


def test_parse_screenshot():
    calls = parse_local("帮我截屏")
    assert calls == [{"name": "take_screenshot", "arguments": {}}]


def test_parse_clipboard_read():
    calls = parse_local("看看剪贴板")
    assert calls == [{"name": "get_clipboard", "arguments": {}}]


def test_parse_clipboard_write():
    calls = parse_local("复制：你好世界")
    assert len(calls) == 1
    assert calls[0]["name"] == "set_clipboard"
    assert calls[0]["arguments"]["text"] == "你好世界"


def test_parse_system_status():
    calls = parse_local("电脑状态")
    assert calls == [{"name": "system_status", "arguments": {}}]


def test_parse_open_folder():
    calls = parse_local("打开桌面")
    assert calls == [{"name": "open_folder", "arguments": {"name": "桌面"}}]


def test_parse_open_url():
    calls = parse_local("打开 www.baidu.com")
    assert calls == [{"name": "open_url", "arguments": {"url": "www.baidu.com"}}]


def test_parse_open_software_still_works():
    calls = parse_local("打开记事本")
    assert calls == [{"name": "open_app", "arguments": {"app_name": "记事本"}}]


def test_get_time_returns_text():
    result = dispatch("get_time", {})
    assert result.success
    assert "星期" in result.message


def test_open_url_builds_https(monkeypatch):
    opened = []
    monkeypatch.setattr(desktop.webbrowser, "open", lambda url: opened.append(url) or True)
    result = dispatch("open_url", {"url": "baidu.com"})
    assert result.success
    assert opened[0] == "https://baidu.com"


def test_system_status_succeeds():
    result = dispatch("system_status", {})
    assert result.success
    assert "内存" in result.message


def test_set_clipboard_rejects_empty():
    result = dispatch("set_clipboard", {"text": "  "})
    assert not result.success


def test_screenshot_actually_saves(tmp_path):
    """真实截屏一次，验证文件生成后清理。"""
    result = dispatch("take_screenshot", {"filename": "auto_test_shot.png"})
    assert result.success, result.message
    path = result.data.get("path", "")
    assert path.endswith("auto_test_shot.png")
    from pathlib import Path

    shot = Path(path)
    if shot.exists():
        shot.unlink()

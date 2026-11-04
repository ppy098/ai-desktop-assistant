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


def test_parse_optimize_memory():
    """“优化内存 / 一键内存优化 / 清理内存 / 释放内存”都走内存优化。"""
    for text in ("优化内存", "一键内存优化", "清理一下内存", "释放内存"):
        calls = parse_local(text)
        assert calls and calls[0]["name"] == "optimize_memory", text


def test_parse_memory_status_not_optimize():
    """“内存占用多少”仍是状态查询，不能被误判成优化。"""
    calls = parse_local("内存占用多少")
    assert calls and calls[0]["name"] == "system_status"


def test_optimize_memory_runs():
    """真实执行一次内存优化，能整理到进程并给出报告。"""
    import sys

    if sys.platform != "win32":
        return
    result = desktop.optimize_memory(elevate=False)
    assert "整理" in result.message


def test_parse_clean_disk():
    """清理磁盘相关说法都应解析为 clean_disk。"""
    for text in ("清理磁盘", "清理磁盘垃圾", "清理一下C盘垃圾", "清理系统垃圾", "清空垃圾文件"):
        calls = parse_local(text)
        assert calls and calls[0]["name"] == "clean_disk", text


def test_parse_disk_status_not_clean():
    """“磁盘空间还剩多少”仍应走 system_status，不能被清理规则截走。"""
    calls = parse_local("磁盘空间还剩多少")
    assert calls and calls[0]["name"] == "system_status"


def test_clean_disk_runs_without_elevation():
    """真实执行一次（不提权），返回成功且带释放量字段。"""
    result = desktop.clean_disk(elevate=False)
    assert result.success
    assert "gained_mb" in result.data


def test_parse_show_desktop_and_lock():
    """显示桌面、锁屏各有独立规则，不能被“打开软件/状态查询”截走。"""
    assert parse_local("显示桌面") == [{"name": "show_desktop", "arguments": {}}]
    assert parse_local("锁屏") == [{"name": "lock_screen", "arguments": {}}]


def test_parse_volume():
    """静音与音量加减都解析成 control_volume。"""
    for text in ("静音", "取消静音", "音量调大3", "音量调小", "声音大一点"):
        calls = parse_local(text)
        assert calls and calls[0]["name"] == "control_volume", text


def test_parse_note():
    """记便签与查看便签区分写/读。"""
    calls = parse_local("记一下 明天买菜")
    assert calls[0]["name"] == "quick_note" and calls[0]["arguments"]["text"] == "明天买菜"
    calls = parse_local("看看便签")
    assert calls == [{"name": "quick_note", "arguments": {}}]


def test_parse_calculate_and_text_tool():
    """算式与文本处理分别落到 calculate / text_tool。"""
    assert parse_local("算一下 12*8")[0]["name"] == "calculate"
    assert parse_local("统计字数：你好世界abc")[0]["arguments"]["action"] == "count"
    assert parse_local("转大写：hello")[0]["arguments"]["action"] == "upper"
    assert parse_local("base64编码：你好")[0]["arguments"]["action"] == "b64encode"


def test_calculate_real():
    """真实计算，支持中文乘除号与括号。"""
    from ai_assistant.tools import extras

    assert extras.calculate("12*8").data["result"] == "96"
    assert extras.calculate("(3+5)/2").data["result"] == "4"
    assert extras.calculate("2^10").data["result"] == "1024"
    assert not extras.calculate("1/0").success
    assert not extras.calculate("__import__('os')").success


def test_text_tool_roundtrip():
    """Base64 编解码往返一致，字数统计正确。"""
    from ai_assistant.tools import extras

    encoded = extras.text_tool("你好", "b64encode")
    decoded = extras.text_tool(encoded.message, "b64decode")
    assert decoded.message == "你好"
    stats = extras.text_tool("abc 你好", "count")
    assert stats.data["chars_no_space"] == 5


def test_quick_note_roundtrip(tmp_path, monkeypatch):
    """便签写进去后能读回来（改写到临时目录，不污染用户文件）。"""
    from ai_assistant.tools import extras

    monkeypatch.setattr(extras, "_NOTES_FILE", tmp_path / "notes.md")
    saved = extras.quick_note("测试便签内容")
    assert saved.success
    listed = extras.quick_note("")
    assert "测试便签内容" in listed.message

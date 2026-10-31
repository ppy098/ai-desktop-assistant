"""本地规则解析与工具层的单元测试（不依赖网络和 API Key）。"""

from ai_assistant.core.agent import parse_local
from ai_assistant.tools import dispatch
from ai_assistant.tools import web as web_module


def test_parse_open_app():
    calls = parse_local("打开记事本")
    assert calls == [{"name": "open_app", "arguments": {"app_name": "记事本"}}]


def test_parse_search():
    calls = parse_local("帮我搜一下青岛天气")
    assert len(calls) == 1
    assert calls[0]["name"] == "web_search"
    assert calls[0]["arguments"]["query"] == "青岛天气"


def test_parse_create_file_with_content():
    calls = parse_local("在桌面创建一个 todo.txt，内容是买牛奶")
    assert len(calls) == 1
    args = calls[0]["arguments"]
    assert args["filename"] == "todo.txt"
    assert args["content"] == "买牛奶"
    assert args["directory"] == "桌面"


def test_parse_multiple_actions():
    calls = parse_local("打开计算器，再搜一下C++教程")
    assert [c["name"] for c in calls] == ["open_app", "web_search"]


def test_create_file_actually_writes(tmp_path):
    result = dispatch(
        "create_file",
        {"filename": "hello.txt", "content": "你好", "directory": str(tmp_path)},
    )
    assert result.success
    assert (tmp_path / "hello.txt").read_text(encoding="utf-8") == "你好"


def test_create_file_rejects_path_separator():
    result = dispatch("create_file", {"filename": "..\\evil.txt", "content": "x"})
    assert not result.success


def test_web_search_builds_url(monkeypatch):
    opened = []
    monkeypatch.setattr(web_module.webbrowser, "open", lambda url: opened.append(url) or True)
    result = dispatch("web_search", {"query": "青岛 天气", "engine": "bing"})
    assert result.success
    assert opened[0].startswith("https://www.bing.com/search?q=")
    assert "%E9%9D%92%E5%B2%9B" in opened[0]


def test_unknown_tool():
    result = dispatch("does_not_exist", {})
    assert not result.success

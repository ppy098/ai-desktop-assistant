"""浏览器搜索工具：调用系统默认浏览器打开搜索引擎结果页。"""

from __future__ import annotations

import webbrowser
from urllib.parse import quote

from .base import ToolResult

# 搜索引擎 URL 模板，{query} 会被替换为 URL 编码后的关键词
_ENGINES: dict[str, str] = {
    "bing": "https://www.bing.com/search?q={query}",
    "baidu": "https://www.baidu.com/s?wd={query}",
    "google": "https://www.google.com/search?q={query}",
}


def search(query: str, engine: str = "bing") -> ToolResult:
    """在浏览器中打开搜索结果页。"""
    keyword = (query or "").strip()
    if not keyword:
        return ToolResult(False, "搜索关键词不能为空")

    engine_key = (engine or "bing").strip().lower()
    template = _ENGINES.get(engine_key, _ENGINES["bing"])
    url = template.format(query=quote(keyword))

    opened = webbrowser.open(url)
    if not opened:
        return ToolResult(False, "无法调用系统浏览器")
    return ToolResult(True, f"已在浏览器中搜索：{keyword}", {"url": url})

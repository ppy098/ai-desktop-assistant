"""AI 代理：把自然语言指令变成工具调用。

两种工作模式：
- online：调用 OpenAI 兼容接口，通过 function-calling 决定工具与参数；
- local ：未配置 API Key（或在线调用失败）时，使用本地关键词规则解析。
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass, field

from ..tools import TOOL_SPECS, ToolResult, dispatch
from .config import Settings

_SYSTEM_PROMPT = (
    "你是运行在 Windows 上的中文桌面助手。用户会用自然语言要求你打开软件、"
    "创建文件或浏览器搜索。请优先调用提供的工具完成动作；一条指令包含多个动作时，"
    "一次性发起全部工具调用。工具执行完成后，用一句简短中文汇报结果，不要复述参数。"
)

# 防止工具调用来回嵌套的保护上限
_MAX_TOOL_ROUNDS = 5


@dataclass
class AgentResponse:
    reply: str
    results: list[ToolResult] = field(default_factory=list)
    mode: str = "local"


# ----------------------------------------------------------------------
# 本地规则解析
# ----------------------------------------------------------------------

_SPLIT_PATTERN = re.compile(r"[，,；;]|然后|接着|并且|再(?:帮我)?")
_FILENAME_PATTERN = re.compile(r"[0-9A-Za-z\u4e00-\u9fa5_\-]+\.[A-Za-z0-9]{1,8}")
_CONTENT_PATTERN = re.compile(r"内容(?:是|为|写|：|:)?[\"“']?(.+?)[\"”']?$")
_OPEN_PATTERN = re.compile(r"(?:请)?(?:帮我)?(?:打开|启动|运行一下|运行)(?:一下)?(.+)")
_SEARCH_PATTERN = re.compile(r"(?:帮我)?(?:搜一下|搜索|搜|查一下|查询|查|找一下)(?:一下)?(.+)")
_CREATE_PATTERN = re.compile(r"(?:创建|新建|建立|建一个|建个)(?:一个|个)?(.+)")
_DIRECTORY_PATTERN = re.compile(r"在(桌面|文档|下载|desktop|documents|downloads)", re.IGNORECASE)


def _clean(text: str) -> str:
    return text.strip().strip("的了吧呢啊 ").strip("\"“”'")


def _split_segments(text: str) -> list[str]:
    """拆分多动作指令，并把“内容是……”分句合并回前面的创建文件分句。"""
    segments: list[str] = []
    for seg in _SPLIT_PATTERN.split(text):
        seg = seg.strip()
        if not seg:
            continue
        if (
            segments
            and re.match(r"内容(?:是|为|写|：|:)", seg)
            and _FILENAME_PATTERN.search(segments[-1])
        ):
            segments[-1] = f"{segments[-1]}，{seg}"
        else:
            segments.append(seg)
    return segments


def parse_local(text: str) -> list[dict]:
    """把中文指令解析为工具调用列表，每个元素形如 {"name": ..., "arguments": {...}}。"""
    calls: list[dict] = []
    for segment in _split_segments(text):

        # 1) 打开软件
        match = _OPEN_PATTERN.fullmatch(segment)
        if match and not _CREATE_PATTERN.fullmatch(segment):
            app_name = _clean(match.group(1))
            app_name = re.sub(r"(软件|程序|应用|应用程序)$", "", app_name).strip()
            if app_name:
                calls.append({"name": "open_app", "arguments": {"app_name": app_name}})
                continue

        # 2) 创建文件
        if _CREATE_PATTERN.search(segment) or _FILENAME_PATTERN.search(segment):
            file_match = _FILENAME_PATTERN.search(segment)
            if file_match:
                filename = file_match.group(0)
                content = ""
                content_match = _CONTENT_PATTERN.search(segment)
                if content_match:
                    content = _clean(content_match.group(1))
                args: dict = {"filename": filename, "content": content}
                dir_match = _DIRECTORY_PATTERN.search(segment)
                if dir_match:
                    args["directory"] = dir_match.group(1)
                calls.append({"name": "create_file", "arguments": args})
                continue

        # 3) 浏览器搜索
        match = _SEARCH_PATTERN.fullmatch(segment)
        if match:
            query = _clean(match.group(1))
            query = re.sub(r"^(一下|个)", "", query).strip()
            if query:
                calls.append({"name": "web_search", "arguments": {"query": query}})
                continue

    return calls


# ----------------------------------------------------------------------
# AI 代理
# ----------------------------------------------------------------------


class Assistant:
    def __init__(self, settings: Settings):
        self._settings = settings

    def handle(self, text: str) -> AgentResponse:
        text = (text or "").strip()
        if not text:
            return AgentResponse(reply="请输入你想让我做的事情")

        if self._settings.has_api_key:
            try:
                return self._handle_online(text)
            except Exception as exc:  # 网络或接口异常时回退本地模式
                local = self._run_local(text)
                local.reply = f"在线服务暂时不可用（{exc}），已改用本地规则。{local.reply}"
                local.mode = "local"
                return local
        return self._run_local(text)

    def _run_local(self, text: str) -> AgentResponse:
        calls = parse_local(text)
        results = [dispatch(c["name"], c["arguments"]) for c in calls]
        if not results:
            return AgentResponse(
                reply="我没听懂这条指令，可以试试：打开记事本 / 搜一下青岛天气 / 创建 todo.txt",
                mode="local",
            )
        summary = "；".join(r.message for r in results)
        return AgentResponse(reply=summary, results=results, mode="local")

    def _handle_online(self, text: str) -> AgentResponse:
        # 延迟导入，未配置 API Key 的用户无需安装 openai 也能跑本地模式
        from openai import OpenAI

        client = OpenAI(base_url=self._settings.base_url, api_key=self._settings.api_key)
        messages: list[dict] = [
            {"role": "system", "content": _SYSTEM_PROMPT},
            {"role": "user", "content": text},
        ]
        results: list[ToolResult] = []

        for _ in range(_MAX_TOOL_ROUNDS):
            response = client.chat.completions.create(
                model=self._settings.model,
                messages=messages,
                tools=TOOL_SPECS,
                tool_choice="auto",
                temperature=0.2,
            )
            message = response.choices[0].message
            messages.append(message.model_dump(exclude_none=True))

            if not message.tool_calls:
                return AgentResponse(
                    reply=message.content or "已完成",
                    results=results,
                    mode="online",
                )

            for tool_call in message.tool_calls:
                raw_args = tool_call.function.arguments or "{}"
                try:
                    arguments = json.loads(raw_args)
                except json.JSONDecodeError:
                    arguments = {}
                # 搜索类工具补充用户配置的搜索引擎
                if tool_call.function.name == "web_search":
                    arguments.setdefault("engine", self._settings.search_engine)
                result = dispatch(tool_call.function.name, arguments)
                results.append(result)
                messages.append(
                    {
                        "role": "tool",
                        "tool_call_id": tool_call.id,
                        "content": result.message,
                    }
                )

        return AgentResponse(reply="工具调用次数过多，已停止。", results=results, mode="online")

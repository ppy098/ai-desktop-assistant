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
    "创建文件、浏览器搜索、打开网址、截屏、读写剪贴板、查看电脑状态、优化内存。"
    "请优先调用提供的工具完成动作；一条指令包含多个动作时，"
    "一次性发起全部工具调用。工具执行完成后，用一句简短中文汇报结果，不要复述参数。"
)

# 防止工具调用来回嵌套的保护上限
_MAX_TOOL_ROUNDS = 5

# 本地模式下 "我没听懂" 的示例提示
_LOCAL_HINT = (
    "我没听懂这条指令，可以试试：打开记事本 / 搜一下青岛天气 / 打开 www.baidu.com / "
    "截屏 / 现在几点 / 看看剪贴板 / 电脑状态 / 优化内存 / 创建 todo.txt"
)


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

# ---- 新增能力的关键词规则 ----
_TIME_PATTERN = re.compile(r"(?:现在|当前)?(?:几点|几号|几日|星期几|礼拜几|时间|日期|今天星期)")
_SCREENSHOT_PATTERN = re.compile(r"(?:帮我)?(?:截屏|截图|屏幕截图|全屏截图|抓屏)")
_CLIPBOARD_READ_PATTERN = re.compile(
    r"剪贴板(?:里|中)?(?:的)?(?:是|有)?(?:什么|内容|文字)?|(?:看看|查看|读取|念一下)剪贴板"
)
_CLIPBOARD_WRITE_PATTERN = re.compile(
    r"^(?:帮我)?(?:复制|拷贝)(?:一下)?(?:这段|这些)?(?:文字|内容|文本)?[：:]?(.+)$"
)
_SYSTEM_PATTERN = re.compile(
    r"(?:电脑状态|系统状态|运行状态|多少内存|内存占用|内存使用|内存还剩|"
    r"磁盘空间|硬盘空间|电池|CPU占用|cpu占用|电脑卡不卡)"
)
_FOLDER_PATTERN = re.compile(r"^(?:帮我)?打开(桌面|文档|下载)(?:文件夹)?$")
_MEMORY_PATTERN = re.compile(
    r"(?:一键)?(?:优化|清理|释放|整理|腾出?)(?:一下)?(?:物理)?内存|"
    r"内存(?:优化|清理|释放|整理)|(?:清|清理|清空|释放)(?:一下)?内存|优化(?:一下)?内存"
)
_DISK_PATTERN = re.compile(
    r"(?:一键)?(?:清理|清扫|删除|清空)(?:一下)?(?:磁盘|硬盘|[Cc] ?盘|系统盘)(?:垃圾|空间|缓存)?|"
    r"(?:清理|清空)(?:系统|电脑)?(?:垃圾|垃圾文件|缓存文件|临时文件)"
)
_URL_PATTERN = re.compile(
    r"^(?:请)?(?:帮我)?(?:打开|访问|浏览|前往)\s*(?:一下)?\s*(?:网页|网址)?\s*[：:]?\s*"
    r"(https?://[^\s，,；;]+|www\.[^\s，,；;]+|"
    r"[A-Za-z0-9][A-Za-z0-9\-]*(?:\.[A-Za-z0-9\-]+)+(?:/[^\s，,；;]*)?)$"
)


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

        # 0) 时间
        if _TIME_PATTERN.search(segment):
            calls.append({"name": "get_time", "arguments": {}})
            continue

        # 0.5) 截屏
        if _SCREENSHOT_PATTERN.search(segment):
            calls.append({"name": "take_screenshot", "arguments": {}})
            continue

        # 0.6) 读取剪贴板
        if _CLIPBOARD_READ_PATTERN.search(segment) and not _CLIPBOARD_WRITE_PATTERN.match(segment):
            calls.append({"name": "get_clipboard", "arguments": {}})
            continue

        # 0.7) 复制到剪贴板
        clip_match = _CLIPBOARD_WRITE_PATTERN.match(segment)
        if clip_match:
            content = _clean(clip_match.group(1))
            if content:
                calls.append({"name": "set_clipboard", "arguments": {"text": content}})
                continue

        # 0.73) 一键清理磁盘（须先于“电脑状态”，否则“清理磁盘空间”会落到状态查询）
        if _DISK_PATTERN.search(segment):
            calls.append({"name": "clean_disk", "arguments": {}})
            continue

        # 0.75) 一键内存优化（须先于“电脑状态”，否则“优化内存”会落到状态查询）
        if _MEMORY_PATTERN.search(segment):
            calls.append({"name": "optimize_memory", "arguments": {}})
            continue

        # 0.8) 电脑状态
        if _SYSTEM_PATTERN.search(segment):
            calls.append({"name": "system_status", "arguments": {}})
            continue

        # 0.9) 打开常用文件夹
        folder_match = _FOLDER_PATTERN.match(segment)
        if folder_match:
            calls.append({"name": "open_folder", "arguments": {"name": folder_match.group(1)}})
            continue

        # 1) 打开网址（须先于“打开软件”，避免把域名当成应用名）
        url_match = _URL_PATTERN.match(segment)
        if url_match:
            calls.append({"name": "open_url", "arguments": {"url": url_match.group(1)}})
            continue

        # 2) 打开软件
        match = _OPEN_PATTERN.fullmatch(segment)
        if match and not _CREATE_PATTERN.fullmatch(segment):
            app_name = _clean(match.group(1))
            app_name = re.sub(r"(软件|程序|应用|应用程序)$", "", app_name).strip()
            if app_name:
                calls.append({"name": "open_app", "arguments": {"app_name": app_name}})
                continue

        # 3) 创建文件
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

        # 4) 浏览器搜索
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

        # 本地规则优先：命中关键词立即执行（毫秒级响应），不必等待大模型
        calls = parse_local(text)
        if calls:
            return self._run_local(text)

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
            return AgentResponse(reply=_LOCAL_HINT, mode="local")
        summary = "；".join(r.message for r in results)
        return AgentResponse(reply=summary, results=results, mode="local")

    def _handle_online(self, text: str) -> AgentResponse:
        # 延迟导入，未配置 API Key 的用户无需安装 openai 也能跑本地模式
        from openai import OpenAI

        client = OpenAI(
            base_url=self._settings.base_url,
            api_key=self._settings.api_key,
            timeout=120.0,
            max_retries=1,
        )
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

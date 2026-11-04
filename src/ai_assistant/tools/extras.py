"""杂项小工具：音量控制、锁屏、便签、算式计算、文本处理、显示桌面。

这些功能都不需要管理员权限，也不改动系统设置，纯本地执行。
"""

from __future__ import annotations

import ast
import base64
import ctypes
import datetime as _dt
import operator
import os
from pathlib import Path

from .base import ToolResult

_VK_VOLUME_MUTE = 0xAD
_VK_VOLUME_DOWN = 0xAE
_VK_VOLUME_UP = 0xAF
_VK_LWIN = 0x5B
_VK_D = 0x44
_KEYEVENTF_KEYUP = 0x0002

_NOTES_FILE = Path.home() / ".ai_desktop_assistant" / "notes.md"

_ALLOWED_BIN_OPS = {
    ast.Add: operator.add,
    ast.Sub: operator.sub,
    ast.Mult: operator.mul,
    ast.Div: operator.truediv,
    ast.FloorDiv: operator.floordiv,
    ast.Mod: operator.mod,
    ast.Pow: operator.pow,
}
_ALLOWED_UNARY_OPS = {ast.UAdd: operator.pos, ast.USub: operator.neg}


def _press_key(vk: int) -> None:
    user32 = ctypes.windll.user32
    user32.keybd_event(vk, 0, 0, 0)
    user32.keybd_event(vk, 0, _KEYEVENTF_KEYUP, 0)


def control_volume(action: str) -> ToolResult:
    """调节系统音量：静音/取消静音/加/减（模拟媒体键，无需管理员）。"""
    if os.name != "nt":
        return ToolResult(success=False, message="音量控制仅支持 Windows")

    text = (action or "").strip()
    if any(k in text for k in ("取消静音", "解除静音", "恢复声音", "开声音")):
        _press_key(_VK_VOLUME_MUTE)
        return ToolResult(success=True, message="已取消静音", data={"action": "unmute"})

    if "静音" in text:
        _press_key(_VK_VOLUME_MUTE)
        return ToolResult(success=True, message="已切换静音状态", data={"action": "mute"})

    steps = 1
    for digit in text:
        if digit.isdigit():
            steps = max(1, min(int(digit), 20))
            break

    if any(k in text for k in ("减", "小", "降低", "调低", "关小", "down")):
        for _ in range(steps):
            _press_key(_VK_VOLUME_DOWN)
        return ToolResult(
            success=True,
            message=f"音量降低 {steps} 格",
            data={"action": "down", "steps": steps},
        )

    for _ in range(steps):
        _press_key(_VK_VOLUME_UP)
    return ToolResult(
        success=True,
        message=f"音量提高 {steps} 格",
        data={"action": "up", "steps": steps},
    )


def lock_screen() -> ToolResult:
    """锁定当前屏幕（不退出登录，也不影响正在运行的程序）。"""
    if os.name != "nt":
        return ToolResult(success=False, message="锁屏仅支持 Windows")
    try:
        ok = ctypes.windll.user32.LockWorkStation()
    except OSError as exc:
        return ToolResult(success=False, message=f"锁屏失败：{exc}")
    if not ok:
        return ToolResult(success=False, message="锁屏失败：系统拒绝执行")
    return ToolResult(success=True, message="已锁屏，按任意键并输入密码即可回到桌面")


def quick_note(text: str = "", limit: int = 5) -> ToolResult:
    """写一条便签；不传内容则返回最近的几条便签。"""
    if not text.strip():
        try:
            if not _NOTES_FILE.exists():
                return ToolResult(success=True, message="便签还是空的，说“记一下 内容”就能记一条")
            lines = _NOTES_FILE.read_text(encoding="utf-8").splitlines()
        except OSError as exc:
            return ToolResult(success=False, message=f"读取便签失败：{exc}")
        recent = [line for line in lines if line.strip()][-limit:]
        if not recent:
            return ToolResult(success=True, message="便签还是空的")
        body = "\n".join(recent)
        return ToolResult(
            success=True,
            message=f"最近的 {len(recent)} 条便签：\n{body}",
            data={"notes": recent},
        )

    content = text.strip().replace("\r", "").replace("\n", " ")
    stamp = _dt.datetime.now().strftime("%Y-%m-%d %H:%M")
    try:
        _NOTES_FILE.parent.mkdir(parents=True, exist_ok=True)
        with _NOTES_FILE.open("a", encoding="utf-8") as handle:
            handle.write(f"- [{stamp}] {content}\n")
    except OSError as exc:
        return ToolResult(success=False, message=f"保存便签失败：{exc}")
    return ToolResult(
        success=True,
        message=f"已记下：{content}（共存在 {_NOTES_FILE}）",
        data={"text": content, "file": str(_NOTES_FILE)},
    )


def _eval_expr(node: ast.AST) -> float:
    if isinstance(node, ast.Expression):
        return _eval_expr(node.body)
    if isinstance(node, ast.Constant) and isinstance(node.value, (int, float)):
        return node.value
    if isinstance(node, ast.UnaryOp) and type(node.op) in _ALLOWED_UNARY_OPS:
        return _ALLOWED_UNARY_OPS[type(node.op)](_eval_expr(node.operand))
    if isinstance(node, ast.BinOp) and type(node.op) in _ALLOWED_BIN_OPS:
        left = _eval_expr(node.left)
        right = _eval_expr(node.right)
        if isinstance(node.op, ast.Pow) and abs(right) > 100:
            raise ValueError("指数太大")
        return _ALLOWED_BIN_OPS[type(node.op)](left, right)
    raise ValueError("只支持 + - * / // % ** 和括号")


def calculate(expression: str) -> ToolResult:
    """计算一个算式，例如 12*8、((3+5)/2)**2。"""
    raw = (expression or "").strip()
    if not raw:
        return ToolResult(success=False, message="请给出要计算的算式")
    normalized = (
        raw.replace("×", "*")
        .replace("÷", "/")
        .replace("（", "(")
        .replace("）", ")")
        .replace("^", "**")
        .replace("＝", "=")
        .replace("=?", "")
        .replace("=", "")
        .replace("？", "")
        .strip()
    )
    try:
        tree = ast.parse(normalized, mode="eval")
        value = _eval_expr(tree)
    except (SyntaxError, ValueError, ZeroDivisionError, OverflowError) as exc:
        return ToolResult(success=False, message=f"算不出来：{exc}")

    if isinstance(value, float) and value.is_integer():
        text = str(int(value))
    else:
        text = f"{value:.10g}"
    return ToolResult(
        success=True,
        message=f"{raw.rstrip('=?？')} = {text}",
        data={"expression": raw, "result": text},
    )


def text_tool(text: str, action: str = "count") -> ToolResult:
    """文本处理：字数统计、转大写、转小写、Base64 编码/解码。"""
    body = "" if text is None else str(text)
    act = (action or "count").strip().lower()

    if act in ("count", "字数", "统计", "stats"):
        chars = len(body)
        chars_no_space = len("".join(body.split()))
        words = len([w for w in body.replace("\n", " ").split(" ") if w.strip()])
        return ToolResult(
            success=True,
            message=f"共 {chars} 个字符（不含空白 {chars_no_space}，按空格分词 {words} 个）",
            data={"chars": chars, "chars_no_space": chars_no_space, "words": words},
        )

    if act in ("upper", "大写"):
        out = body.upper()
        return ToolResult(success=True, message=out, data={"text": out})

    if act in ("lower", "小写"):
        out = body.lower()
        return ToolResult(success=True, message=out, data={"text": out})

    if act in ("b64encode", "base64编码", "encode"):
        try:
            out = base64.b64encode(body.encode("utf-8")).decode("ascii")
        except (UnicodeEncodeError, ValueError) as exc:
            return ToolResult(success=False, message=f"编码失败：{exc}")
        return ToolResult(success=True, message=out, data={"text": out})

    if act in ("b64decode", "base64解码", "decode"):
        try:
            out = base64.b64decode(body.encode("ascii"), validate=False).decode("utf-8")
        except (UnicodeDecodeError, UnicodeEncodeError, ValueError) as exc:
            return ToolResult(success=False, message=f"解码失败：{exc}")
        return ToolResult(success=True, message=out, data={"text": out})

    return ToolResult(success=False, message=f"不认识的文本操作：{action}")


def show_desktop() -> ToolResult:
    """最小化所有窗口，露出桌面（等同 Win+D）。"""
    if os.name != "nt":
        return ToolResult(success=False, message="显示桌面仅支持 Windows")
    user32 = ctypes.windll.user32
    user32.keybd_event(_VK_LWIN, 0, 0, 0)
    user32.keybd_event(_VK_D, 0, 0, 0)
    user32.keybd_event(_VK_D, 0, _KEYEVENTF_KEYUP, 0)
    user32.keybd_event(_VK_LWIN, 0, _KEYEVENTF_KEYUP, 0)
    return ToolResult(success=True, message="已最小化所有窗口（再按一次可恢复）")

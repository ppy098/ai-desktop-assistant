"""配置加载与保存。

读取优先级：settings.json（软件内保存）> .env（手动配置）> 环境变量 > 默认值。
settings.json 保存在程序根目录（源码运行时为项目根目录，打包后为 exe 所在目录）。
"""

from __future__ import annotations

import json
import os
import sys
from dataclasses import dataclass, asdict
from pathlib import Path

from dotenv import load_dotenv

from ..ui.themes import DEFAULT_THEME

_SETTINGS_FILE = "settings.json"


def _project_root() -> Path:
    # PyInstaller 打包后 __file__ 位于 _internal 内，改为读 exe 所在目录
    if getattr(sys, "frozen", False):
        return Path(sys.executable).resolve().parent
    # 源码运行：当前文件 src/ai_assistant/core/config.py，向上三级即项目根目录
    return Path(__file__).resolve().parents[3]


@dataclass
class Settings:
    base_url: str
    api_key: str
    model: str
    search_engine: str
    theme: str = DEFAULT_THEME

    @property
    def has_api_key(self) -> bool:
        return bool(self.api_key) and not self.api_key.startswith("sk-在这里")


def load_settings() -> Settings:
    """加载配置：settings.json 优先，其次 .env，最后默认值。"""
    root = _project_root()

    # 1) settings.json
    json_path = root / _SETTINGS_FILE
    if json_path.exists():
        try:
            data = json.loads(json_path.read_text(encoding="utf-8"))
            return Settings(
                base_url=str(data.get("base_url", "")).strip()
                or os.environ.get("AI_BASE_URL", "https://ark.cn-beijing.volces.com/api/v3"),
                api_key=str(data.get("api_key", "")).strip(),
                model=str(data.get("model", "")).strip()
                or os.environ.get("AI_MODEL", "doubao-seed-1-6-250615"),
                search_engine=str(data.get("search_engine", "")).strip()
                or os.environ.get("SEARCH_ENGINE", "bing").strip().lower(),
                theme=str(data.get("theme", DEFAULT_THEME)).strip() or DEFAULT_THEME,
            )
        except (json.JSONDecodeError, OSError):
            pass  # 配置文件损坏时回退到 .env / 默认

    # 2) .env（兼容旧的手动配置方式）
    load_dotenv(root / ".env")
    return Settings(
        base_url=os.environ.get("AI_BASE_URL", "https://ark.cn-beijing.volces.com/api/v3"),
        api_key=os.environ.get("AI_API_KEY", "").strip(),
        model=os.environ.get("AI_MODEL", "doubao-seed-1-6-250615"),
        search_engine=os.environ.get("SEARCH_ENGINE", "bing").strip().lower(),
        theme=DEFAULT_THEME,
    )


def save_settings(settings: Settings) -> None:
    """把设置写入程序根目录的 settings.json。"""
    path = _project_root() / _SETTINGS_FILE
    path.write_text(
        json.dumps(asdict(settings), ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

"""配置加载：优先读取 .env（源码运行时在项目根目录，打包后在 exe 旁），其次读取系统环境变量。"""

from __future__ import annotations

import os
import sys
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv


def _project_root() -> Path:
    # PyInstaller 打包后 __file__ 位于 _internal 内，改为读 exe 所在目录
    if getattr(sys, "frozen", False):
        return Path(sys.executable).resolve().parent
    # 源码运行：当前文件 src/ai_assistant/core/config.py，向上三级即项目根目录
    return Path(__file__).resolve().parents[3]


@dataclass(frozen=True)
class Settings:
    base_url: str
    api_key: str
    model: str
    search_engine: str

    @property
    def has_api_key(self) -> bool:
        return bool(self.api_key) and not self.api_key.startswith("sk-在这里")


def load_settings() -> Settings:
    """加载配置；.env 不存在时使用默认值，程序仍可在本地模式运行。"""
    load_dotenv(_project_root() / ".env")
    return Settings(
        base_url=os.environ.get("AI_BASE_URL", "https://api.deepseek.com/v1"),
        api_key=os.environ.get("AI_API_KEY", "").strip(),
        model=os.environ.get("AI_MODEL", "deepseek-chat"),
        search_engine=os.environ.get("SEARCH_ENGINE", "bing").strip().lower(),
    )

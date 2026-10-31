# 架构设计

## 分层结构

```
用户输入
   │
   ▼
ui/main_window.py        图形界面，负责展示与输入；AI 调用放在 QThread 中避免卡顿
   │
   ▼
core/agent.py            Assistant：选择在线/本地模式，把指令转换为工具调用
   │
   ├── core/config.py    从 .env / 环境变量加载 Settings
   │
   ▼
tools/                   无状态工具层，统一返回 ToolResult
   ├── launcher.py       打开应用（内置别名 + 开始菜单快捷方式扫描）
   ├── files.py          创建文本文件（限制在用户主目录内）
   └── web.py            浏览器搜索（默认浏览器 + 搜索引擎 URL）
```

## 两种工作模式

| 模式 | 触发条件 | 指令解析方式 |
| --- | --- | --- |
| online | `.env` 中配置了有效 API Key | 大模型 function-calling，模型返回工具名与参数，程序执行后把结果回传模型生成总结 |
| local | 未配置 Key，或在线调用异常 | `parse_local()` 用正则规则识别“打开/搜索/创建”三类指令 |

在线模式下工具调用循环设有 `_MAX_TOOL_ROUNDS` 上限，防止模型反复调用造成死循环。

## 工具注册机制

- `tools/__init__.py` 中的 `TOOL_SPECS` 是 OpenAI 兼容的函数 Schema，同时作为工具清单的唯一来源；
- `TOOL_HANDLERS` 维护工具名到 Python 函数的映射；
- 新增工具只需：编写函数 → 在两个表中登记，界面与 agent 无需改动。

## 安全边界

- 文件创建只允许在 `%USERPROFILE%` 之下，且文件名不允许包含路径分隔符；
- API Key 仅从本地 `.env` 读取，`.env` 被 `.gitignore` 排除；
- 工具层捕获全部异常并以 `ToolResult` 返回，避免异常穿透到界面线程。

## 后续扩展方向

1. 工具层增加窗口管理、截屏、剪贴板等能力；
2. 界面增加系统托盘、全局快捷键、流式输出；
3. 抽象 AI Provider 接口，增加 Ollama 本地模型支持；
4. 引入插件发现机制，支持第三方通过 entry points 注册工具。

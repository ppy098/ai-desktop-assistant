# AI Desktop Assistant（AI 桌面助手）

一个运行在 Windows 上的开源桌面助手：用一句自然语言，让 AI 帮你**打开软件、创建文件、在浏览器中搜索**。

> 示例对话
> “打开记事本” → 自动启动记事本
> “在桌面上创建一个叫 todo.txt 的文件，内容写：买牛奶” → 自动创建文件
> “帮我搜一下青岛今天的天气” → 自动打开浏览器搜索
> “打开计算器，再搜一下 C++ 教程” → 一条指令可执行多个动作

## 功能特性



* 自然语言指令，基于在线大模型（OpenAI 兼容接口，支持豆包 / DeepSeek / OpenAI 等）

* 内置三类工具：启动应用程序、创建文本文件、浏览器搜索

* **未配置 API Key 时自动切换为本地规则模式**，不联网也能体验基础功能

* **右下角悬浮球常驻**：单击从球后面展开对话面板（非独立窗口），可拖动，系统托盘双入口

* **软件内「设置」界面**：API Key / 接口地址 / 模型 / 搜索引擎直接填写保存，支持一键「测试连接」，无需手动编辑配置文件

* **5 套个性化皮肤**：浅色、深色、薄荷、海洋、日落，切换即时生效

* 基于 PySide6 的图形界面，纯 Python，结构清晰，适合二次开发

* 密钥保存在本机 `settings.json`（或 `.env`），不会被提交到仓库

## 快速开始

### 1. 环境要求



* Windows 10 / 11（64 位）

* Python 3.10 及以上（开发环境使用 3.13）

### 2. 获取代码并安装依赖



```
git clone https://github.com/你的用户名/ai-desktop-assistant.git
cd ai-desktop-assistant
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

### 3. 配置 AI（可选）

**推荐方式：在软件内配置。** 启动程序后，右键悬浮球（或托盘图标）→ 设置，填入：

* **API Key**：豆包（火山方舟）为 32 位，在火山引擎方舟控制台申请
* **接口地址**：豆包默认 `https://ark.cn-beijing.volces.com/api/v3`
* **模型**：如 `doubao-seed-1-6-250615` 或推理接入点 `ep-xxx`
* 点「测试连接」验证通过后点「保存」，配置写入本机 `settings.json`

也可以手动复制 `.env.example` 为 `.env` 后编辑（仅在 `settings.json` 不存在时生效）：

```
Copy-Item .env.example .env
notepad .env
```

不配置也可以运行，程序会使用本地关键词规则处理指令。

### 4. 启动



```
python -m ai_assistant
```

或直接运行 `scripts\run.ps1`。

## 使用示例



| 你说的话                  | 执行的动作     |
| --------------------- | --------- |
| 打开记事本 / 打开计算器         | 启动对应程序    |
| 搜一下 “青岛天气”            | 浏览器打开搜索引擎 |
| 在桌面创建 hello.txt，内容是你好 | 创建文本文件    |

## 项目结构



```
ai-desktop-assistant/
├── src/ai_assistant/
│   ├── main.py              # 程序入口
│   ├── core/                # 配置加载、AI 代理（指令解析与工具调度）
│   ├── tools/               # 工具：打开软件、创建文件、浏览器搜索
│   └── ui/                  # PySide6 图形界面
├── tests/                   # 单元测试
├── docs/                    # 设计文档
├── scripts/                 # 辅助运行脚本
├── .env.example             # 密钥配置模板
├── requirements.txt
├── pyproject.toml
└── LICENSE
```

详细设计见 [docs/architecture.md](docs/architecture.md)。

## 开发与测试



```
# 运行单元测试
pytest -v
```

## 安全说明



* 本程序可以在你的电脑上启动程序和创建文件，请勿在不可信的自动化环境中授予其权限。

* 文件创建默认只允许在当前用户目录下，避免误操作系统目录。

* API Key 属于敏感信息：保存在本机 `settings.json`（或 `.env`），两者均已通过 `.gitignore` 排除，不会提交到 GitHub，请勿把 Key 分享给他人。

## 路线图



* [x] 系统托盘常驻、右下角悬浮球、从球后面展开面板

* [x] 软件内 API Key 设置界面与个性化皮肤

* [ ] 更多工具：删除 / 移动文件、窗口管理、截屏

* [ ] 流式输出与多轮对话

* [ ] 插件机制，支持自定义工具

* [ ] 支持本地大模型（Ollama）

## 贡献

欢迎提交 Issue 和 Pull Request。提交代码前请确保 `pytest` 通过，并保持现有代码风格。

## 许可证

[MIT](LICENSE)
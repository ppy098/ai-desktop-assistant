# 一键运行脚本：自动准备虚拟环境、安装依赖并启动程序
# 用法：在项目根目录执行  .\scripts\run.ps1

$ErrorActionPreference = "Stop"
$root = Split-Path -Parent $PSScriptRoot
Set-Location $root

if (-not (Test-Path ".venv")) {
    Write-Host "首次运行，正在创建虚拟环境..." -ForegroundColor Cyan
    python -m venv .venv
}

.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
python -m ai_assistant

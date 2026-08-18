$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent (Split-Path -Parent $MyInvocation.MyCommand.Path)
Set-Location $Root
if (-not (Get-Command py -ErrorAction SilentlyContinue)) { throw "Python 3.12以上が必要です。" }
py -3.12 -m venv .venv
& .\.venv\Scripts\python.exe -m pip install --upgrade pip
& .\.venv\Scripts\python.exe -m pip install -e ".[documents]"
if (-not (Test-Path "config\minidora.toml")) { Copy-Item "config\minidora.toml.example" "config\minidora.toml" }
& .\.venv\Scripts\minidora.exe doctor
Write-Host "導入完了。scripts\start_windows.ps1 で起動できます。"

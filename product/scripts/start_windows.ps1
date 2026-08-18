$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent (Split-Path -Parent $MyInvocation.MyCommand.Path)
Set-Location $Root
if (-not (Test-Path ".venv\Scripts\minidora.exe")) { & "$Root\scripts\install_windows.ps1" }
& .\.venv\Scripts\minidora.exe serve @args

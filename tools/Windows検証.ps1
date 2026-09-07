#requires -Version 7.0
[CmdletBinding()]
param()

$ErrorActionPreference = 'Stop'
if (-not $IsWindows) { throw 'WindowsのPowerShell 7で実行してください。' }

$根 = Split-Path -Parent $PSScriptRoot
$Python = Join-Path $根 '.venv-win/Scripts/python.exe'
if (-not (Test-Path -LiteralPath $Python -PathType Leaf)) {
    throw '先に tools/Windows開発環境.ps1 を実行してください。'
}

function Python検証 {
    param([string]$名前, [string[]]$引数)
    Write-Host "検証: $名前"
    & $Python @引数
    if ($LASTEXITCODE -ne 0) { throw "$名前 に失敗しました。終了コード: $LASTEXITCODE" }
}

$元のUTF8 = $env:PYTHONUTF8
Push-Location -LiteralPath $根
try {
    $env:PYTHONUTF8 = '1'
    Python検証 '依存関係' @('-m', 'pip', 'check')
    Python検証 'リポジトリ整合性監査' @('tools/repository_consistency_check.py')
    Python検証 '日本語基底監査' @('tools/日本語基底監査.py')
    Python検証 '構文確認' @('-m', 'compileall', '-q', 'src', 'tests', 'tools')
    Python検証 '単体試験' @('-m', 'unittest', 'discover', '-s', 'tests', '-v')
    Python検証 '規模測定の回帰' @('tools/規模測定.py')
    Python検証 'module CLI' @('-m', 'minidora', '2+3')
    Write-Host '検証: console script'
    & (Join-Path $根 '.venv-win/Scripts/minidora.exe') '2+3'
    if ($LASTEXITCODE -ne 0) { throw 'console scriptの実行に失敗しました。' }
    Write-Host 'Windowsローカル検証: 合格'
} finally {
    $env:PYTHONUTF8 = $元のUTF8
    Pop-Location
}

#requires -Version 7.0
[CmdletBinding()]
param(
    [ValidatePattern('^3\.(11|12|13|14)$')]
    [string]$Python版 = '3.13'
)

$ErrorActionPreference = 'Stop'
if (-not $IsWindows) { throw 'WindowsのPowerShell 7で実行してください。' }

$根 = Split-Path -Parent $PSScriptRoot
$環境 = Join-Path $根 '.venv-win'
$Python = Join-Path $環境 'Scripts/python.exe'
$元のUTF8 = $env:PYTHONUTF8
Push-Location -LiteralPath $根
try {
    $env:PYTHONUTF8 = '1'
    if (Test-Path -LiteralPath $環境) {
        if (-not (Test-Path -LiteralPath $Python -PathType Leaf)) {
            throw '.venv-win がWindows用仮想環境ではありません。既存内容を確認してください。'
        }
    } else {
        & py "-$Python版" -m venv $環境
        if ($LASTEXITCODE -ne 0) { throw 'Windows用仮想環境の作成に失敗しました。py --list-paths でPythonを確認してください。' }
    }

    & $Python -c "import sys; from pathlib import Path; assert sys.platform == 'win32'; assert sys.prefix != sys.base_prefix; assert Path(sys.prefix).resolve() == Path(sys.argv[1]).resolve(); assert '.'.join(map(str, sys.version_info[:2])) == sys.argv[2], 'Python版が一致しません'; print(sys.version); print(sys.executable)" $環境 $Python版
    if ($LASTEXITCODE -ne 0) { throw '仮想環境の場所・OS・Python版が要求と一致しません。既存環境は自動削除しません。' }

    & $Python -m pip install -e .
    if ($LASTEXITCODE -ne 0) { throw 'MINIDORAの編集可能インストールに失敗しました。' }
    & $Python -m pip check
    if ($LASTEXITCODE -ne 0) { throw 'Python依存関係の検証に失敗しました。' }

    & git config --local core.autocrlf input
    if ($LASTEXITCODE -ne 0) { throw 'リポジトリ内のGit改行設定に失敗しました。' }
    & git config --local core.longpaths true
    if ($LASTEXITCODE -ne 0) { throw 'リポジトリ内のGit長いパス設定に失敗しました。' }

    Write-Host 'Windows開発環境の準備が完了しました。'
    Write-Host '検証: pwsh -NoProfile -File .\tools\Windows検証.ps1'
    Write-Host '実行: .\.venv-win\Scripts\python.exe -X utf8 -m minidora "2+3"'
} finally {
    $env:PYTHONUTF8 = $元のUTF8
    Pop-Location
}

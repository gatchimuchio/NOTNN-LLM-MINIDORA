# Windowsネイティブ開発環境

現行の開発用補助手順。日本語正本であり、[AGENTS.md](../AGENTS.md) の検証手順と [日本語基底規定](../設計/00_日本語基底規定_v1.md) をWindowsで実行するための環境を扱う。模型・能力・評価の仕様は変更しない。

## 前提と初回準備

Windows版Python 3.13、Python Launcher (`py`)、PowerShell 7 (`pwsh`)、Git for Windowsを使う。通常の開発・単体試験にはGPU、WSL、Docker、追加の実行時Python依存は不要。

リポジトリ直下で実行する。

```powershell
pwsh -NoProfile -File .\tools\Windows開発環境.ps1
```

`.venv-win` を作り、`pip install -e .` でこのチェックアウトを導入する。既存の `.venv` は保持する。準備にはビルド依存を取得するネットワーク接続が必要になる場合がある。導入済みの別の対応版を指定する場合は `-Python版 3.12` などを付ける。既存環境の版が異なる場合は停止し、自動削除・置換はしない。

準備時に、このリポジトリのGit設定だけ `core.autocrlf=input` と `core.longpaths=true` にする。作業ファイルを一括変換せず、グローバル設定とWindowsの保護設定は変更しない。

## 日常の実行と検証

有効化なしでも、Windows用Pythonを直接指定して実行できる。

```powershell
.\.venv-win\Scripts\python.exe -X utf8 -m minidora "2+3"
pwsh -NoProfile -File .\tools\Windows検証.ps1
```

検証スクリプトは依存整合性、リポジトリ整合性、日本語基底、構文、全単体試験、規模測定の回帰、module CLI、console scriptを順に実行し、失敗時には非ゼロで終了する。GPQA全数測定や外部サービスの設定は含まない。ローカル合格を全OS・Python版のCI合格や製品完成の証拠とは扱わない。

通常の `python` / `minidora` コマンドを使う場合は、新しいPowerShellごとに次を実行する。

```powershell
. .\.venv-win\Scripts\Activate.ps1
$env:PYTHONUTF8 = '1'
python -m minidora "2+3"
```

`py` は仮想環境を作るときに使い、日常は `.venv-win` のPythonを使う。準備・検証スクリプトは子プロセスもUTF-8で動かし、終了時に呼出元の `PYTHONUTF8` を元に戻す。

## VS Code

リポジトリのフォルダーを開く。`.vscode` にWindows用Python、PowerShell、UTF-8/LF、unittest検出、準備・検証タスク、F5のCLIデバッグを設定している。MicrosoftのPython / Python Debugger拡張を使う。

すでに別のPythonを選択しているウィンドウでは、`Python: Select Interpreter` から `.venv-win\Scripts\python.exe` を選び直す。保存済みの選択は `python.defaultInterpreterPath` より優先される。テスト画面は単体試験用であり、監査を含む一式は `MINIDORA: Windows検証` タスクで実行する。

## 配置と再作成

OneDriveのドキュメント等がWindows Defenderの「フォルダー アクセスの制御」で保護されていると、Python・Git・エディターによる書き込みが拒否される場合がある。その場合は、保護設定を維持したまま通常の開発用フォルダーにコピーして作業する。元のチェックアウトと未コミット差分を保持し、新しいチェックアウトにも差分が揃っていることを確認する。

仮想環境はOS・配置に依存するため、WSL用環境や別の場所の環境を流用しない。リポジトリを別の場所に置いた場合は、その場所でWindows環境を作り直す。`.venv-win` はGitに含めない。

参照: [Python venv公式文書](https://docs.python.org/3.13/library/venv.html)、[Python UTF-8設定](https://docs.python.org/3.13/using/cmdline.html#envvar-PYTHONUTF8)、[VS Code Python設定](https://code.visualstudio.com/docs/python/settings-reference)。

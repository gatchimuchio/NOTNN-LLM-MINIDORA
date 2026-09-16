"""旧一括置換入口を、ファイルを書き換えない完了監査へ切り替える。

退役した置換器は docs/履歴_日本語基底正規化/ にテキストとして保存する。
この入口は正規化を再適用せず、現在の監査結果を返すだけである。
"""
from __future__ import annotations
from pathlib import Path
import subprocess
import sys


def main() -> int:
    根 = Path(__file__).resolve().parents[1]
    終了値 = 0
    for 名前 in ("日本語基底監査.py", "日本語基底詳細監査.py", "リポジトリ整合性監査.py"):
        結果 = subprocess.run([sys.executable, str(根 / "tools" / 名前)], cwd=根, check=False)
        if 結果.returncode != 0:
            終了値 = 1
    return 終了値


if __name__ == "__main__":
    raise SystemExit(main())

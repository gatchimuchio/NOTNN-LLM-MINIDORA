# -*- coding: utf-8 -*-
"""旧日本語基底正規化入口の読み取り専用互換実装。

自動置換・自動修正は行わず、現行の三監査を順に実行して採否だけを集約する。
"""
from __future__ import annotations

from pathlib import Path
import subprocess
import sys


根 = Path(__file__).resolve().parent
監査群 = (
    "日本語基底監査.py",
    "日本語基底詳細監査.py",
    "リポジトリ整合性監査.py",
)


def main() -> int:
    結果群 = []
    for 名前 in 監査群:
        結果群.append(subprocess.run([sys.executable, str(根 / 名前)]).returncode)
    return 0 if all(値 == 0 for 値 in 結果群) else 1


if __name__ == "__main__":
    raise SystemExit(main())

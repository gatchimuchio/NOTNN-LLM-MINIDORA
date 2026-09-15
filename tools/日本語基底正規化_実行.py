# -*- coding: utf-8 -*-
"""PR #115 専用の一時正規化実行器。workflow群は接続権限のある別経路で扱う。"""
from __future__ import annotations

from pathlib import Path
import runpy


対象 = Path(__file__).with_name("日本語基底正規化_一時.py")
本文 = 対象.read_text(encoding="utf-8")
開始 = 本文.index("def _互換ツール本文")
終了 = 本文.index("\ndef _移送", 開始)
修正版 = '''def _互換ツール本文(正本名: str) -> str:
    return (
        f'"""旧英字名の互換入口。現行日本語正本は `{正本名}`。"""\\n'
        'from pathlib import Path\\n'
        'import runpy\\n\\n'
        f'_正本経路 = Path(__file__).with_name("{正本名}")\\n'
        '_名前空間 = runpy.run_path(str(_正本経路), run_name="_minidora_互換")\\n'
        'for _名, _値 in _名前空間.items():\\n'
        '    if not _名.startswith("__"):\\n'
        '        globals()[_名] = _値\\n'
    )
'''
本文 = 本文[:開始] + 修正版 + 本文[終了:]
本文 = 本文.replace(
    "    _ワークフロー名を日本語化()\n",
    "    # workflow 改名は GitHub 接続権限のある別経路で適用する。\n",
)
本文 = 本文.replace(
    '        相対 = 対象.relative_to(根).as_posix()\n        if 相対.startswith(除外先頭):',
    '        相対 = 対象.relative_to(根).as_posix()\n        if 相対.startswith(".github/workflows/"):\n            continue\n        if 相対.startswith(除外先頭):',
)
対象.write_text(本文, encoding="utf-8")
runpy.run_path(str(対象), run_name="__main__")

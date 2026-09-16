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
本文 = 本文.replace(
    '        if not 対象.is_file() or 対象.resolve() == 自己 or 対象.suffix.lower() not in 対象拡張子:\n            continue',
    '        if not 対象.is_file() or 対象.resolve() == 自己 or 対象.suffix.lower() not in 対象拡張子:\n            continue\n        if 対象.name in {"日本語基底監査.py", "日本語基底詳細監査.py", "日本語基底正規化_実行.py", "日本語基底正規化_仕上げ.py"}:\n            continue',
)
対象.write_text(本文, encoding="utf-8")
名前空間 = runpy.run_path(str(対象), run_name="_日本語基底正規化")
正規化 = 名前空間.get("main")
if not callable(正規化):
    raise RuntimeError("日本語基底正規化器のmainを取得できない")
if 正規化() != 0:
    raise RuntimeError("日本語基底正規化器が失敗した")

# 過去の一括正規化で監査器自身の「検出対象語」まで日本語化された箇所を正す。
根 = Path(__file__).resolve().parents[1]
監査対象 = 根 / "tools/日本語基底監査.py"
監査本文 = 監査対象.read_text(encoding="utf-8")
監査本文 = 監査本文.replace("pipeline|実行系|gate", "pipeline|runtime|gate")
状態開始 = 監査本文.index("_旧状態値 = {")
状態終了 = 監査本文.index("\n}\n\n\ndef _日本語を含む", 状態開始) + 2
旧状態定義 = '''_旧状態値 = {
    "PROVISIONAL_BY_DEFAULT",
    "CLOSED_FOR_OPERATION",
    "STRUCTURED_PUBLIC_PROJECTION",
    "FULL_FIELD_ACTIVE",
    "PARTIALLY_ARTICULATED",
    "MEANING_PRESERVED",
    "UNFORMED",
    "SHADOW",
    "PATTERN",
    "MECHANISM_CANDIDATE",
    "PRINCIPLE_CANDIDATE",
    "STANDARD_RELATIONS",
    "FORMED_RELATIONS",
    "PRIMARY_CAPABILITY_ACTIONS",
}'''
監査本文 = 監査本文[:状態開始] + 旧状態定義 + 監査本文[状態終了:]
監査対象.write_text(監査本文, encoding="utf-8")

詳細対象 = 根 / "tools/日本語基底詳細監査.py"
if 詳細対象.exists():
    詳細本文 = 詳細対象.read_text(encoding="utf-8")
    詳細本文 = 詳細本文.replace('"実行系", "gate"', '"runtime", "gate"')
    詳細対象.write_text(詳細本文, encoding="utf-8")

# 途中版の日本語化で生じた「日本語正本語 + 旧英語サフィックス」を全treeで解消する。
混成名置換 = {
    "HDS構文化器_action_delta": "HDS構文化作用差分",
    "HDS構文化器_audit_ir": "HDS構文化監査中間表現",
    "HDS構文化器_dynamics": "HDS構文化動態",
    "HDS構文化失敗集": "HDS構文化失敗集",
    "HDS構文化失敗": "HDS構文化失敗",
    "HDS構文化器_frontend": "HDS構文化前処理",
    "HDS構文化器_history": "HDS構文化履歴",
    "HDS構文化器_pipeline_v1_4": "HDS構文化処理系列_v1_4",
    "HDS構文化器_pipeline_v1_3": "HDS構文化処理系列_v1_3",
    "HDS構文化記録_v1_3": "HDS構文化記録_v1_3",
    "HDS構文化記録_v1_2": "HDS構文化記録_v1_2",
    "HDS構文化記録_v1_1": "HDS構文化記録_v1_1",
    "HDS構文化記録": "HDS構文化記録",
    "HDS構文化器_tacit": "HDS構文化暗黙知",
}
変更数 = 0
for 経路 in (根 / "src").rglob("*.py"):
    内容 = 経路.read_text(encoding="utf-8")
    新内容 = 内容
    for 旧名, 新名 in 混成名置換.items():
        新内容 = 新内容.replace(旧名, 新名)
    if 新内容 != 内容:
        経路.write_text(新内容, encoding="utf-8")
        変更数 += 1

確認対象 = 根 / "src/minidora/HDS構文化器_v1.py"
確認本文 = 確認対象.read_text(encoding="utf-8")
残存 = [旧名 for 旧名 in 混成名置換 if 旧名 in 確認本文]
if 残存:
    raise RuntimeError("混成import名の補正漏れ: " + ", ".join(残存))
print(f"混成import補正: {変更数}ファイル")

# 詳細監査で残る自己定義識別子・内部鍵・混成パスをAST基準で仕上げる。
仕上げ対象 = Path(__file__).with_name("日本語基底正規化_仕上げ.py")
仕上げ空間 = runpy.run_path(str(仕上げ対象), run_name="_日本語基底仕上げ")
仕上げ = 仕上げ空間.get("main")
if not callable(仕上げ):
    raise RuntimeError("日本語基底仕上げ正規化器のmainを取得できない")
if 仕上げ() != 0:
    raise RuntimeError("日本語基底仕上げ正規化器が失敗した")

from __future__ import annotations

import unittest

from minidora.HDSコア入力 import HDSコア入力束, HDSコア目的, HDSコア表現制約
from minidora.HDS実行主体 import (
    HDS作用供給器,
    HDS作用結果,
    HDS作用状態,
    HDS終端,
    HDS関数作用,
)
from minidora.HDS駆動コア import HDS継承基準版, HDS駆動コア


class _コア入力構文化器:
    def コア入力コンパイル(self, 問合せ, **kwargs):
        return HDSコア入力束(
            原文=問合せ,
            認知世界ID="正本継承試験",
            意味項目=(),
            関係=(),
            条件=(),
            目的=(HDSコア目的("目的:1", "依頼", "完了"),),
            作用要求=(),
            要求成果=(),
            残差=(),
            検証要求=(),
            実行制約=(),
            表現制約=HDSコア表現制約("ja"),
        )


def _完了作用():
    return HDS関数作用(
        "継承試験/完了",
        lambda 状態: HDS作用結果(
            HDS作用状態.成立,
            追加状態=frozenset({"完了"}),
            理由=("正本継承試験",),
        ),
        出力状態=("完了",),
    )


class HDS正本継承試験(unittest.TestCase):
    def test_継承基準は再設計直前HDSミニドラ正本を固定する(self):
        self.assertEqual(HDS継承基準版, "HDS-MINIDORA-1194452a")

    def test_コア正本入力と旧動的作用供給を同じ通常循環で使える(self):
        コア = HDS駆動コア(
            HDSコンパイラ=_コア入力構文化器(),
            作用供給器=(HDS作用供給器("供給", lambda 状態: (_完了作用(),)),),
        )
        結果 = コア.実行("完了させる", 要求状態=("完了",))
        self.assertEqual(結果.終端, HDS終端.採用)
        self.assertIn("HDSコア入力済み", 結果.状態.成立状態)
        self.assertIn("HDSコア入力", 結果.状態.成果辞書())
        self.assertTrue(any(行.作用ID == "継承試験/完了" for 行 in 結果.履歴))

    def test_旧基準が承認済みなら新拡張を起動せず完全保持する(self):
        基準 = object()
        呼出 = []
        判定 = HDS駆動コア().非退行継承実行(
            "入力",
            基準実行=lambda: 基準,
            基準承認判定=lambda 値: 値 is 基準,
            拡張実行=lambda: 呼出.append("拡張"),
            拡張承認判定=lambda 値: True,
            拡張採用証明=lambda 旧, 新: True,
        )
        self.assertIs(判定.出力, 基準)
        self.assertTrue(判定.基準固定)
        self.assertFalse(判定.拡張採用)
        self.assertEqual(呼出, [])

    def test_旧基準が未承認なら旧HDS実行系も同じ非退行契約で継承できる(self):
        基準 = {"状態": "SUSPEND"}
        拡張 = {"状態": "APPROVE", "回答": "A"}
        判定 = HDS駆動コア().非退行継承実行(
            "入力",
            基準実行=lambda: 基準,
            基準承認判定=lambda 値: 値["状態"] == "APPROVE",
            拡張実行=lambda: 拡張,
            拡張承認判定=lambda 値: 値["状態"] == "APPROVE",
            拡張採用証明=lambda 旧, 新: 旧["状態"] != "APPROVE" and 新["状態"] == "APPROVE",
        )
        self.assertIs(判定.出力, 拡張)
        self.assertTrue(判定.拡張採用)

    def test_追加採用証明がなければ旧基準を保持する(self):
        基準 = {"状態": "SUSPEND"}
        拡張 = {"状態": "APPROVE", "回答": "A"}
        判定 = HDS駆動コア().非退行継承実行(
            "入力",
            基準実行=lambda: 基準,
            基準承認判定=lambda 値: False,
            拡張実行=lambda: 拡張,
            拡張承認判定=lambda 値: True,
            拡張採用証明=lambda 旧, 新: False,
        )
        self.assertIs(判定.出力, 基準)
        self.assertTrue(判定.基準固定)
        self.assertFalse(判定.拡張採用)

    def test_拡張実行省略時は新HDSコア自身を使う(self):
        コア = HDS駆動コア(
            作用供給器=(HDS作用供給器("供給", lambda 状態: (_完了作用(),)),),
        )
        基準 = {"状態": "SUSPEND"}
        判定 = コア.非退行継承実行(
            "完了させる",
            基準実行=lambda: 基準,
            基準承認判定=lambda 値: False,
            拡張採用証明=lambda 旧, 新: 新.終端 == HDS終端.採用,
            要求状態=("完了",),
        )
        self.assertTrue(判定.拡張採用)
        self.assertEqual(判定.出力.終端, HDS終端.採用)


if __name__ == "__main__":
    unittest.main()

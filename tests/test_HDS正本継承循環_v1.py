from __future__ import annotations

import unittest

from minidora.HDS構文化器_v1 import 公開HDSコンパイラ
from minidora.HDS駆動コア import HDS駆動コア, HDS駆動コア版
from minidora.HDS実行主体 import HDS終端, HDS作用供給器, HDS関数作用, HDS作用結果, HDS作用状態
from minidora.HDS選択継承循環 import (
    回答成果名,
    基準結果成果名,
    現行結果成果名,
    影結果成果名,
    非退行判定成果名,
    参照世代成果名,
)
from minidora.参照 import 参照記録


class 固定追加参照:
    名称 = "試験追加参照"

    def __init__(self, 記録群):
        self.記録群 = tuple(記録群)
        self.呼出回数 = 0

    def 検索(self, 問合せ, 上限=8):
        self.呼出回数 += 1
        return self.記録群[:上限]


def 証拠(主体: str, *, 否定: bool = False, 識別子: str = "r1"):
    本文 = f"{主体} {'does not inhibit' if 否定 else 'inhibits'} Enzyme X."
    return 参照記録(
        識別子=識別子,
        対象=主体,
        内容=本文,
        由来="試験",
        供給器="試験資料",
        信頼=1.0,
    )


class HDS正本継承循環試験(unittest.TestCase):
    def setUp(self):
        self.構文化器 = 公開HDSコンパイラ()
        self.コア = HDS駆動コア(HDSコンパイラ=self.構文化器, 最大作用回数=24)
        self.問い = "Which molecule inhibits Enzyme X?"
        self.選択肢 = ("Molecule A", "Molecule B")

    def test_版はv5(self):
        self.assertEqual(HDS駆動コア版, "MINIDORA-HDS-FIRST-v5")


    def test_駆動コアが要求単位の動的作用供給を保持(self):
        def 供給(状態):
            if "継承確認済み" in 状態.成立状態:
                return ()
            return (
                HDS関数作用(
                    "継承確認",
                    lambda _状態: HDS作用結果(
                        HDS作用状態.成立,
                        追加状態=frozenset({"継承確認済み"}),
                    ),
                    出力状態=("継承確認済み",),
                ),
            )

        結果 = HDS駆動コア().実行(
            "継承確認",
            要求状態=("継承確認済み",),
            追加作用供給器=(HDS作用供給器("継承確認供給", 供給),),
        )
        self.assertEqual(結果.終端, HDS終端.採用)
        self.assertEqual([x.作用ID for x in 結果.履歴], ["継承確認"])

    def test_基準承認済みは追加観測せず完全保持(self):
        provider = 固定追加参照((証拠("Molecule B", 識別子="late"),))
        結果 = self.コア.選択実行(
            self.問い,
            self.選択肢,
            初期参照=(証拠("Molecule A", 識別子="base"),),
            参照供給器=provider,
        )
        self.assertEqual(結果.終端, HDS終端.採用, 結果.理由)
        成果 = 結果.状態.成果辞書()
        self.assertEqual(成果[回答成果名], "A")
        self.assertIs(成果[基準結果成果名], 成果[現行結果成果名])
        self.assertEqual(provider.呼出回数, 0)
        self.assertEqual([x.作用ID for x in 結果.履歴], ["HDS継承/模型再評価"])

    def test_未閉包は追加参照して再評価し閉包(self):
        provider = 固定追加参照((証拠("Molecule A", 識別子="extra"),))
        結果 = self.コア.選択実行(
            self.問い,
            self.選択肢,
            初期参照=(),
            参照供給器=provider,
        )
        self.assertEqual(結果.終端, HDS終端.採用, 結果.理由)
        成果 = 結果.状態.成果辞書()
        self.assertEqual(成果[回答成果名], "A")
        self.assertGreaterEqual(provider.呼出回数, 1)
        self.assertGreaterEqual(int(成果[参照世代成果名]), 1)
        self.assertEqual(
            [x.作用ID for x in 結果.履歴[:3]],
            ["HDS継承/模型再評価", "HDS継承/追加参照", "HDS継承/模型再評価"],
        )
        判定 = 成果[非退行判定成果名]
        self.assertTrue(判定.拡張採用)
        self.assertFalse(判定.基準固定)

    def test_証明なし拡張は影結果に留まり採用しない(self):
        provider = 固定追加参照((証拠("Molecule A", 識別子="extra"),))
        結果 = self.コア.選択実行(
            self.問い,
            self.選択肢,
            初期参照=(),
            参照供給器=provider,
            拡張採用証明=lambda _前, _後: False,
        )
        self.assertEqual(結果.終端, HDS終端.保留)
        成果 = 結果.状態.成果辞書()
        self.assertNotIn(回答成果名, 成果)
        self.assertIn(影結果成果名, 成果)
        self.assertTrue(成果[非退行判定成果名].基準固定)
        self.assertFalse(成果[非退行判定成果名].拡張採用)

    def test_追加参照なしは推測せず保留(self):
        結果 = self.コア.選択実行(self.問い, self.選択肢, 初期参照=())
        self.assertEqual(結果.終端, HDS終端.保留)
        成果 = 結果.状態.成果辞書()
        self.assertNotIn(回答成果名, 成果)
        self.assertEqual(成果[基準結果成果名].状態, "SUSPEND")


if __name__ == "__main__":
    unittest.main()

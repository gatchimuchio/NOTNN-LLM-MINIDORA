from __future__ import annotations

import unittest

from minidora.HDS実行主体 import (
    HDS作用結果,
    HDS作用状態,
    HDS実行主体,
    HDS実行状態,
    HDS終端,
    HDS関数作用,
)
from minidora.HDS駆動コア import HDS駆動コア
from minidora.統合駆動_v2.学習 import HDS経験学習器


def _処理作用():
    return HDS関数作用(
        "学習試験/処理",
        lambda _状態: HDS作用結果(HDS作用状態.成立, 追加状態=frozenset({"完了"})),
        純粋作用=True,
        作用定義ID="学習試験/共通処理",
    )


def _ノイズ作用(*, 純粋=True):
    return HDS関数作用(
        "学習試験/高優先度ノイズ",
        lambda _状態: HDS作用結果(HDS作用状態.成立, 追加状態=frozenset({"ノイズ"})),
        出力状態=("ノイズ",),
        優先度=100.0,
        純粋作用=純粋,
        作用定義ID="学習試験/ノイズ",
    )


def _状態(文脈):
    return HDS実行状態(
        要求状態=frozenset({"完了"}),
        主体状態=(("文脈", 文脈),),
    )


class HDS経験学習統合V1試験(unittest.TestCase):
    def test_空の学習器は既存COMMITを一切変更しない(self):
        作用A = _処理作用()
        作用B = _処理作用()
        初期 = _状態("同一")
        基準 = HDS実行主体((作用A,), 最大作用回数=1).実行(初期)
        学習付き = HDS実行主体((作用B,), 最大作用回数=1, 学習器=HDS経験学習器()).実行(初期)
        self.assertEqual(基準, 学習付き)
        self.assertEqual(基準.終端, HDS終端.採用)

    def test_二文脈の共通実測効果で従来保留だけを回復する(self):
        学習器 = HDS経験学習器()
        処理 = _処理作用()
        for 文脈 in ("A", "B"):
            結果 = HDS実行主体((処理,), 最大作用回数=1, 学習器=学習器).実行(_状態(文脈))
            self.assertEqual(結果.終端, HDS終端.採用)

        ノイズ = _ノイズ作用()
        基準 = HDS実行主体((処理, ノイズ), 最大作用回数=1).実行(_状態("C"))
        self.assertEqual(基準.終端, HDS終端.保留)
        self.assertEqual(基準.履歴[0].作用ID, "学習試験/高優先度ノイズ")

        改善 = HDS実行主体((処理, ノイズ), 最大作用回数=1, 学習器=学習器).実行(_状態("C"))
        self.assertEqual(改善.終端, HDS終端.採用)
        self.assertEqual(改善.履歴[0].作用ID, "学習試験/処理")
        self.assertIn("HDS_EXPERIENCE_LEARNING_RECOVERY_COMMIT", 改善.理由)

    def test_非純粋作用を含む実行では学習回復しない(self):
        学習器 = HDS経験学習器()
        処理 = _処理作用()
        for 文脈 in ("A", "B"):
            HDS実行主体((処理,), 最大作用回数=1, 学習器=学習器).実行(_状態(文脈))
        結果 = HDS実行主体((処理, _ノイズ作用(純粋=False)), 最大作用回数=1, 学習器=学習器).実行(_状態("C"))
        self.assertEqual(結果.終端, HDS終端.保留)
        self.assertEqual(結果.履歴[0].作用ID, "学習試験/高優先度ノイズ")

    def test_コアを跨いで学習し初期化で元へ戻る(self):
        コア = HDS駆動コア(最大作用回数=1)
        処理 = _処理作用()
        for 文脈 in ("A", "B"):
            結果 = コア.実行(
                "学習経験" + 文脈,
                要求状態=("完了",),
                主体状態={"文脈": 文脈},
                追加作用=(処理,),
            )
            self.assertEqual(結果.終端, HDS終端.採用)

        改善 = コア.実行(
            "転用C",
            要求状態=("完了",),
            主体状態={"文脈": "C"},
            追加作用=(処理, _ノイズ作用()),
        )
        self.assertEqual(改善.終端, HDS終端.採用)
        self.assertIn("HDS_EXPERIENCE_LEARNING_RECOVERY_COMMIT", 改善.理由)

        コア.学習を初期化()
        復元 = コア.実行(
            "転用D",
            要求状態=("完了",),
            主体状態={"文脈": "D"},
            追加作用=(処理, _ノイズ作用()),
        )
        self.assertEqual(復元.終端, HDS終端.保留)


if __name__ == "__main__":
    unittest.main()

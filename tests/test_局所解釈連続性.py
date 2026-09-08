from __future__ import annotations

import unittest

from minidora.runtime import ミニドラ, 要求
from minidora.hds_adapter import HDS文脈
from minidora.hds_compiler_v1 import 公開HDSコンパイラ


class 局所解釈連続性試験(unittest.TestCase):
    def test_次turnは直前更新状態を起点にする(self) -> None:
        body = ミニドラ()

        first = body.実行(要求("2+3"))
        self.assertEqual(first.値, 5)
        self.assertEqual(body.局所解釈状態.版, 1)
        self.assertEqual(body.局所解釈状態.直前結果, 5)

        second = body.実行(要求("4+5"))
        self.assertEqual(second.値, 9)
        self.assertEqual(second.状態["局所解釈起点"]["版"], 1)
        self.assertEqual(second.状態["局所解釈起点"]["直前結果"], 5)
        self.assertEqual(body.局所解釈状態.版, 2)
        self.assertEqual(body.局所解釈状態.直前結果, 9)

    def test_HDS非接続turnも局所解釈を更新する(self) -> None:
        body = ミニドラ()
        body.実行(要求("2+3"))

        context = body.HDS文脈
        self.assertEqual(context.記憶版, 1)
        self.assertEqual(context.直前入力, "2+3")
        self.assertEqual(context.直前結果, 5)
        self.assertEqual(context.現在焦点, 5)
        self.assertEqual(context.直前採否, "合格")

    def test_保留は採用済み焦点を無言上書きしない(self) -> None:
        body = ミニドラ()
        body.実行(要求("2+3"))
        held = body.実行(要求("外部確認が必要な質問"))

        self.assertEqual(held.採否.状態.value, "保留")
        self.assertEqual(held.状態["局所解釈起点"]["直前結果"], 5)
        self.assertEqual(body.局所解釈状態.現在焦点, 5)
        self.assertEqual(body.局所解釈状態.直前結果, 5)
        self.assertEqual(body.局所解釈状態.直前採否, "保留")

    def test_Runtime境界と明示初期化で局所状態を切れる(self) -> None:
        first = ミニドラ()
        second = ミニドラ()
        first.実行(要求("2+3"))

        self.assertEqual(first.局所解釈状態.版, 1)
        self.assertEqual(second.局所解釈状態.版, 0)

        first.局所解釈を初期化()
        self.assertEqual(first.局所解釈状態.版, 0)
        self.assertIsNone(first.局所解釈状態.直前入力)
        self.assertIsNone(first.局所解釈状態.現在焦点)

    def test_HDS非接続でも局所解釈が最終計算へ到達する(self) -> None:
        body = ミニドラ()
        first = body.実行(要求("2+3"))
        second = body.実行(要求("それに4を足して"))

        self.assertEqual(first.値, 5)
        self.assertEqual(second.値, 9)
        self.assertEqual(second.状態["局所解釈起点"]["直前結果"], 5)
        self.assertEqual(second.状態["文脈0"], 5)

    def test_HDS接続でも局所解釈が意味IRから最終計算まで到達する(self) -> None:
        compiler = 公開HDSコンパイラ()
        body = ミニドラ(HDSコンパイラ_=compiler)
        first = body.実行(要求("2+3"))
        second = body.実行(要求("それに4を足して"))

        self.assertEqual(first.値, 5)
        self.assertEqual(second.値, 9)
        self.assertIsNotNone(second.HDS_IR)
        assert second.HDS_IR is not None
        self.assertTrue(any(item.種別 == "共参照" for item in second.HDS_IR.関係))
        self.assertEqual(second.状態["文脈0"], 5)

    def test_resetすると同じ追加入力は成立しない(self) -> None:
        body = ミニドラ(HDSコンパイラ_=公開HDSコンパイラ())
        body.実行(要求("2+3"))
        body.局所解釈を初期化()
        reset = body.実行(要求("それに4を足して"))

        self.assertIsNone(reset.値)
        self.assertNotEqual(reset.採否.状態.value, "合格")

    def test_計算Pへ文脈Dataを埋め込まず状態参照で束縛する(self) -> None:
        compiler = 公開HDSコンパイラ()
        context = HDS文脈(
            記憶版=1,
            現在焦点=5,
            直前結果=5,
            直前入力="2+3",
            直前採否="合格",
        )
        bundle = compiler.コンパイル束("それに4を足して", 文脈=context, 前回結果=5)
        plan = bundle.計算計画

        self.assertEqual(plan.初期状態["文脈0"], 5)
        self.assertEqual(plan.初期状態["入力0"], 4)
        self.assertEqual(plan.手順.命令列[0].引数, ("$文脈0", "$入力0"))
        self.assertNotIn(5, plan.手順.命令列[0].引数)
        self.assertTrue(any(item.種別 == "共参照" for item in bundle.意味IR.関係))


if __name__ == "__main__":
    unittest.main()

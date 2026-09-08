from __future__ import annotations

import unittest

from minidora.runtime import ミニドラ, 要求


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


if __name__ == "__main__":
    unittest.main()

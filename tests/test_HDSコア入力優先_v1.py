from __future__ import annotations

import unittest

from minidora.HDSコア入力 import HDSコア入力束
from minidora.HDS適合器 import HDS独立コア入力コンパイル
from minidora.HDS構文化作用 import HDS構文化作用
from minidora.HDS構文化器_v1 import 公開HDSコンパイラ
from minidora.HDS実行主体 import HDS実行状態, HDS作用状態


class HDSコア入力優先試験(unittest.TestCase):
    def setUp(self) -> None:
        self.構文化器 = 公開HDSコンパイラ()

    def test_コア入力が構文化器の正本である(self):
        入力束 = self.構文化器.コア入力コンパイル("A causes B")
        self.assertIsInstance(入力束, HDSコア入力束)
        self.assertTrue(入力束.コア需要を検査())
        for 名 in ("手順", "計算計画", "作用差分構造", "意味作用履歴", "初期状態"):
            self.assertFalse(hasattr(入力束, 名), 名)

    def test_コア入力正本ではLegacy計画と監査副産物を生成しない(self):
        class 計画禁止:
            def 計画(self, *args, **kwargs):
                raise AssertionError("Core入力正本でLegacy計画器を呼んだ")

        def 監査禁止(*args, **kwargs):
            raise AssertionError("Core入力正本で監査副産物を生成した")

        self.構文化器._計算計画器 = 計画禁止()
        self.構文化器._完成 = 監査禁止
        入力束 = self.構文化器.コア入力コンパイル("A causes B")
        self.assertIsInstance(入力束, HDSコア入力束)

    def test_コンパイル束はコア入力を正本としてLegacy成果を分離する(self):
        束 = self.構文化器.コンパイル束("2+3")
        self.assertIs(束.正本, 束.コア入力)
        self.assertIsNone(束.意味IR.手順)
        self.assertTrue(束.計算計画.手順.命令列)
        self.assertFalse(hasattr(束.正本, "計算計画"))

    def test_監査座標はコア入力へ混入しない(self):
        詳細 = self.構文化器.詳細コンパイル("A causes B")
        self.assertTrue(any(x.種別.startswith("監査.") for x in 詳細.IR.座標))
        入力束 = self.構文化器.コア入力コンパイル("A causes B")
        self.assertFalse(any(x.種別.startswith(("監査.", "保持.", "暫定性.", "帰還.")) for x in 入力束.意味項目))

    def test_意味条件と関係制約を混同せず能力名へ変換しない(self):
        入力束 = self.構文化器.コア入力コンパイル("If A causes B, B increases C.")
        self.assertTrue(入力束.関係)
        self.assertTrue(入力束.条件)
        self.assertTrue(all(x.種別 for x in 入力束.条件))
        self.assertTrue(any(any(v.startswith("検索述語=") for v in x.制約) for x in 入力束.関係))
        self.assertFalse(any(any(v.startswith("検索述語=") for v in (str(x.内容),)) for x in 入力束.条件))
        self.assertEqual(入力束.作用要求, ())
        self.assertEqual(入力束.要求成果, ())

    def test_選択候補を作用要求や完了条件へ昇格しない(self):
        入力束 = self.構文化器.問題コア入力("Which is correct?", ("A", "B", "C"))
        self.assertTrue(any(x.種別 == "候補" for x in 入力束.目的))
        self.assertEqual(入力束.作用要求, ())
        self.assertEqual(入力束.要求成果, ())

    def test_明示作用要求を能力名なしで供給する(self):
        入力束 = self.構文化器.コア入力コンパイル("本文を要約してください。")
        self.assertEqual(tuple(x.種別 for x in 入力束.作用要求), ("要約",))
        self.assertEqual(入力束.要求成果, ("要約結果",))
        self.assertFalse(any(hasattr(x, "能力") for x in 入力束.作用要求))

    def test_未知命令形を黙って捨てない(self):
        入力束 = self.構文化器.コア入力コンパイル("本文を未知操作してください。")
        self.assertTrue(any(x.種別 == "作用要求未構文化" for x in 入力束.残差))
        self.assertEqual(入力束.作用要求, ())

    def test_説明文中の英語動詞を要求へ誤認しない(self):
        入力束 = self.構文化器.コア入力コンパイル("We compare A and B.")
        self.assertEqual(入力束.作用要求, ())

    def test_独立コア入力コンパイルは会話文脈を混入しない(self):
        入力束 = HDS独立コア入力コンパイル(self.構文化器, "A inhibits B")
        self.assertIsInstance(入力束, HDSコア入力束)
        self.assertEqual(入力束.文脈引用, ())
        self.assertTrue(any(x.種別 == "阻害" for x in 入力束.関係))

    def test_構文化作用はコア入力を第一級成果として返す(self):
        作用 = HDS構文化作用(self.構文化器, "A causes B")
        結果 = 作用.実行(HDS実行状態())
        self.assertEqual(結果.状態, HDS作用状態.成立)
        成果 = dict(結果.成果)
        self.assertIsInstance(成果["HDSコア入力"], HDSコア入力束)
        self.assertIn("HDS_IR", 成果)
        self.assertEqual(dict(結果.主体状態差分)["HDSコア入力署名"], 成果["HDSコア入力"].意味署名)

    def test_コア入力からC7用の経験効果を捏造しない(self):
        入力束 = self.構文化器.コア入力コンパイル("A causes B")
        使用責任 = {責任 for _, 責任群 in 入力束.消費責任 for 責任 in 責任群}
        self.assertNotIn("C7", 使用責任)
        self.assertFalse(hasattr(入力束, "期待効果"))


if __name__ == "__main__":
    unittest.main()

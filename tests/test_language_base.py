from __future__ import annotations

import unittest

from minidora import 公開HDSコンパイラ, 標準言語基底P
from minidora.semantic_tokens import 意味語


class 言語基底P試験(unittest.TestCase):
    def test_かなとカタカナを同じ音へ接続する(self) -> None:
        hira = 標準言語基底P.文字知識("ね")
        kata = 標準言語基底P.文字知識("ネ")
        self.assertEqual(hira.体系, "ひらがな")
        self.assertEqual(kata.体系, "カタカナ")
        self.assertEqual(hira.ローマ字, "ne")
        self.assertEqual(kata.ローマ字, "ne")
        self.assertEqual(kata.読み, "ね")

    def test_漢字とラテン文字を文字体系として分別する(self) -> None:
        self.assertEqual(標準言語基底P.文字知識("猫").体系, "漢字")
        self.assertEqual(標準言語基底P.文字知識("A").体系, "ラテン文字")
        self.assertEqual(標準言語基底P.文字知識("3").体系, "数字")

    def test_日本語正本なので漢字単独を自動的に中国語扱いしない(self) -> None:
        self.assertEqual(標準言語基底P.入力言語判定("猫"), "ja")
        self.assertEqual(標準言語基底P.入力言語判定("ねこ"), "ja")
        self.assertEqual(標準言語基底P.入力言語判定("cat"), "en")
        self.assertEqual(標準言語基底P.入力言語判定("这是猫"), "zh")

    def test_基底文法と基底P概念を世界知識と分けて保持する(self) -> None:
        self.assertEqual(標準言語基底P.文法機能("は"), "主題")
        self.assertEqual(標準言語基底P.文法機能("if"), "条件")
        relation = 標準言語基底P.語彙知識("因果")
        self.assertIsNotNone(relation)
        self.assertEqual(relation.区分, "関係")
        self.assertIsNone(標準言語基底P.語彙知識("東京都の人口"))

    def test_HDS_Compilerが同じ言語基底Pを保持する(self) -> None:
        compiler = 公開HDSコンパイラ()
        self.assertIs(compiler.言語基底P, 標準言語基底P)
        self.assertEqual(compiler.コンパイル("猫").入力言語, "ja")
        self.assertEqual(compiler.コンパイル("What is a cat?").入力言語, "en")

    def test_ミニドラ意味処理が一文字漢字を意味記号として保持する(self) -> None:
        self.assertIn("猫", 意味語("猫"))
        self.assertNotIn("は", 意味語("猫 は 動物"))
        self.assertIn("猫", 意味語("猫 は 動物"))
        self.assertIn("動物", 意味語("猫 は 動物"))

    def test_言語基底版と統計を機械取得できる(self) -> None:
        stats = 標準言語基底P.統計()
        self.assertEqual(stats["版"], "v0.1")
        self.assertGreaterEqual(stats["ひらがな"], 46)
        self.assertGreaterEqual(stats["カタカナ"], 46)
        self.assertGreater(stats["日本語基底語彙"], 0)
        self.assertGreater(stats["英語基底機能"], 0)


if __name__ == "__main__":
    unittest.main()

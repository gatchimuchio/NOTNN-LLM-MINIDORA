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

    def test_日本語正本と外部言語識別コードを分離する(self) -> None:
        self.assertEqual(標準言語基底P.規定言語, "日本語")
        self.assertEqual(標準言語基底P.基底言語, "日本語")
        self.assertEqual(標準言語基底P.基底言語コード, "ja")
        self.assertEqual(標準言語基底P.入力言語判定("猫"), "ja")
        self.assertEqual(標準言語基底P.入力言語判定("ねこ"), "ja")
        self.assertEqual(標準言語基底P.入力言語判定("cat"), "en")
        self.assertEqual(標準言語基底P.入力言語判定("这是猫"), "zh")
        self.assertEqual(標準言語基底P.入力言語名("cat"), "英語")

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

    def test_外部英語関係知識は日本語正本概念へ接続する(self) -> None:
        self.assertEqual(標準言語基底P.英語基本形("generated"), "generate")
        self.assertEqual(標準言語基底P.英語関係概念("suppressed"), "阻害")
        self.assertIn("generate", 標準言語基底P.英語関係族()["生成"])
        self.assertTrue(標準言語基底P.英語関係構文())
        knowledge = 標準言語基底P.語彙知識("generated")
        self.assertIsNotNone(knowledge)
        self.assertEqual(knowledge.基本義, ("生成",))
        self.assertEqual(knowledge.区分, "関係語")

    def test_一般関係も日本語概念へ接続する(self) -> None:
        self.assertEqual(標準言語基底P.英語基本形("interactions"), "interact")
        self.assertEqual(標準言語基底P.英語関係概念("interacts"), "相互作用")
        self.assertEqual(標準言語基底P.英語関係概念("bound"), "結合")
        self.assertEqual(標準言語基底P.英語関係概念("located"), "位置")
        self.assertEqual(標準言語基底P.英語関係概念("derived"), "由来")
        self.assertIn("rel:相互作用", 意味語("interactions"))

    def test_言語基底版と統計を機械取得できる(self) -> None:
        stats = 標準言語基底P.統計()
        self.assertEqual(stats["版"], "v0.4")
        self.assertEqual(stats["規定言語"], "日本語")
        self.assertEqual(stats["基底言語"], "日本語")
        self.assertEqual(stats["基底言語コード"], "ja")
        self.assertGreaterEqual(stats["ひらがな"], 46)
        self.assertGreaterEqual(stats["カタカナ"], 46)
        self.assertGreater(stats["日本語基底語彙"], 0)
        self.assertGreater(stats["外部英語文法機能"], 0)
        self.assertGreaterEqual(stats["外部英語関係族"], 17)
        self.assertGreater(stats["外部英語関係基本形"], 0)
        self.assertNotIn("英語基底機能", stats)


if __name__ == "__main__":
    unittest.main()

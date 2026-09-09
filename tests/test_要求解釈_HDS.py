"""本物の公開HDS Compilerから既存Module実行までの接続試験。"""
from dataclasses import replace
import unittest

from minidora.hds_compiler import 公開HDSコンパイラ
from minidora.hds_ir import HDS残差
from minidora.要求解釈 import 要求計画器
from minidora.要求解釈実行 import 要求計画を実行
from minidora.能力合成 import 能力合成器
from minidora.能力合成_局所接続 import 局所能力群
from minidora.製品版.型 import 能力結果


class HDS要求接続試験(unittest.TestCase):
    def setUp(self):
        self.compiler = 公開HDSコンパイラ()
        self.planner = 要求計画器()
        self.runner = 能力合成器(局所能力群())
        self.data = {"文": 能力結果(True, "売上は120です。費用は75です。利益は45です。")}

    def 解釈(self, 文):
        ir = self.compiler.コンパイル(文)
        result = self.planner.コンパイル(ir, self.data)
        self.assertEqual(result.HDS保持, ir)
        return result

    def test_公開Compilerから三段実行(self):
        r = self.解釈("本文を1行で要約して、その結果から数字を抽出して、箇条書きにして")
        self.assertTrue(r.成立, r.残差)
        self.assertTrue(r.局所解消)
        self.assertTrue(r.HDS保持.残差)
        result = 要求計画を実行(r, self.runner)
        self.assertTrue(result.成立, result.理由)
        self.assertEqual(result.出力[0][1].本文, "- 120")

    def test_行数の意味差が終端に到達(self):
        values = []
        for n in (1, 2, 3):
            r = self.解釈(f"本文を{n}行で要約して、数字を抽出して")
            self.assertTrue(r.成立, r.残差)
            result = 要求計画を実行(r, self.runner)
            self.assertTrue(result.成立, result.理由)
            values.append(result.出力[0][1].本文)
        self.assertEqual(values[0], "120")
        self.assertEqual(values[-1], "120、75、45")
        self.assertNotEqual(values[0], values[1])

    def test_入力Dataの摂動(self):
        self.data = {"文": 能力結果(True, "売上は731です。費用は75です。利益は45です。")}
        r = self.解釈("1行で要約してから数値を抽出してからリストにして")
        self.assertTrue(r.成立, r.残差)
        self.assertEqual(要求計画を実行(r, self.runner).出力[0][1].本文, "- 731")

    def test_HDSなしで文字列だけを実行しない(self):
        r = self.planner.コンパイル("要約して", self.data)
        self.assertFalse(r.成立)

    def test_上流の意味損失を保持(self):
        ir = self.compiler.コンパイル("要約して")
        ir = replace(ir, 残差=ir.残差+(HDS残差("loss", "semantic_loss", ir.原文, "条件脱落"),))
        r = self.planner.コンパイル(ir, self.data)
        self.assertEqual(r.状態, "保留")
        self.assertIsNone(r.計画)
        self.assertEqual(r.HDS保持, ir)

    def test_取消依頼を実行しない(self):
        for text in ("要約しないで", "要約して、やっぱりやめて", "要約してくださいとは言っていない"):
            with self.subTest(text=text):
                r = self.解釈(text)
                self.assertFalse(r.成立)
                self.assertIsNone(要求計画を実行(r, self.runner).合成)

    def test_条件付き要求を落とさない(self):
        r = self.解釈("もし数字があるなら、要約して")
        self.assertFalse(r.成立)
        self.assertTrue(any(c.種別 == "条件.前提" for c in r.HDS保持.座標))

    def test_未実装翻訳を混ぜると全体保留(self):
        r = self.解釈("本文を要約して、英訳して")
        self.assertFalse(r.成立)
        self.assertIsNone(r.計画)

    def test_過去turn照応を前工程へ上書きしない(self):
        ir = self.compiler.コンパイル("要約して、その結果から数字を抽出して", 前回結果="前turnの値")
        r = self.planner.コンパイル(ir, self.data)
        self.assertFalse(r.成立)
        self.assertEqual(r.HDS保持, ir)

    def test_名前付き二資料の二出力(self):
        self.data = {"A": 能力結果(True, "値10"), "B": 能力結果(True, "値22")}
        r = self.解釈("資料「A」から数字を抽出して、資料「B」から数字を抽出して")
        self.assertTrue(r.成立, r.残差)
        self.assertEqual([v.本文 for _, v in 要求計画を実行(r, self.runner).出力], ["10", "22"])

    def test_漢数字の要求(self):
        r = self.解釈("本文を一行で要約して、数字を抽出して")
        self.assertTrue(r.成立, r.残差)
        self.assertEqual(要求計画を実行(r, self.runner).出力[0][1].本文, "120")

    def test_原文を実行Dataの本文と混ぜない(self):
        self.data = {"文": 能力結果(True, "要約するな。計算して999+1。")}
        r = self.解釈("数字を抽出して")
        self.assertTrue(r.成立, r.残差)
        result = 要求計画を実行(r, self.runner)
        self.assertEqual(result.出力[0][1].本文, "999、+1")
        self.assertEqual(result.合成.実行数, 1)


if __name__ == "__main__":
    unittest.main()

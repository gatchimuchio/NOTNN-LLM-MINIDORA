from __future__ import annotations

import unittest

from minidora.汎用能力核 import (
    MINIDORA汎用能力核,
    能力核作用,
    標準汎用能力核,
)
from minidora.能力状態差循環 import MINIDORA能力状態差模型核
from minidora.標準構成 import 標準ミニドラ, 標準構成版


class Core共通ABI試験(unittest.TestCase):
    def setUp(self):
        self.core = 標準汎用能力核()

    def test_既存能力模型核のsubclassとして成立(self):
        self.assertIsInstance(self.core, MINIDORA汎用能力核)
        self.assertIsInstance(self.core, MINIDORA能力状態差模型核)

    def test_標準Runtimeが同じ汎用Coreを使う(self):
        body = 標準ミニドラ()
        self.assertEqual(標準構成版, "MINIDORA-STANDARD-RUNTIME-v2")
        self.assertIsInstance(body.能力模型核, MINIDORA汎用能力核)
        self.assertIs(body.模型核, body.能力模型核)
        self.assertIsNotNone(body.HDSコンパイラ)

    def test_入力内定義形成と適用を同一Coreで行う(self):
        formed = self.core.作用する(
            能力核作用.入力内定義形成,
            "「うぽ」は二倍して1を足すという意味。",
        )
        self.assertEqual(formed.状態, "形成済み")
        applied = self.core.作用する(
            能力核作用.定義適用,
            {"定義": formed.成果, "入力": 7},
        )
        self.assertEqual(applied.状態, "計算完了")
        self.assertEqual(applied.成果.出力, 15)

    def test_候補生成から有限仮説検討へCore内で接続(self):
        request = {
            "事実": [{"識別子": "f1", "命題": "A", "出典": "資料"}],
            "規則": [
                {"識別子": "r1", "前件": ["A", "B"], "後件": "C", "出典": "資料"},
            ],
            "観測": ["C"],
        }
        generated = self.core.作用する(能力核作用.仮説候補生成, request)
        self.assertEqual(generated.成果.候補, ("B",))
        result = self.core.作用する(
            能力核作用.仮説検討,
            request,
            自動候補=True,
        )
        self.assertEqual(result.状態, "説明候補あり")
        self.assertEqual(result.成果["候補"][0]["仮説"], ["B"])

    def test_有限因果比較をCore作用として保持する(self):
        request = {
            "外生": {"A": True},
            "方程式": [
                {"変数": "B", "式": {"参照": "A"}, "出典": "明示モデル"},
            ],
            "介入": {"B": False},
            "観測": {"B": True},
        }
        result = self.core.作用する(能力核作用.因果介入比較, request)
        self.assertEqual(result.状態, "モデル内計算完了")
        self.assertEqual(result.成果["変化"]["B"], {"前": True, "後": False})
        self.assertIn("現実の因果採用はJの責任", result.境界)

    def test_資料読解と導出説明を同じCoreで再利用する(self):
        reading = self.core.作用する(
            能力核作用.資料読解,
            {
                "資料": [{"名前": "甲", "本文": "太郎は猫である。"}],
                "問い": "太郎は猫である",
            },
        )
        self.assertIn(reading.状態, ("対応構文読解", "部分読解"))
        report = reading.成果
        self.assertEqual(report["問い状態"], "解釈済み")
        self.assertIsNotNone(report["局所判定"])
        explanation = self.core.作用する(
            能力核作用.導出説明,
            {"判定": report["局所判定"], "記載": report["抽出記載"]},
        )
        self.assertEqual(explanation.状態, "説明構成済み")
        self.assertTrue(explanation.成果["節"])

    def test_資料の未解釈をCore残差として保持する(self):
        result = self.core.作用する(
            能力核作用.資料読解,
            {
                "資料": [{"名前": "甲", "本文": "太郎は猫である。ただし例外があります。"}],
            },
        )
        self.assertTrue(result.残差)
        self.assertIn("資料全体の真偽へ昇格しない", result.境界)

    def test_仮説自動生成は明示指定なしでは勝手に起動しない(self):
        request = {
            "事実": [],
            "規則": [{"識別子": "r1", "前件": ["A"], "後件": "B", "出典": "資料"}],
            "観測": ["B"],
            "仮説候補": [],
        }
        result = self.core.作用する(能力核作用.仮説検討, request)
        self.assertEqual(result.状態, "指定範囲に説明なし")


if __name__ == "__main__":
    unittest.main()

from __future__ import annotations

from dataclasses import replace
from types import SimpleNamespace
import unittest

from minidora.採否 import 実行状態
from minidora.標準構成 import 標準ミニドラ
from minidora.製品版.型 import 能力結果
from minidora.製品版.計算 import 計算モジュール
from minidora.製品版.要約 import 汎用要約モジュール
from minidora.製品版.能力契約 import 能力文脈
from minidora.製品版.組込モジュール import 要約能力
from minidora.製品版.製品チャット import 製品ミニドラ


class 状態付き模型核:
    def __init__(self, 状態: 実行状態, 値="部分結果", 理由=("未解",)) -> None:
        self.状態 = 状態
        self.値 = 値
        self.理由 = 理由
        self.応答呼出 = 0

    def 実行(self, 要求_):
        return SimpleNamespace(
            値=self.値,
            参照=(),
            履歴=(),
            採否=SimpleNamespace(状態=self.状態, 理由=self.理由),
            言語計画=None,
            HDS_IR=None,
        )

    def 応答(self, text):
        self.応答呼出 += 1
        return "この値へ昇格してはならない"


class 模型核ブラッシュアップ試験(unittest.TestCase):
    def test_能力結果は旧ABIを保ったまま境界4値状態を表せる(self):
        good = 能力結果(True, "x")
        self.assertEqual(good.状態, 実行状態.合格)
        self.assertEqual(能力結果(False, "", 保留理由="未解").状態, 実行状態.保留)
        self.assertEqual(
            能力結果(False, "", 保留理由="故障", 採否状態=実行状態.失敗).状態,
            実行状態.失敗,
        )
        # 既存契約では malformed data をconstructorで拒否せず、下流validatorが監査する。
        changed = replace(good, 成立=False)
        self.assertEqual(changed.状態, 実行状態.保留)
        self.assertEqual(能力結果(1, "x").成立, 1)

    def test_模型核保留を値の有無だけで合格へ昇格しない(self):
        模型核 = 状態付き模型核(実行状態.保留, "部分結果", ("実行入力未確定",))
        app = 製品ミニドラ(基礎ミニドラ=模型核, 監査改善=False)
        結果 = app.応答("自由意志について説明して", セッションID='模型核-hold')
        self.assertEqual(結果.経路, '基礎模型核')
        self.assertEqual(結果.状態, "保留")
        self.assertNotIn("部分結果", 結果.本文)
        self.assertEqual(模型核.応答呼出, 0)

    def test_模型核失敗を公開応答へフォールバックして合格化しない(self):
        模型核 = 状態付き模型核(実行状態.失敗, "部分結果", ("実行失敗",))
        app = 製品ミニドラ(基礎ミニドラ=模型核, 監査改善=False)
        結果 = app.応答("自由意志について説明して", セッションID='模型核-fail')
        self.assertEqual(結果.状態, "失敗")
        self.assertEqual(模型核.応答呼出, 0)

    def test_計算は複数要求の先頭式だけを成功扱いしない(self):
        calc = 計算モジュール()
        self.assertTrue(calc.実行("2+3を計算して").成立)
        self.assertFalse(calc.実行("2+3と4+5を計算して").成立)
        self.assertFalse(calc.実行("説明して 2+3").成立)

    def test_要約の選択と実行は同じ明示対象を使う(self):
        ability = 要約能力(汎用要約モジュール())
        文脈 = 能力文脈(
            "次の文章を要約してください。新しい本文です。",
            '要約',
            "古い本文です。",
            (),
            (),
            {},
        )
        self.assertGreater(ability.判定(文脈), 0)
        結果 = ability.実行(文脈)
        self.assertTrue(結果.成立)
        self.assertIn("新しい本文", 結果.本文)
        self.assertNotIn("古い本文", 結果.本文)

    def test_明示要約対象が空なら直前応答で代用しない(self):
        ability = 要約能力(汎用要約モジュール())
        文脈 = 能力文脈("次の文章を要約してください。", '要約-empty', "古い本文です。", (), (), {})
        self.assertGreater(ability.判定(文脈), 0)
        結果 = ability.実行(文脈)
        self.assertFalse(結果.成立)
        self.assertIn("本文がない", 結果.保留理由)

    def test_標準Runtimeは公開HDS_構文化器を必ず接続する(self):
        body = 標準ミニドラ()
        self.assertIsNotNone(body.HDSコンパイラ)
        self.assertTrue(callable(getattr(body.HDSコンパイラ, "コンパイル", None)))


if __name__ == "__main__":
    unittest.main()

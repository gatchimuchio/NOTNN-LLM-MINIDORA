from __future__ import annotations

import unittest

from minidora.HDS実行主体 import HDS実行主体, HDS実行状態, HDS終端
from minidora.HDS汎用作用 import HDS参照取得作用, HDS計算実行作用
from minidora.参照 import 固定参照供給器, 参照記録
from minidora.計算中間表現 import 計算中間表現, 計算実行結果


class _計算器:
    def __init__(self, 出力):
        self.出力 = 出力
        self.呼出回数 = 0

    def 計算実行(self, 中間表現, 初期状態=None):
        self.呼出回数 += 1
        return 計算実行結果(dict(初期状態 or {}), (), False, self.出力)


class HDS汎用作用試験(unittest.TestCase):
    def test_参照取得は観測作用として残差を解消する(self):
        供給器 = 固定参照供給器((
            参照記録("r1", "対象", "対象の資料", "試験", "固定"),
        ))
        作用 = HDS参照取得作用(供給器, "対象")
        初期 = HDS実行状態(
            要求状態=frozenset({"参照取得済み"}),
            残差=frozenset({"観測不足"}),
        )
        結果 = HDS実行主体((作用,), 最大作用回数=3).実行(初期)
        self.assertEqual(結果.終端, HDS終端.採用)
        self.assertIn("参照取得済み", 結果.状態.成立状態)
        self.assertNotIn("観測不足", 結果.状態.残差)
        self.assertEqual(len(結果.状態.成果辞書()["参照記録"]), 1)

    def test_空参照を観測十分へ昇格しない(self):
        供給器 = 固定参照供給器(())
        作用 = HDS参照取得作用(供給器, "対象")
        初期 = HDS実行状態(
            要求状態=frozenset({"参照取得済み"}),
            残差=frozenset({"観測不足"}),
        )
        結果 = HDS実行主体((作用,), 最大作用回数=4).実行(初期)
        self.assertEqual(結果.終端, HDS終端.保留)
        self.assertIn("観測不足", 結果.状態.残差)
        self.assertNotIn("参照取得済み", 結果.状態.成立状態)

    def test_計算実行は局所成果をHDSへ帰還する(self):
        計算器 = _計算器(3)
        中間表現 = 計算中間表現("試験計算", ())
        作用 = HDS計算実行作用(計算器, 中間表現)
        初期 = HDS実行状態(
            要求状態=frozenset({"計算実行済み"}),
            残差=frozenset({"計算要求"}),
        )
        結果 = HDS実行主体((作用,), 最大作用回数=3).実行(初期)
        self.assertEqual(結果.終端, HDS終端.採用)
        self.assertEqual(計算器.呼出回数, 1)
        self.assertEqual(結果.状態.成果辞書()["計算結果"], 3)
        self.assertNotIn("計算要求", 結果.状態.残差)

    def test_計算出力なしを成功扱いしない(self):
        計算器 = _計算器(None)
        中間表現 = 計算中間表現("試験計算", ())
        作用 = HDS計算実行作用(計算器, 中間表現)
        初期 = HDS実行状態(要求状態=frozenset({"計算実行済み"}))
        結果 = HDS実行主体((作用,), 最大作用回数=3).実行(初期)
        self.assertEqual(結果.終端, HDS終端.保留)
        self.assertNotIn("計算実行済み", 結果.状態.成立状態)
        self.assertIn("計算結果未形成", 結果.状態.残差)


if __name__ == "__main__":
    unittest.main()

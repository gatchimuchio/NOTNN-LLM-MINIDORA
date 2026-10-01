from __future__ import annotations

import unittest

from minidora.HDS実行主体 import (
    HDS作用結果,
    HDS作用状態,
    HDS実行主体,
    HDS実行状態,
    HDS終端,
    HDS関数作用,
    HDS作用機会,
)
from minidora.統合駆動_v2.適応記憶 import HDS適応記憶
from minidora.コア.状態操作 import 状態差を受理


class HDS適応記憶試験(unittest.TestCase):
    def test_成功した状態差を同じ作用文脈の後続選択へ反映する(self):
        順序 = []
        動的 = HDS関数作用(
            "動的再取得",
            lambda 状態: (
                順序.append("動的再取得")
                or HDS作用結果(
                    HDS作用状態.成立,
                    追加状態=frozenset({"初回済み"}),
                    解消残差=frozenset({"観測不足"}),
                )
            ),
            機会判定=lambda 状態: "観測不足" in 状態.残差,
            解消対象=("観測不足",),
        )
        利用 = HDS関数作用(
            "資料利用",
            lambda 状態: (
                順序.append("資料利用")
                or HDS作用結果(
                    HDS作用状態.成立,
                    追加状態=frozenset({"利用済み"}),
                    追加残差=frozenset({"観測不足"}),
                )
            ),
            入力状態=("初回済み",),
            出力状態=("利用済み",),
        )
        ノイズ = HDS関数作用(
            "高優先度ノイズ",
            lambda 状態: (
                順序.append("高優先度ノイズ")
                or HDS作用結果(HDS作用状態.成立, 追加状態=frozenset({"ノイズ"}))
            ),
            入力状態=("利用済み",),
            出力状態=("ノイズ",),
            優先度=100.0,
        )
        初期 = HDS実行状態(
            要求状態=frozenset({"利用済み"}),
            残差=frozenset({"観測不足"}),
        )
        結果 = HDS実行主体((動的, 利用, ノイズ), 最大作用回数=6).実行(初期)
        self.assertEqual(結果.終端, HDS終端.採用)
        self.assertEqual(順序, ["動的再取得", "資料利用", "動的再取得"])

    def test_同一主体では実行を跨いで適応を継続する(self):
        順序 = []
        動的 = HDS関数作用(
            "動的再取得",
            lambda 状態: (
                順序.append("動的再取得")
                or HDS作用結果(HDS作用状態.成立, 追加状態=frozenset({"資料あり"}))
            ),
            機会判定=lambda 状態: "資料あり" not in 状態.成立状態,
            出力状態=("資料あり",),
        )
        ノイズ = HDS関数作用(
            "高優先度ノイズ",
            lambda 状態: (
                順序.append("高優先度ノイズ")
                or HDS作用結果(HDS作用状態.成立, 追加状態=frozenset({"ノイズ"}))
            ),
            入力状態=("利用済み",),
            出力状態=("ノイズ",),
            優先度=100.0,
        )
        主体 = HDS実行主体((動的, ノイズ), 最大作用回数=4)
        初期 = HDS実行状態(
            要求状態=frozenset({"資料あり"}),
            成立状態=frozenset({"利用済み"}),
        )
        self.assertEqual(主体.実行(初期).終端, HDS終端.採用)

        順序.clear()
        self.assertEqual(主体.実行(初期).終端, HDS終端.採用)
        self.assertEqual(順序[0], "動的再取得")
        self.assertGreaterEqual(主体.適応記憶.経験数, 2)

    def test_別適応記憶インスタンスへ経験を共有しない(self):
        機会 = HDS作用機会("作用A", "入力", 作用定義ID="定義A", 意味入力署名="意味A")
        前 = HDS実行状態()
        結果 = HDS作用結果(HDS作用状態.成立, 追加状態=frozenset({"成立"}))
        _, 差 = 状態差を受理(前, 結果)

        第一 = HDS適応記憶()
        第一.結果を受け取る(機会, 結果, 差, 前)
        self.assertFalse(第一.機会を補正(機会).期待.空)

        第二 = HDS適応記憶()
        self.assertTrue(第二.機会を補正(機会).期待.空)

    def test_失敗反証で同一文脈の旧期待を撤回する(self):
        機会 = HDS作用機会("作用A", "入力", 作用定義ID="定義A", 意味入力署名="意味A")
        前 = HDS実行状態()
        成功 = HDS作用結果(HDS作用状態.成立, 追加状態=frozenset({"成立"}))
        _, 成功差 = 状態差を受理(前, 成功)
        記憶 = HDS適応記憶()
        記憶.結果を受け取る(機会, 成功, 成功差, 前)
        self.assertFalse(記憶.機会を補正(機会).期待.空)

        失敗 = HDS作用結果(HDS作用状態.失敗)
        _, 失敗差 = 状態差を受理(前, 失敗)
        記憶.結果を受け取る(機会, 失敗, 失敗差, 前)
        self.assertTrue(記憶.機会を補正(機会).期待.空)


if __name__ == "__main__":
    unittest.main()

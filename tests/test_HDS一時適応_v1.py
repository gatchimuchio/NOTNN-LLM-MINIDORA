from __future__ import annotations

import unittest

from minidora.HDS実行主体 import (
    HDS作用結果,
    HDS作用状態,
    HDS実行主体,
    HDS実行状態,
    HDS終端,
    HDS関数作用,
)
from minidora.統合駆動_v2.一時適応 import HDS一時適応キャッシュ


class HDS一時適応試験(unittest.TestCase):
    def test_成功した状態差を同じ作用文脈の後続選択へ反映する(self):
        順序 = []

        動的 = HDS関数作用(
            "動的再取得",
            lambda 状態: (
                順序.append("動的再取得")
                or HDS作用結果(
                    HDS作用状態.成立,
                    追加状態=frozenset({"資料あり"}),
                )
            ),
            機会判定=lambda 状態: "資料あり" not in 状態.成立状態,
        )
        利用 = HDS関数作用(
            "資料利用",
            lambda 状態: (
                順序.append("資料利用")
                or HDS作用結果(
                    HDS作用状態.成立,
                    追加状態=frozenset({"利用済み"}),
                    削除状態=frozenset({"資料あり"}),
                )
            ),
            入力状態=("資料あり",),
            出力状態=("利用済み",),
        )
        ノイズ = HDS関数作用(
            "高優先度ノイズ",
            lambda 状態: (
                順序.append("高優先度ノイズ")
                or HDS作用結果(
                    HDS作用状態.成立,
                    追加状態=frozenset({"ノイズ"}),
                )
            ),
            入力状態=("利用済み",),
            出力状態=("ノイズ",),
            優先度=100.0,
        )
        初期 = HDS実行状態(要求状態=frozenset({"利用済み", "資料あり"}))
        結果 = HDS実行主体((動的, 利用, ノイズ), 最大作用回数=6).実行(初期)

        self.assertEqual(結果.終端, HDS終端.採用)
        self.assertEqual(順序, ["動的再取得", "資料利用", "動的再取得"])

    def test_実行を跨いで一時適応を蓄積しない(self):
        順序 = []

        動的 = HDS関数作用(
            "動的再取得",
            lambda 状態: (
                順序.append("動的再取得")
                or HDS作用結果(
                    HDS作用状態.成立,
                    追加状態=frozenset({"資料あり"}),
                )
            ),
            機会判定=lambda 状態: "資料あり" not in 状態.成立状態,
        )
        ノイズ = HDS関数作用(
            "高優先度ノイズ",
            lambda 状態: (
                順序.append("高優先度ノイズ")
                or HDS作用結果(
                    HDS作用状態.成立,
                    追加状態=frozenset({"ノイズ"}),
                )
            ),
            入力状態=("利用済み",),
            出力状態=("ノイズ",),
            優先度=100.0,
        )
        主体 = HDS実行主体((動的, ノイズ), 最大作用回数=4)

        第一 = HDS実行状態(
            要求状態=frozenset({"資料あり"}),
            成立状態=frozenset({"利用済み"}),
        )
        self.assertEqual(主体.実行(第一).終端, HDS終端.採用)

        順序.clear()
        第二 = HDS実行状態(
            要求状態=frozenset({"資料あり"}),
            成立状態=frozenset({"利用済み"}),
        )
        self.assertEqual(主体.実行(第二).終端, HDS終端.採用)
        self.assertEqual(順序[:2], ["高優先度ノイズ", "動的再取得"])

    def test_失敗と無変化を適応根拠にしない(self):
        class 機会:
            作用ID = "作用A"
            入力状態 = frozenset()
            出力状態 = frozenset()
            解消対象 = frozenset()
            読取認識 = ()
            読取成果 = ()
            種別 = "通常"
            契約版 = "v1"

        class 差:
            追加状態 = ("誤",)
            解消残差 = ("不足",)

        キャッシュ = HDS一時適応キャッシュ()
        差.変化有無 = True
        キャッシュ.結果を受け取る(
            機会(),
            HDS作用結果(HDS作用状態.失敗),
            差(),
        )
        差.変化有無 = False
        キャッシュ.結果を受け取る(
            機会(),
            HDS作用結果(HDS作用状態.成立),
            差(),
        )

        補正 = キャッシュ.機会を補正(機会())
        self.assertFalse(補正.出力状態)
        self.assertFalse(補正.解消対象)


if __name__ == "__main__":
    unittest.main()

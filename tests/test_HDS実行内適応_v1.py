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


class HDS実行内適応試験(unittest.TestCase):
    def _主体(self, 順序):
        def 学習対象実行(状態):
            順序.append("学習対象")
            if "段階2" in 状態.成立状態:
                return HDS作用結果(
                    HDS作用状態.成立,
                    追加状態=frozenset({"完了"}),
                    解消残差=frozenset({"不足"}),
                )
            return HDS作用結果(
                HDS作用状態.成立,
                追加状態=frozenset({"段階1"}),
                解消残差=frozenset({"不足"}),
            )

        学習対象 = HDS関数作用(
            "学習対象",
            学習対象実行,
            優先度=10.0,
            機会判定=lambda 状態: "段階1" not in 状態.成立状態 and "完了" not in 状態.成立状態,
        )
        切替 = HDS関数作用(
            "切替",
            lambda 状態: (
                順序.append("切替")
                or HDS作用結果(
                    HDS作用状態.成立,
                    追加状態=frozenset({"段階2"}),
                    削除状態=frozenset({"段階1"}),
                    追加残差=frozenset({"不足"}),
                )
            ),
            入力状態=("段階1",),
            出力状態=("段階2",),
            優先度=20.0,
        )
        ノイズ = HDS関数作用(
            "ノイズ",
            lambda 状態: (
                順序.append("ノイズ")
                or HDS作用結果(HDS作用状態.成立, 追加状態=frozenset({"ノイズ済み"}))
            ),
            優先度=100.0,
            機会判定=lambda 状態: "段階2" in 状態.成立状態 and "ノイズ済み" not in 状態.成立状態,
        )
        return HDS実行主体((学習対象, 切替, ノイズ), 最大作用回数=8)

    def test_同一実行内の経験から後続作用選択へ反映する(self):
        順序 = []
        主体 = self._主体(順序)
        初期 = HDS実行状態(
            要求状態=frozenset({"完了"}),
            残差=frozenset({"不足"}),
        )
        結果 = 主体.実行(初期)
        self.assertEqual(結果.終端, HDS終端.採用)
        self.assertEqual(順序[:3], ["学習対象", "切替", "学習対象"])
        self.assertNotIn("ノイズ", 順序)

    def test_実行終了後に経験を持ち越さない(self):
        順序 = []
        主体 = self._主体(順序)
        第一 = HDS実行状態(
            要求状態=frozenset({"完了"}),
            残差=frozenset({"不足"}),
        )
        self.assertEqual(主体.実行(第一).終端, HDS終端.採用)

        順序.clear()
        第二 = HDS実行状態(
            要求状態=frozenset({"完了"}),
            成立状態=frozenset({"段階2"}),
            残差=frozenset({"不足"}),
        )
        結果 = 主体.実行(第二)
        self.assertEqual(結果.終端, HDS終端.採用)
        self.assertEqual(順序[0], "ノイズ")
        self.assertNotIn("一時学習", repr(結果.状態))


if __name__ == "__main__":
    unittest.main()

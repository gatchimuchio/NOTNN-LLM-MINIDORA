from __future__ import annotations

import unittest

from minidora.規模測定 import 規模測定


class 規模測定試験(unittest.TestCase):
    def test_三つの規模面を別々に返す(self) -> None:
        結果 = 規模測定()
        self.assertIn("試験状態数", 結果.状態域規模)
        self.assertIn("模型関係実体数", 結果.関係域規模)
        self.assertIn("共有適用試験数", 結果.共有適用規模)
        self.assertIn(結果.大規模性状態, {"未成立", "局所成立候補"})

    def test_状態域は複数体系と長文履歴を実測する(self) -> None:
        結果 = 規模測定()
        self.assertEqual(結果.状態域規模["試験状態数"], 384)
        self.assertEqual(結果.状態域規模["識別内部状態数"], 384)
        self.assertEqual(結果.状態域規模["試験言語体系数"], 3)
        self.assertTrue(結果.状態域規模["一万文字状態受理"])
        self.assertTrue(結果.状態域規模["履歴深さ256受理"])

    def test_関係域は一般関係と構造差を実測する(self) -> None:
        結果 = 規模測定()
        関係 = 結果.関係域規模
        self.assertEqual(関係["意味対応済み関係族数"], 17)
        self.assertEqual(関係["関係構造生成試験数"], 544)
        self.assertEqual(関係["識別関係構造数"], 544)
        self.assertTrue(関係["方向差が成立差へ到達"])
        self.assertTrue(関係["肯否差が成立差へ到達"])
        self.assertTrue(関係["履歴順序差が成立差へ到達"])
        self.assertTrue(関係["条件結合差が成立差へ到達"])

    def test_共有適用は同一関係実体を多数状態へ再利用する(self) -> None:
        結果 = 規模測定()
        self.assertEqual(結果.共有適用規模["共有適用試験数"], 256)
        self.assertEqual(結果.共有適用規模["同一関係群での成功数"], 256)
        self.assertTrue(結果.共有適用規模["関係実体再利用"])

    def test_一点閾値で大規模判定しない(self) -> None:
        結果 = 規模測定()
        reason = " ".join(結果.理由)
        self.assertIn("一点閾値", reason)
        self.assertIn("現代LLM参照群", " ".join(結果.比較集合))

    def test_三面が揃った時だけ局所成立候補とする(self) -> None:
        結果 = 規模測定()
        self.assertEqual(結果.大規模性状態, "局所成立候補")
        self.assertIn("物理規模同等を主張しない", " ".join(結果.理由))


if __name__ == "__main__":
    unittest.main()

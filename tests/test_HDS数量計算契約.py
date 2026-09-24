from __future__ import annotations

import unittest

from minidora.HDS構文化器_v1 import 公開HDSコンパイラ


class HDS数量計算契約試験(unittest.TestCase):
    def setUp(self) -> None:
        self.構文化器 = 公開HDSコンパイラ()

    def test_明示算術は実行可能として固定する(self) -> None:
        束 = self.構文化器.コンパイル束("2+3")
        self.assertEqual(束.数量計算契約.状態, "実行可能")
        self.assertTrue(束.数量計算契約.計算P実行可能)
        self.assertEqual([x.値 for x in 束.数量計算契約.問い数量], ["2", "3"])

    def test_数量候補があって法則が無ければ法則不足を保持する(self) -> None:
        束 = self.構文化器.問題コンパイル束(
            "A state has lifetime 1e-9 s. Which energy difference is resolvable?",
            ("1e-9 eV", "1e-6 eV", "1e-3 eV", "1 eV"),
        )
        契約 = 束.数量計算契約
        self.assertEqual(契約.状態, "法則不足")
        self.assertFalse(契約.計算P実行可能)
        self.assertIn("計算法則未形成", 契約.不足)
        self.assertTrue(any(x.値 == "1e-9" and "s" in x.単位 for x in 契約.問い数量))
        self.assertEqual(set(契約.候補被覆ラベル), set("ABCD"))

    def test_非数量問題は非数量のままにする(self) -> None:
        束 = self.構文化器.問題コンパイル束(
            "Which molecule inhibits Enzyme X?",
            ("Protein A", "Protein B", "Protein C", "Protein D"),
        )
        self.assertEqual(束.数量計算契約.状態, "非数量")
        self.assertFalse(束.数量計算契約.数量問題)


if __name__ == "__main__":
    unittest.main()

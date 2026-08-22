from __future__ import annotations

import unittest

from minidora.semantic_tokens import 意味語


class 意味語正規化試験(unittest.TestCase):
    def test_単純な英語屈折差を同一語へ寄せる(self) -> None:
        self.assertEqual(意味語("uses"), 意味語("use"))
        self.assertEqual(意味語("engines"), 意味語("engine"))
        self.assertEqual(意味語("studies"), 意味語("study"))
        self.assertEqual(意味語("processes"), 意味語("process"))
        self.assertEqual(意味語("running"), 意味語("run"))

    def test_機能語を意味照合へ混入しない(self) -> None:
        self.assertEqual(意味語("the engine of the system"), frozenset({"engine", "system"}))

    def test_日本語意味語は保持する(self) -> None:
        self.assertEqual(意味語("触媒 反応 促進"), frozenset({"触媒", "反応", "促進"}))

    def test_1桁数値choiceを保持する(self) -> None:
        self.assertIn("0", 意味語("0"))
        self.assertIn("6", 意味語("6"))
        self.assertEqual(意味語("x"), frozenset())

    def test_符号付き数値を区別する(self) -> None:
        self.assertIn("-1", 意味語("-1"))
        self.assertIn("+1", 意味語("+1"))
        self.assertNotEqual(意味語("-1"), 意味語("+1"))

    def test_分数と指数を数式anchorとして保持する(self) -> None:
        self.assertIn("math:1/3", 意味語("1/3"))
        self.assertIn("math:10^-16", 意味語("10^-16 J"))


if __name__ == "__main__":
    unittest.main()

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

    def test_選択QA制御語を意味証拠へ混入せず派生関係語は正規化する(self) -> None:
        terms = 意味語("Which of the following statements is most likely correct regarding catalytic inhibition?")
        self.assertEqual(terms, frozenset({"catalytic", "inhibit", "rel:阻害"}))

    def test_モーダルと回答操作語を落として対象語は保持する(self) -> None:
        terms = 意味語("Select the best answer that could describe protein transport")
        self.assertEqual(terms, frozenset({"protein", "transport"}))

    def test_日本語意味語は保持する(self) -> None:
        self.assertEqual(意味語("触媒 反応 促進"), frozenset({"触媒", "反応", "促進"}))

    def test_1桁数値と単独choice_atomを保持する(self) -> None:
        self.assertIn("0", 意味語("0"))
        self.assertIn("6", 意味語("6"))
        self.assertIn("atom:x", 意味語("x"))
        self.assertIn("atom:b", 意味語("b"))
        self.assertIn("atom:c", 意味語("c) option"))

    def test_符号付き数値を区別する(self) -> None:
        self.assertIn("-1", 意味語("-1"))
        self.assertIn("+1", 意味語("+1"))
        self.assertNotEqual(意味語("-1"), 意味語("+1"))

    def test_分数指数科学記数法を数式anchorとして保持する(self) -> None:
        self.assertIn("math:1/3", 意味語("1/3"))
        self.assertIn("math:10^-16", 意味語("10^-16 J"))
        self.assertIn("math:2.6*1e5", 意味語("2.6*1e5 GeV"))
        self.assertIn("math:1/3", 意味語(r"\frac{1}{3}"))
        self.assertIn("math:sqrt(2)", 意味語(r"\sqrt{2}"))

    def test_技術記号を通常語と別anchorで保持する(self) -> None:
        self.assertIn("sym:e", 意味語("E = 2*x"))
        self.assertIn("sym:x", 意味語("E = 2*x"))
        self.assertIn("sym:θ", 意味語("θ"))


if __name__ == "__main__":
    unittest.main()

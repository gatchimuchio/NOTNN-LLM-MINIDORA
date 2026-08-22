from __future__ import annotations

import unittest

from minidora.choice_intent import HDS選択意図判定


class HDS選択意図試験(unittest.TestCase):
    def test_exceptを例外選択として判定する(self) -> None:
        result = HDS選択意図判定("All statements are correct except which one?")
        self.assertEqual(result.種別, "EXCEPTION")

    def test_incorrectとnot_trueを例外選択として判定する(self) -> None:
        self.assertEqual(HDS選択意図判定("Which statement is incorrect?").種別, "EXCEPTION")
        self.assertEqual(HDS選択意図判定("Which statement is not true?").種別, "EXCEPTION")

    def test_least_likely系を例外選択として判定する(self) -> None:
        self.assertEqual(
            HDS選択意図判定("Which mechanism is least likely to explain the observation?").種別,
            "EXCEPTION",
        )
        self.assertEqual(
            HDS選択意図判定("Which option is least consistent with the evidence?").種別,
            "EXCEPTION",
        )
        self.assertEqual(
            HDS選択意図判定("Which outcome is most unlikely under this condition?").種別,
            "EXCEPTION",
        )

    def test_日本語の該当しないと可能性が低いを例外選択として判定する(self) -> None:
        self.assertEqual(HDS選択意図判定("次のうち該当しないものはどれか？").種別, "EXCEPTION")
        self.assertEqual(HDS選択意図判定("次のうち最も可能性が低いものはどれか？").種別, "EXCEPTION")

    def test_背景中のnotだけでは例外選択にしない(self) -> None:
        text = (
            "The first experiment did not converge. The second experiment produced stable evidence. "
            "Which mechanism best explains the final observation?"
        )
        self.assertEqual(HDS選択意図判定(text).種別, "POSITIVE")

    def test_直前背景のfalse_positiveも最終質問へ伝染しない(self) -> None:
        text = (
            "The preliminary assay produced a false positive. "
            "Which mechanism best explains the confirmed observation?"
        )
        self.assertEqual(HDS選択意図判定(text).種別, "POSITIVE")

    def test_単なるsmallestやminimumは例外扱いしない(self) -> None:
        self.assertEqual(HDS選択意図判定("Which value is the smallest?").種別, "POSITIVE")
        self.assertEqual(HDS選択意図判定("Which energy is minimum at equilibrium?").種別, "POSITIVE")

    def test_通常のwhich問題はpositiveのまま(self) -> None:
        self.assertEqual(HDS選択意図判定("Which process is active in the cell?").種別, "POSITIVE")


if __name__ == "__main__":
    unittest.main()

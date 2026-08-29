from __future__ import annotations

import unittest

from minidora.hds_choice_runtime import HDS選択実行結果
from minidora.hds適応候補調停 import HDS適応候補調停


def _result(
    state: str,
    label: str | None,
    content: str | None,
    *,
    cross_updates: int = 0,
    reason: str = "TEST",
) -> HDS選択実行結果:
    return HDS選択実行結果(
        state,
        label,
        content,
        (reason,),
        None,
        2,
        1,
        0,
        0,
        0,
        0,
        候補横断更新数=cross_updates,
    )


class HDS適応候補調停試験(unittest.TestCase):
    def test_二段候補横断更新が成立した能力提案を優先する(self) -> None:
        primary = _result("PROPOSE", "A", "能力", cross_updates=1, reason="PRIMARY")
        base = _result("APPROVE", "B", "基礎", reason="BASE")

        selected = HDS適応候補調停(primary, base)

        self.assertEqual(selected.状態, "PROPOSE")
        self.assertEqual(selected.回答ラベル, "A")
        self.assertIn("SECOND_ORDER_STATE_DIFFERENCE_SUPPORTED", selected.理由)
        self.assertNotIn("HDS_ADAPTIVE_BASE_SELECTED", selected.理由)

    def test_二段差分が無ければ閉じた基礎経路を提案へ落とす(self) -> None:
        primary = _result("PROPOSE", "A", "能力", cross_updates=0, reason="PRIMARY")
        base = _result("APPROVE", "B", "基礎", reason="BASE")

        selected = HDS適応候補調停(primary, base)

        self.assertEqual(selected.状態, "PROPOSE")
        self.assertEqual(selected.回答ラベル, "B")
        self.assertIn("HDS_ADAPTIVE_BASE_SELECTED", selected.理由)
        self.assertIn("CANDIDATE_GENERATION_HAS_NO_COMMIT_AUTHORITY", selected.理由)

    def test_二段差分も基礎閉包も無ければ単独primaryを救済しない(self) -> None:
        primary = _result("PROPOSE", "A", "能力", cross_updates=0, reason="PRIMARY")
        base = _result("SUSPEND", None, None, reason="BASE_SUSPEND")

        selected = HDS適応候補調停(primary, base)

        self.assertEqual(selected.状態, "SUSPEND")
        self.assertIsNone(selected.回答ラベル)
        self.assertIsNone(selected.回答内容)
        self.assertIn("PRIMARY_WITHOUT_SECOND_ORDER_SUPPORT_NOT_COMMITTED", selected.理由)

    def test_能力経路がSUSPENDでも基礎閉包は提案として残す(self) -> None:
        primary = _result("SUSPEND", None, None, reason="PRIMARY_SUSPEND")
        base = _result("APPROVE", "C", "基礎", reason="BASE")

        selected = HDS適応候補調停(primary, base)

        self.assertEqual(selected.状態, "PROPOSE")
        self.assertEqual(selected.回答ラベル, "C")


if __name__ == "__main__":
    unittest.main()

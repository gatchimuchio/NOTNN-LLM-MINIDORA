from __future__ import annotations

import unittest

from minidora.hds_compiler import 公開HDSコンパイラ
from minidora.hds_ir import 値状態
from minidora.hds_reference import HDS参照問合せ候補


class HDS不足スロット試験(unittest.TestCase):
    def setUp(self) -> None:
        self.compiler = 公開HDSコンパイラ()

    def test_英語未知始点を候補へ置換したR_queryにする(self) -> None:
        ir = self.compiler.問題IR(
            "Which molecule causes apoptosis under hypoxia?",
            ("Protein A", "Protein B", "Protein C", "Protein D"),
        )
        unknown = [c for c in ir.座標 if c.種別 == "目的.未知始点"]
        self.assertEqual(len(unknown), 1)
        self.assertEqual(unknown[0].値状態, 値状態.未観測)
        self.assertEqual(str(unknown[0].内容).casefold(), "molecule")
        relation = next(r for r in ir.関係 if r.種別 == "因果" and r.値状態 == 値状態.未観測)
        self.assertIn("不足位置=始点", relation.条件)
        queries = tuple(q.casefold() for q in HDS参照問合せ候補(ir))
        for choice in ("protein a", "protein b", "protein c", "protein d"):
            self.assertIn(f"{choice} causes apoptosis under hypoxia", queries)

    def test_英語未知終点を候補へ置換する(self) -> None:
        ir = self.compiler.問題IR(
            "Protein A inhibits which pathway under hypoxia?",
            ("glycolysis", "apoptosis", "translation", "transport"),
        )
        unknown = [c for c in ir.座標 if c.種別 == "目的.未知終点"]
        self.assertEqual(len(unknown), 1)
        self.assertEqual(str(unknown[0].内容).casefold(), "pathway")
        queries = tuple(q.casefold() for q in HDS参照問合せ候補(ir))
        self.assertIn("protein a inhibits glycolysis under hypoxia", queries)

    def test_受動態でも意味方向に沿って未知終点を作る(self) -> None:
        ir = self.compiler.問題IR(
            "Which disease is caused by Protein A?",
            ("Disease A", "Disease B", "Disease C", "Disease D"),
        )
        relation = next(r for r in ir.関係 if r.種別 == "因果")
        coords = ir.座標辞書()
        self.assertEqual(str(coords[relation.始点[0]].内容), "Protein A")
        self.assertEqual(coords[relation.終点[0]].種別, "目的.未知終点")
        queries = tuple(q.casefold() for q in HDS参照問合せ候補(ir))
        self.assertIn("protein a causes disease a", queries)

    def test_日本語未知始点も同じ意味構造へ落とす(self) -> None:
        ir = self.compiler.問題IR(
            "どのタンパク質がアポトーシスを引き起こす？",
            ("タンパク質A", "タンパク質B", "タンパク質C", "タンパク質D"),
        )
        unknown = [c for c in ir.座標 if c.種別 == "目的.未知始点"]
        self.assertEqual(len(unknown), 1)
        self.assertEqual(str(unknown[0].内容), "タンパク質")
        queries = HDS参照問合せ候補(ir)
        self.assertIn("タンパク質A 引き起こす アポトーシス", queries)

    def test_関係が確定しない疑問文へ不足スロットを捏造しない(self) -> None:
        ir = self.compiler.問題IR(
            "Which of the following statements is correct under hypoxia?",
            ("A statement", "B statement", "C statement", "D statement"),
        )
        self.assertFalse(any(c.種別.startswith("目的.未知") for c in ir.座標))
        self.assertFalse(any("不足位置=" in cond for r in ir.関係 for cond in r.条件))

    def test_選択極性は外部検索語へ漏らさない(self) -> None:
        ir = self.compiler.問題IR(
            "Which molecule is least likely to cause apoptosis under hypoxia?",
            ("Protein A", "Protein B", "Protein C", "Protein D"),
        )
        queries = tuple(q.casefold() for q in HDS参照問合せ候補(ir))
        self.assertFalse(any("least likely" in q for q in queries if "protein " in q))
        self.assertFalse(any("始点" in q or "終点" in q for q in queries))


if __name__ == "__main__":
    unittest.main()

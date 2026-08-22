from __future__ import annotations

import unittest

from minidora.hds_ir import HDSIR, HDS実行核, HDS座標, 値状態
from minidora.hds_reference import HDS参照問合せ候補


def _ir() -> HDSIR:
    return HDSIR(
        原文="Which process is active for ProteinX under hypoxia?",
        正規化文="Which process is active for ProteinX under hypoxia?",
        認知世界ID="reference-role-test",
        座標=(
            HDS座標("protein", "対象.実体", "ProteinX"),
            HDS座標("process", "関係.述語表層", "activates"),
            HDS座標("state", "状態.環境", "hypoxia"),
            HDS座標("time", "文脈.時点", "acute phase"),
            HDS座標("uncertain", "条件.未解", "mouse only", 値状態=値状態.未確定),
            HDS座標("choice:A", "目的.候補", "catalysis"),
            HDS座標("choice:B", "目的.候補", "transport"),
            HDS座標("choice:C", "目的.候補", "folding"),
            HDS座標("choice:D", "目的.候補", "signaling"),
        ),
        関係=(),
        残差=(),
        意味作用履歴=(),
        実行核=HDS実行核("参照回答"),
        参照必須=True,
        種別="knowledge_query",
        閉包状態="CLOSED_FOR_OPERATION",
        入力言語="en",
    )


def _formula_ir() -> HDSIR:
    common = "The mass dimension of kappa is"
    return HDSIR(
        原文="What is the mass dimension of kappa and is the theory renormalizable?",
        正規化文="What is the mass dimension of kappa and is the theory renormalizable?",
        認知世界ID="reference-formula-test",
        座標=(
            HDS座標("subject", "対象.実体", "kappa interaction operator"),
            HDS座標("choice:A", "目的.候補", f"{common} -1 and the theory is renormalizable"),
            HDS座標("choice:B", "目的.候補", f"{common} -1 and the theory is not renormalizable"),
            HDS座標("choice:C", "目的.候補", f"{common} 1 and the theory is renormalizable"),
            HDS座標("choice:D", "目的.候補", f"{common} 1 and the theory is not renormalizable"),
        ),
        関係=(),
        残差=(),
        意味作用履歴=(),
        実行核=HDS実行核("参照回答"),
        参照必須=True,
        種別="knowledge_query",
        閉包状態="CLOSED_FOR_OPERATION",
        入力言語="en",
    )


class HDS参照役割Query試験(unittest.TestCase):
    def test_HDS役割順で構造queryを形成する(self) -> None:
        queries = HDS参照問合せ候補(_ir())
        structural = next(
            q for q in queries
            if "ProteinX" in q and "activates" in q and "hypoxia" in q and "acute phase" in q
        )
        self.assertLess(structural.index("ProteinX"), structural.index("activates"))
        self.assertLess(structural.index("activates"), structural.index("hypoxia"))
        self.assertNotIn("mouse only", structural)

    def test_4択query枠を全候補へ対称に予約する(self) -> None:
        queries = HDS参照問合せ候補(_ir(), 最大候補数=4)
        self.assertEqual(len(queries), 4)
        for choice in ("catalysis", "transport", "folding", "signaling"):
            self.assertEqual(sum(choice in q for q in queries), 1)
        self.assertTrue(all("ProteinX" in q for q in queries))

    def test_既定6枠では表面構造と4候補を共存させる(self) -> None:
        queries = HDS参照問合せ候補(_ir())
        self.assertEqual(len(queries), 6)
        self.assertEqual(sum("catalysis" in q for q in queries), 1)
        self.assertEqual(sum("transport" in q for q in queries), 1)
        self.assertEqual(sum("folding" in q for q in queries), 1)
        self.assertEqual(sum("signaling" in q for q in queries), 1)

    def test_長文choiceは共通文より差分語を検索へ残す(self) -> None:
        queries = HDS参照問合せ候補(_formula_ir(), 最大候補数=4)
        self.assertEqual(len(queries), 4)
        self.assertTrue(any("-1" in q for q in queries))
        self.assertTrue(any("not" in q for q in queries))
        self.assertTrue(all(len(q) <= 360 for q in queries))
        self.assertFalse(any("The mass dimension of kappa is The mass dimension" in q for q in queries))

    def test_数値だけが違うchoiceでも差分を失わない(self) -> None:
        ir = HDSIR(
            原文="How many loops?",
            正規化文="How many loops?",
            認知世界ID="reference-number-test",
            座標=(
                HDS座標("subject", "対象.実体", "loop diagram"),
                HDS座標("choice:A", "目的.候補", "1"),
                HDS座標("choice:B", "目的.候補", "2"),
                HDS座標("choice:C", "目的.候補", "3"),
                HDS座標("choice:D", "目的.候補", "6"),
            ),
            関係=(), 残差=(), 意味作用履歴=(), 実行核=HDS実行核("参照回答"),
            参照必須=True, 種別="knowledge_query", 閉包状態="CLOSED_FOR_OPERATION", 入力言語="en",
        )
        queries = HDS参照問合せ候補(ir, 最大候補数=4)
        for number in ("1", "2", "3", "6"):
            self.assertEqual(sum(number in q.split() for q in queries), 1)

    def test_長文queryは冒頭文脈と末尾焦点を同時に保持する(self) -> None:
        filler = " ".join(f"context{i}" for i in range(120))
        text = f"AlphaProtein {filler} final_focus_marker"
        ir = HDSIR(
            原文=text,
            正規化文=text,
            認知世界ID="reference-long-context-test",
            座標=(
                HDS座標("choice:A", "目的.候補", "red"),
                HDS座標("choice:B", "目的.候補", "blue"),
            ),
            関係=(), 残差=(), 意味作用履歴=(), 実行核=HDS実行核("参照回答"),
            参照必須=True, 種別="knowledge_query", 閉包状態="CLOSED_FOR_OPERATION", 入力言語="en",
        )
        queries = HDS参照問合せ候補(ir)
        self.assertTrue(any("AlphaProtein" in q and "final_focus_marker" in q for q in queries))


if __name__ == "__main__":
    unittest.main()

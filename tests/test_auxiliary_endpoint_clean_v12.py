from __future__ import annotations

import unittest

from minidora import 公開HDSコンパイラ


def _条件値(relation, key: str) -> str:
    prefix = key + "="
    for raw in relation.条件:
        value = str(raw)
        if value.startswith(prefix):
            return value[len(prefix):].strip()
    return ""


def _edge(ir, kind: str, start: str, end: str):
    coords = ir.座標辞書()
    rows = [
        r for r in ir.関係
        if str(r.種別) == kind
        and any(str(coords[cid].内容) == start for cid in r.始点 if cid in coords)
        and any(str(coords[cid].内容) == end for cid in r.終点 if cid in coords)
    ]
    if len(rows) != 1:
        raise AssertionError(f"expected one {start} --{kind}→ {end}, got {len(rows)}")
    return rows[0]


class 補助語端点CleanV12試験(unittest.TestCase):
    def setUp(self) -> None:
        self.compiler = 公開HDSコンパイラ()

    def test_be進行を実体端点と相へ分離する(self) -> None:
        ir = self.compiler.コンパイル("Protein A is generating Molecule B.")
        rel = _edge(ir, "生成", "Protein A", "Molecule B")
        self.assertEqual(_条件値(rel, "相"), "進行")
        self.assertEqual(_条件値(rel, "時制"), "現在")
        self.assertFalse(any(str(c.種別) == "対象.始点" and str(c.内容) == "Protein A is" for c in ir.座標))

    def test_have完了を実体端点と相へ分離する(self) -> None:
        ir = self.compiler.コンパイル("Protein A has generated Molecule B.")
        rel = _edge(ir, "生成", "Protein A", "Molecule B")
        self.assertEqual(_条件値(rel, "相"), "完了")
        self.assertEqual(_条件値(rel, "時制"), "現在")

    def test_had完了は過去を保持する(self) -> None:
        ir = self.compiler.コンパイル("Protein A had generated Molecule B.")
        rel = _edge(ir, "生成", "Protein A", "Molecule B")
        self.assertEqual(_条件値(rel, "相"), "完了")
        self.assertEqual(_条件値(rel, "時制"), "過去")

    def test_完了進行も端点へ混ぜない(self) -> None:
        ir = self.compiler.コンパイル("Protein A has been generating Molecule B.")
        rel = _edge(ir, "生成", "Protein A", "Molecule B")
        self.assertEqual(_条件値(rel, "相"), "完了進行")

    def test_do強調を端点へ混ぜない(self) -> None:
        ir = self.compiler.コンパイル("Protein A did generate Molecule B.")
        rel = _edge(ir, "生成", "Protein A", "Molecule B")
        self.assertEqual(_条件値(rel, "強調"), "do")
        self.assertEqual(_条件値(rel, "時制"), "過去")

    def test_is_associated_withのA_is偽関係を残さない(self) -> None:
        ir = self.compiler.コンパイル("Protein A is associated with Protein B.")
        rel = _edge(ir, "相関", "Protein A", "Protein B")
        coords = ir.座標辞書()
        self.assertFalse(
            any(
                str(r.種別) == "相関"
                and any(str(coords[cid].内容) == "Protein A is" for cid in r.始点 if cid in coords)
                for r in ir.関係
            )
        )

    def test_既存受動態の意味方向を壊さない(self) -> None:
        ir = self.compiler.コンパイル("Protein A was inhibited by Protein B.")
        _edge(ir, "阻害", "Protein B", "Protein A")


if __name__ == "__main__":
    unittest.main()

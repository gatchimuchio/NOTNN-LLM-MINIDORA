from __future__ import annotations

import unittest

from minidora import 公開HDSコンパイラ
from minidora.hds_reference import HDS参照問合せ候補


def _条件値(relation, key: str) -> str:
    prefix = key + "="
    for raw in relation.条件:
        value = str(raw)
        if value.startswith(prefix):
            return value[len(prefix):].strip()
    return ""


def _比較関係(ir, kind: str):
    rows = [
        relation for relation in ir.関係
        if str(relation.種別) == kind and str(relation.由来) == "共有言語基底P"
    ]
    if len(rows) != 1:
        raise AssertionError(f"expected one comparison relation {kind}, got {len(rows)}")
    return rows[0]


class 自然言語比較V07試験(unittest.TestCase):
    def setUp(self) -> None:
        self.compiler = 公開HDSコンパイラ()

    def test_greater_thanを比較大へ射影する(self) -> None:
        ir = self.compiler.コンパイル("Energy A is greater than Energy B.")
        relation = _比較関係(ir, "比較.大")
        coords = ir.座標辞書()
        self.assertEqual(coords[relation.始点[0]].内容, "Energy A")
        self.assertEqual(coords[relation.終点[0]].内容, "Energy B")
        self.assertEqual(_条件値(relation, "検索述語"), "greater than")
        self.assertEqual(_条件値(relation, "比較"), "")

    def test_lower_thanを比較小へ射影する(self) -> None:
        ir = self.compiler.コンパイル("Rate A is lower than Rate B.")
        relation = _比較関係(ir, "比較.小")
        coords = ir.座標辞書()
        self.assertEqual(coords[relation.始点[0]].内容, "Rate A")
        self.assertEqual(coords[relation.終点[0]].内容, "Rate B")

    def test_at_leastとat_mostを別関係へする(self) -> None:
        ge = _比較関係(self.compiler.コンパイル("Value A is at least Value B."), "比較.以上")
        le = _比較関係(self.compiler.コンパイル("Value A is at most Value B."), "比較.以下")
        self.assertEqual(_条件値(ge, "検索述語"), "at least")
        self.assertEqual(_条件値(le, "検索述語"), "at most")

    def test_equal_and_differentを関係化する(self) -> None:
        eq = _比較関係(self.compiler.コンパイル("State A is equal to State B."), "等価")
        ne = _比較関係(self.compiler.コンパイル("State A is different from State B."), "不同")
        self.assertEqual(_条件値(eq, "検索述語"), "equal to")
        self.assertEqual(_条件値(ne, "検索述語"), "different from")

    def test_比較質問を未知始点へ落とす(self) -> None:
        ir = self.compiler.コンパイル("Which quantity is greater than threshold X?")
        relation = _比較関係(ir, "比較.大")
        coords = ir.座標辞書()
        self.assertEqual(_条件値(relation, "不足位置"), "始点")
        self.assertEqual(coords[relation.始点[0]].種別, "目的.未知始点")
        self.assertEqual(coords[relation.始点[0]].内容, "quantity")
        self.assertEqual(coords[relation.終点[0]].内容, "threshold X")

    def test_比較質問の候補queryを関係方向付きで生成する(self) -> None:
        ir = self.compiler.問題IR(
            "Which quantity is greater than threshold X?",
            ("Value A", "Value B", "Value C", "Value D"),
        )
        queries = tuple(q.casefold() for q in HDS参照問合せ候補(ir))
        for candidate in ("value a", "value b", "value c", "value d"):
            self.assertTrue(any(candidate in q and "greater than" in q and "threshold x" in q for q in queries), queries)

    def test_単なる比較語を世界知識へ昇格しない(self) -> None:
        ir = self.compiler.コンパイル("The greater problem remains unresolved.")
        comparison = [relation for relation in ir.関係 if str(relation.種別).startswith("比較.") and str(relation.由来) == "共有言語基底P"]
        self.assertEqual(comparison, [])


if __name__ == "__main__":
    unittest.main()

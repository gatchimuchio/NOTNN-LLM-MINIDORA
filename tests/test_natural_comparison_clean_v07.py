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


def _関係(ir, kind: str):
    rows = [r for r in ir.関係 if str(r.種別) == kind and str(r.由来) == "共有言語基底P"]
    if len(rows) != 1:
        raise AssertionError(f"expected one {kind}, got {len(rows)}")
    return rows[0]


class 自然言語比較CleanV07試験(unittest.TestCase):
    def setUp(self) -> None:
        self.compiler = 公開HDSコンパイラ()

    def test_greater_thanを比較大へ落とす(self) -> None:
        ir = self.compiler.コンパイル("Energy A is greater than Energy B.")
        rel = _関係(ir, "比較.大")
        coords = ir.座標辞書()
        self.assertEqual(coords[rel.始点[0]].内容, "Energy A")
        self.assertEqual(coords[rel.終点[0]].内容, "Energy B")
        self.assertEqual(_条件値(rel, "検索述語"), "greater than")

    def test_equal_differentを分ける(self) -> None:
        self.assertEqual(_条件値(_関係(self.compiler.コンパイル("A is equal to B."), "等価"), "検索述語"), "equal to")
        self.assertEqual(_条件値(_関係(self.compiler.コンパイル("A is different from B."), "不同"), "検索述語"), "different from")

    def test_equals動詞も等価へ落とす(self) -> None:
        self.assertEqual(_関係(self.compiler.コンパイル("Expression A equals Expression B."), "等価").種別, "等価")

    def test_比較質問を未知始点へ落とす(self) -> None:
        ir = self.compiler.コンパイル("Which quantity is greater than threshold X?")
        rel = _関係(ir, "比較.大")
        coords = ir.座標辞書()
        self.assertEqual(_条件値(rel, "不足位置"), "始点")
        self.assertEqual(coords[rel.始点[0]].内容, "quantity")
        self.assertEqual(coords[rel.終点[0]].内容, "threshold X")

    def test_what_does_equalを未知終点へ落とす(self) -> None:
        ir = self.compiler.コンパイル("What does Expression A equal?")
        rel = _関係(ir, "等価")
        self.assertEqual(_条件値(rel, "不足位置"), "終点")
        self.assertEqual(ir.座標辞書()[rel.始点[0]].内容, "Expression A")

    def test_候補queryへ比較関係を復号する(self) -> None:
        ir = self.compiler.問題IR(
            "Which quantity is greater than threshold X?",
            ("Value A", "Value B", "Value C", "Value D"),
        )
        queries = tuple(q.casefold() for q in HDS参照問合せ候補(ir))
        for candidate in ("value a", "value b", "value c", "value d"):
            self.assertTrue(any(candidate in q and "greater than" in q and "threshold x" in q for q in queries), queries)

    def test_単なるgreaterは比較関係にしない(self) -> None:
        ir = self.compiler.コンパイル("The greater problem remains unresolved.")
        self.assertFalse(any(str(r.種別).startswith("比較.") and str(r.由来) == "共有言語基底P" for r in ir.関係))


if __name__ == "__main__":
    unittest.main()

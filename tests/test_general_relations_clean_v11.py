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


class 一般関係CleanV11試験(unittest.TestCase):
    def setUp(self) -> None:
        self.compiler = 公開HDSコンパイラ()

    def _edge(self, text: str, kind: str, start: str, end: str) -> None:
        ir = self.compiler.コンパイル(text)
        rel = _関係(ir, kind)
        coords = ir.座標辞書()
        self.assertEqual(coords[rel.始点[0]].内容, start)
        self.assertEqual(coords[rel.終点[0]].内容, end)

    def test_bind_toを結合へ落とす(self) -> None:
        self._edge("Protein A binds to Protein B.", "結合", "Protein A", "Protein B")

    def test_interact_withを相互作用へ落とす(self) -> None:
        self._edge("Protein A interacts with Protein B.", "相互作用", "Protein A", "Protein B")

    def test_consist_ofとcomposed_ofを構成へ落とす(self) -> None:
        self._edge("Complex A consists of Subunit B.", "構成", "Complex A", "Subunit B")
        self._edge("Complex A is composed of Subunit B.", "構成", "Complex A", "Subunit B")

    def test_belong_locate_deriveを別関係へ落とす(self) -> None:
        self._edge("Entity A belongs to Group B.", "所属", "Entity A", "Group B")
        self._edge("Entity A is located in Region B.", "位置", "Entity A", "Region B")
        self._edge("Entity A is derived from Source B.", "由来", "Entity A", "Source B")

    def test_is_derived_fromでA_is偽始点を作らない(self) -> None:
        ir = self.compiler.コンパイル("Entity A is derived from Source B.")
        derived = [r for r in ir.関係 if str(r.種別) == "由来" and str(r.由来) == "共有言語基底P"]
        self.assertEqual(len(derived), 1)
        coords = ir.座標辞書()
        self.assertNotEqual(str(coords[derived[0].始点[0]].内容).casefold(), "entity a is")

    def test_interact質問を未知始点へ落とす(self) -> None:
        ir = self.compiler.コンパイル("Which protein interacts with receptor X?")
        rel = next(r for r in ir.関係 if str(r.種別) == "相互作用" and _条件値(r, "不足位置") == "始点")
        coords = ir.座標辞書()
        self.assertEqual(coords[rel.始点[0]].内容, "protein")
        self.assertEqual(coords[rel.終点[0]].内容, "receptor X")
        self.assertEqual(_条件値(rel, "検索述語"), "interact with")

    def test_consist_of質問を未知始点へ落とす(self) -> None:
        ir = self.compiler.コンパイル("Which structure consists of component X?")
        rel = next(r for r in ir.関係 if str(r.種別) == "構成" and _条件値(r, "不足位置") == "始点")
        self.assertEqual(_条件値(rel, "検索述語"), "consist of")

    def test_R_queryも新関係を英語へ戻す(self) -> None:
        ir = self.compiler.問題IR(
            "Which protein interacts with receptor X?",
            ("Protein A", "Protein B", "Protein C", "Protein D"),
        )
        queries = tuple(q.casefold() for q in HDS参照問合せ候補(ir))
        self.assertTrue(any("protein a" in q and "interact with" in q and "receptor x" in q for q in queries), queries)


if __name__ == "__main__":
    unittest.main()

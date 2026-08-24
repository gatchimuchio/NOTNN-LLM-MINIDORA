from __future__ import annotations

import unittest

from minidora import 公開HDSコンパイラ
from minidora.hds_runtime_projection import HDSKData射影


def _条件値(relation, key: str) -> str:
    prefix = key + "="
    for raw in relation.条件:
        value = str(raw)
        if value.startswith(prefix):
            return value[len(prefix):].strip()
    return ""


def _阻害関係(ir):
    rows = [relation for relation in ir.関係 if str(relation.種別) == "阻害"]
    if not rows:
        raise AssertionError("阻害関係が存在しない")
    return next((r for r in rows if _条件値(r, "scope結合") == "Compiler"), rows[0])


def _K内容(ir) -> tuple[str, ...]:
    return tuple(str(coord.内容) for coord in HDSKData射影(ir).座標)


class HDS英語RelationScope試験(unittest.TestCase):
    def setUp(self) -> None:
        self.compiler = 公開HDSコンパイラ()

    def test_does_notを実体端点と否定scopeへ分離する(self) -> None:
        ir = self.compiler.コンパイル("Compound A does not inhibit Enzyme X.")
        relation = _阻害関係(ir)
        coords = ir.座標辞書()
        self.assertEqual(str(coords[relation.始点[0]].内容), "Compound A")
        self.assertEqual(str(coords[relation.終点[0]].内容), "Enzyme X")
        self.assertEqual(_条件値(relation, "極性"), "否定")
        self.assertEqual(_条件値(relation, "scope結合"), "Compiler")
        self.assertEqual(HDSKData射影(ir).関係, ())
        self.assertIn("Compound A", _K内容(ir))
        self.assertNotIn("Compound A does not", _K内容(ir))
        self.assertTrue(any(str(c.種別) == "表層.端点原形" and str(c.内容) == "Compound A does not" for c in ir.座標))

    def test_mayを実体端点と可能scopeへ分離する(self) -> None:
        ir = self.compiler.コンパイル("Compound A may inhibit Enzyme X.")
        relation = _阻害関係(ir)
        coords = ir.座標辞書()
        self.assertEqual(str(coords[relation.始点[0]].内容), "Compound A")
        self.assertEqual(str(coords[relation.終点[0]].内容), "Enzyme X")
        self.assertEqual(_条件値(relation, "様相"), "可能")
        self.assertEqual(_条件値(relation, "様相表層"), "may")
        self.assertEqual(HDSKData射影(ir).関係, ())
        self.assertIn("Compound A", _K内容(ir))
        self.assertNotIn("Compound A may", _K内容(ir))
        self.assertTrue(any(str(c.種別) == "表層.端点原形" and str(c.内容) == "Compound A may" for c in ir.座標))

    def test_mustを必要scopeとして保持する(self) -> None:
        ir = self.compiler.コンパイル("Compound A must inhibit Enzyme X.")
        relation = _阻害関係(ir)
        coords = ir.座標辞書()
        self.assertEqual(str(coords[relation.始点[0]].内容), "Compound A")
        self.assertEqual(_条件値(relation, "様相"), "必要")
        self.assertEqual(HDSKData射影(ir).関係, ())
        self.assertNotIn("Compound A must", _K内容(ir))

    def test_if条件を同じ関係へ結ぶ(self) -> None:
        ir = self.compiler.コンパイル("If condition X, Compound A inhibits Enzyme X.")
        relation = _阻害関係(ir)
        self.assertEqual(_条件値(relation, "条件scope"), "If condition X")
        self.assertEqual(HDSKData射影(ir).関係, ())

    def test_通常肯定文にはscopeを捏造しない(self) -> None:
        ir = self.compiler.コンパイル("Compound A inhibits Enzyme X.")
        relation = _阻害関係(ir)
        self.assertEqual(_条件値(relation, "極性"), "")
        self.assertEqual(_条件値(relation, "様相"), "")
        self.assertEqual(_条件値(relation, "条件scope"), "")
        self.assertTrue(any(str(r.種別) == "阻害" for r in HDSKData射影(ir).関係))
        self.assertFalse(any(str(c.種別) == "表層.端点原形" for c in ir.座標))

    def test_質問文は宣言scope層で再解釈しない(self) -> None:
        ir = self.compiler.コンパイル("Which compound may inhibit Enzyme X?")
        scoped = [r for r in ir.関係 if _条件値(r, "scope結合") == "Compiler"]
        self.assertEqual(scoped, [])


if __name__ == "__main__":
    unittest.main()

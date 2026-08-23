from __future__ import annotations

import unittest

from minidora.hds_compiler_v1 import 公開HDSコンパイラ
from minidora.hds_ir import 値状態


def _edges(ir, kind: str) -> list[tuple[str, str, str]]:
    coords = ir.座標辞書()
    out = []
    for relation in ir.関係:
        if relation.種別 != kind or relation.値状態 != 値状態.確定:
            continue
        for sid in relation.始点:
            for oid in relation.終点:
                if sid in coords and oid in coords:
                    out.append((str(coords[sid].内容), str(coords[oid].内容), str(relation.由来)))
    return out


class HDS英語基底関係試験(unittest.TestCase):
    def setUp(self) -> None:
        self.compiler = 公開HDSコンパイラ()

    def test_過去形generatedを生成関係として保持する(self) -> None:
        ir = self.compiler.コンパイル("Protein A generated metabolite B.")
        edges = _edges(ir, "生成")
        self.assertTrue(any(start == "Protein A" and end == "metabolite B" for start, end, _ in edges))

    def test_受動態inhibited_byを意味方向へ反転する(self) -> None:
        ir = self.compiler.コンパイル("Protein A was inhibited by Protein B.")
        edges = _edges(ir, "阻害")
        self.assertTrue(any(start == "Protein B" and end == "Protein A" for start, end, _ in edges))

    def test_既存現在形関係を二重追加しない(self) -> None:
        ir = self.compiler.コンパイル("Protein A causes apoptosis.")
        edges = _edges(ir, "因果")
        exact = [(start, end) for start, end, _ in edges if start == "Protein A" and end == "apoptosis"]
        self.assertEqual(exact, [("Protein A", "apoptosis")])

    def test_疑問文へ確定関係を捏造しない(self) -> None:
        ir = self.compiler.コンパイル("Which protein was inhibited by Protein B?")
        edges = _edges(ir, "阻害")
        self.assertFalse(any(origin == "共有言語基底P" for _, _, origin in edges))

    def test_単なる共起は関係へ昇格しない(self) -> None:
        ir = self.compiler.コンパイル("Protein A and Protein B were measured in the same sample.")
        self.assertFalse(any(relation.由来 == "共有言語基底P" for relation in ir.関係))


if __name__ == "__main__":
    unittest.main()

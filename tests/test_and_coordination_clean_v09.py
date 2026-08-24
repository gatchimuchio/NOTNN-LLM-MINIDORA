from __future__ import annotations

import unittest

from minidora import 公開HDSコンパイラ


def _expanded(ir, kind: str):
    return [r for r in ir.関係 if str(r.種別) == kind and any(str(x) == "AND展開=v0.9-clean" for x in r.条件)]


def _edges(ir, relations):
    coords = ir.座標辞書()
    return {(str(coords[r.始点[0]].内容), str(coords[r.終点[0]].内容)) for r in relations}


class ANDCoordinationCleanV09試験(unittest.TestCase):
    def setUp(self) -> None:
        self.compiler = 公開HDSコンパイラ()

    def test_主語ANDを二本の関係へ展開する(self) -> None:
        ir = self.compiler.コンパイル("Protein A and Protein B inhibit Enzyme X.")
        rows = _expanded(ir, "阻害")
        self.assertEqual(_edges(ir, rows), {("Protein A", "Enzyme X"), ("Protein B", "Enzyme X")})

    def test_目的語ANDを二本の関係へ展開する(self) -> None:
        ir = self.compiler.コンパイル("Protein A inhibits Enzyme X and Enzyme Y.")
        rows = _expanded(ir, "阻害")
        self.assertEqual(_edges(ir, rows), {("Protein A", "Enzyme X"), ("Protein A", "Enzyme Y")})

    def test_両端ANDは直積へ展開する(self) -> None:
        ir = self.compiler.コンパイル("Protein A and Protein B inhibit Enzyme X and Enzyme Y.")
        rows = _expanded(ir, "阻害")
        self.assertEqual(len(rows), 4)
        self.assertEqual(
            _edges(ir, rows),
            {
                ("Protein A", "Enzyme X"), ("Protein A", "Enzyme Y"),
                ("Protein B", "Enzyme X"), ("Protein B", "Enzyme Y"),
            },
        )

    def test_ORは両方成立とみなさない(self) -> None:
        ir = self.compiler.コンパイル("Protein A or Protein B inhibits Enzyme X.")
        self.assertEqual(_expanded(ir, "阻害"), [])

    def test_複雑な非対称句は無理に分割しない(self) -> None:
        ir = self.compiler.コンパイル("Research and Development Department inhibits Enzyme X.")
        self.assertEqual(_expanded(ir, "阻害"), [])


if __name__ == "__main__":
    unittest.main()

from __future__ import annotations

import unittest

from minidora import 公開HDSコンパイラ


def _関係(ir, kind: str):
    rows = [r for r in ir.関係 if str(r.種別) == kind and str(r.由来) == "共有言語基底P" and any(str(x).startswith("英語関係節射影=") for x in r.条件)]
    if len(rows) != 1:
        raise AssertionError(f"expected one relative-clause relation {kind}, got {len(rows)}")
    return rows[0]


class 明示関係節照応CleanV08試験(unittest.TestCase):
    def setUp(self) -> None:
        self.compiler = 公開HDSコンパイラ()

    def test_whichを先行詞へ戻して能動関係を作る(self) -> None:
        ir = self.compiler.コンパイル("Protein A, which inhibits Protein B, is stable.")
        rel = _関係(ir, "阻害")
        coords = ir.座標辞書()
        self.assertEqual(coords[rel.始点[0]].内容, "Protein A")
        self.assertEqual(coords[rel.終点[0]].内容, "Protein B")
        self.assertFalse(any(str(coords[cid].内容).casefold() == "which" for r in ir.関係 for cid in (*r.始点, *r.終点) if cid in coords))

    def test_受動関係節は意味方向へ反転する(self) -> None:
        ir = self.compiler.コンパイル("Protein A, which is inhibited by Compound X, is stable.")
        rel = _関係(ir, "阻害")
        coords = ir.座標辞書()
        self.assertEqual(coords[rel.始点[0]].内容, "Compound X")
        self.assertEqual(coords[rel.終点[0]].内容, "Protein A")

    def test_whoも明示先行詞へ戻す(self) -> None:
        ir = self.compiler.コンパイル("Researcher A, who uses Method B, reported the result.")
        rel = _関係(ir, "使用")
        coords = ir.座標辞書()
        self.assertEqual(coords[rel.始点[0]].内容, "Researcher A")
        self.assertEqual(coords[rel.終点[0]].内容, "Method B")

    def test_自由代名詞itは勝手に先行詞へ解決しない(self) -> None:
        ir = self.compiler.コンパイル("Protein A was observed. It inhibits Protein B.")
        self.assertFalse(any(any(str(x).startswith("英語関係節射影=") for x in r.条件) for r in ir.関係))

    def test_カンマなし制限関係節は現段階で推測しない(self) -> None:
        ir = self.compiler.コンパイル("Protein A which inhibits Protein B is stable.")
        self.assertFalse(any(any(str(x).startswith("英語関係節射影=") for x in r.条件) for r in ir.関係))


if __name__ == "__main__":
    unittest.main()

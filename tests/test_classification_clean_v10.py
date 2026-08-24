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


def _分類(ir):
    rows = [r for r in ir.関係 if str(r.種別) == "分類" and str(r.由来) == "共有言語基底P"]
    if len(rows) != 1:
        raise AssertionError(f"expected one classification relation, got {len(rows)}")
    return rows[0]


class 明示分類CleanV10試験(unittest.TestCase):
    def setUp(self) -> None:
        self.compiler = 公開HDSコンパイラ()

    def test_is_aを分類へ落とす(self) -> None:
        ir = self.compiler.コンパイル("Water is a compound.")
        rel = _分類(ir)
        coords = ir.座標辞書()
        self.assertEqual(coords[rel.始点[0]].内容, "Water")
        self.assertEqual(coords[rel.終点[0]].内容, "compound")
        self.assertEqual(_条件値(rel, "検索述語"), "is a")

    def test_type_ofを分類へ落とす(self) -> None:
        ir = self.compiler.コンパイル("Entity A is a type of Entity B.")
        rel = _分類(ir)
        coords = ir.座標辞書()
        self.assertEqual(coords[rel.始点[0]].内容, "Entity A")
        self.assertEqual(coords[rel.終点[0]].内容, "Entity B")
        self.assertEqual(_条件値(rel, "検索述語"), "is a type of")

    def test_分類質問を未知始点へ落とす(self) -> None:
        ir = self.compiler.コンパイル("Which molecule is a compound?")
        rel = _分類(ir)
        coords = ir.座標辞書()
        self.assertEqual(_条件値(rel, "不足位置"), "始点")
        self.assertEqual(coords[rel.始点[0]].種別, "目的.未知始点")
        self.assertEqual(coords[rel.始点[0]].内容, "molecule")
        self.assertEqual(coords[rel.終点[0]].内容, "compound")

    def test_型なし選択肢質問も未知始点へ落とす(self) -> None:
        ir = self.compiler.コンパイル("Which of the following is a compound?")
        rel = _分類(ir)
        self.assertEqual(ir.座標辞書()[rel.始点[0]].内容, "選択肢")

    def test_候補queryへ分類関係を復号する(self) -> None:
        ir = self.compiler.問題IR(
            "Which molecule is a compound?",
            ("Water", "Option B", "Option C", "Option D"),
        )
        queries = tuple(q.casefold() for q in HDS参照問合せ候補(ir))
        self.assertTrue(any("water" in q and "is a" in q and "compound" in q for q in queries), queries)

    def test_否定分類は肯定分類へ昇格しない(self) -> None:
        ir = self.compiler.コンパイル("Water is not a compound.")
        self.assertFalse(any(str(r.種別) == "分類" and str(r.由来) == "共有言語基底P" for r in ir.関係))

    def test_前置詞付き役割句を単純分類へしない(self) -> None:
        ir = self.compiler.コンパイル("Protein A is an inhibitor of Protein B.")
        self.assertFalse(any(str(r.種別) == "分類" and str(r.由来) == "共有言語基底P" for r in ir.関係))


if __name__ == "__main__":
    unittest.main()

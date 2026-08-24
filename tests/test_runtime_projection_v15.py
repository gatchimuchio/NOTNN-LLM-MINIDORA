from __future__ import annotations

import unittest

from minidora import 公開HDSコンパイラ
from minidora.hds_ir import HDSIR, HDS実行核, HDS座標, HDS関係, 値状態
from minidora.hds_runtime_projection import HDSKData射影, HDSK候補射影, HDSK質問射影


def _条件値(relation: HDS関係, key: str) -> str:
    prefix = key + "="
    for raw in relation.条件:
        value = str(raw)
        if value.startswith(prefix):
            return value[len(prefix):].strip()
    return ""


class Runtime射影V15試験(unittest.TestCase):
    def setUp(self) -> None:
        self.compiler = 公開HDSコンパイラ()

    def test_未知端点でも既知関係種別をKへ渡す(self) -> None:
        original = self.compiler.コンパイル("Which molecule inhibits Enzyme X?")
        projected = HDSK質問射影(original)
        relation = next(r for r in projected.関係 if _条件値(r, "不足位置") == "始点")
        self.assertEqual(str(relation.種別), "阻害")
        self.assertEqual(relation.値状態, 値状態.確定)
        self.assertEqual(str(relation.暫定性), "RELATION_TYPE_KNOWN_ENDPOINT_OPEN")
        coords = projected.座標辞書()
        known = [coords[cid] for cid in relation.終点 if cid in coords and coords[cid].値状態 == 値状態.確定]
        self.assertTrue(any("Enzyme X" == str(coord.内容) for coord in known))
        unknown = [coords[cid] for cid in relation.始点 if cid in coords]
        self.assertTrue(any(coord.値状態 == 値状態.未観測 for coord in unknown))

    def test_関係質問では検索制御目的メタをKへ混ぜない(self) -> None:
        original = self.compiler.問題IR(
            "Which molecule is least likely to inhibit Enzyme X?",
            ("A", "B", "C", "D"),
        )
        projected = HDSK質問射影(original)
        kinds = {str(coord.種別) for coord in projected.座標 if not coord.座標ID.startswith("choice:")}
        self.assertFalse(any(kind.startswith("検索.") for kind in kinds))
        self.assertFalse(any(kind.startswith("制御.") for kind in kinds))
        # 未知端点は関係形を保つため残せるが、未観測なのでK意味語にはならない。
        self.assertTrue(any(coord.値状態 == 値状態.未観測 for coord in projected.座標 if not coord.座標ID.startswith("choice:")))

    def test_非関係質問ではCompilerの検索表層だけを照合焦点へ使う(self) -> None:
        original = self.compiler.問題IR(
            "Which of the following statements best describes cellular respiration?",
            ("A", "B", "C", "D"),
        )
        projected = HDSK質問射影(original)
        focus = [coord for coord in projected.座標 if str(coord.種別) == "対象.照合焦点"]
        self.assertTrue(focus)
        self.assertTrue(any("cellular" in str(coord.内容).casefold() and "respiration" in str(coord.内容).casefold() for coord in focus))
        self.assertEqual(projected.関係, ())

    def test_候補とDataでは検索制御目的監査をKへ入れない(self) -> None:
        ir = HDSIR(
            原文="synthetic",
            正規化文="synthetic",
            認知世界ID="test",
            座標=(
                HDS座標("s", "対象.始点", "Compound A"),
                HDS座標("o", "対象.終点", "Enzyme X"),
                HDS座標("search", "検索.英語正規化", "compound inhibit enzyme"),
                HDS座標("control", "制御.選択意図", "反転"),
                HDS座標("purpose", "目的.要求型", "molecule"),
                HDS座標("audit", "監査.R_query", "audit query"),
            ),
            関係=(HDS関係("r", ("s",), ("o",), "阻害"),),
            残差=(),
            意味作用履歴=(),
            実行核=HDS実行核(),
        )
        for projected in (HDSK候補射影(ir), HDSKData射影(ir)):
            self.assertEqual({coord.座標ID for coord in projected.座標}, {"s", "o"})
            self.assertEqual(len(projected.関係), 1)
            self.assertEqual(projected.関係[0].種別, "阻害")

    def test_片端が非意味メタなら関係自体をKへ流さない(self) -> None:
        ir = HDSIR(
            原文="synthetic",
            正規化文="synthetic",
            認知世界ID="test",
            座標=(
                HDS座標("s", "対象.始点", "Compound A"),
                HDS座標("meta", "目的.要求型", "molecule"),
            ),
            関係=(HDS関係("r", ("s",), ("meta",), "分類"),),
            残差=(),
            意味作用履歴=(),
            実行核=HDS実行核(),
        )
        projected = HDSKData射影(ir)
        self.assertEqual({coord.座標ID for coord in projected.座標}, {"s"})
        self.assertEqual(projected.関係, ())


if __name__ == "__main__":
    unittest.main()

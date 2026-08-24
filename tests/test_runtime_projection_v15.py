from __future__ import annotations

import unittest

from minidora import 公開HDSコンパイラ
from minidora.hds_ir import HDSIR, HDS実行核, HDS座標, HDS関係, 値状態
from minidora.hds_reference import HDS参照問合せ候補
from minidora.hds_runtime_projection import HDSKData射影, HDSK候補代入可能, HDSK候補射影, HDSK質問射影, HDSR質問射影
from minidora.trinity_context import Trinity文脈系
from minidora.採否 import 実行状態, 採否結果


def _条件値(relation: HDS関係, key: str) -> str:
    prefix = key + "="
    for raw in relation.条件:
        value = str(raw)
        if value.startswith(prefix):
            return value[len(prefix):].strip()
    return ""


def _synthetic_relation_ir(*, start: str = "Compound A", end: str = "Enzyme X", conditions: tuple[str, ...] = (), extra: tuple[HDS座標, ...] = ()) -> HDSIR:
    return HDSIR(
        原文=f"{start} inhibits {end}.",
        正規化文=f"{start} inhibits {end}.",
        認知世界ID="test",
        座標=(
            HDS座標("s", "対象.始点", start),
            HDS座標("o", "対象.終点", end),
            HDS座標("v", "関係.述語", "inhibit"),
            *extra,
        ),
        関係=(HDS関係("r", ("s",), ("o",), "阻害", 条件=conditions),),
        残差=(),
        意味作用履歴=(),
        実行核=HDS実行核(),
    )


def _entity_ir(text: str = "Compound A") -> HDSIR:
    return HDSIR(
        原文=text,
        正規化文=text,
        認知世界ID="test",
        座標=(HDS座標("e", "対象.主題語", text),),
        関係=(),
        残差=(),
        意味作用履歴=(),
        実行核=HDS実行核(),
    )


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

    def test_関係質問では検索制御メタをKへ混ぜない(self) -> None:
        original = self.compiler.問題IR(
            "Which molecule is least likely to inhibit Enzyme X?",
            ("A", "B", "C", "D"),
        )
        projected = HDSK質問射影(original)
        kinds = {str(coord.種別) for coord in projected.座標 if not coord.座標ID.startswith("choice:")}
        self.assertFalse(any(kind.startswith("検索.") for kind in kinds))
        self.assertFalse(any(kind.startswith("制御.") for kind in kinds))
        self.assertTrue(any(coord.値状態 == 値状態.未観測 for coord in projected.座標 if not coord.座標ID.startswith("choice:")))

    def test_非関係質問ではCompiler主題語だけをK照合核へ使う(self) -> None:
        original = self.compiler.問題IR(
            "Which of the following statements best describes cellular respiration?",
            ("A", "B", "C", "D"),
        )
        projected = HDSK質問射影(original)
        topics = [coord for coord in projected.座標 if not coord.座標ID.startswith("choice:")]
        self.assertTrue(topics)
        self.assertTrue(all(str(coord.種別) == "対象.主題語" for coord in topics))
        joined = " ".join(str(coord.内容).casefold() for coord in topics)
        self.assertIn("cellular", joined)
        self.assertIn("respiration", joined)
        self.assertFalse(any(str(coord.種別).startswith("検索.") for coord in projected.座標))
        self.assertEqual(projected.関係, ())

    def test_R関係質問は検索述語既知端点候補を保持する(self) -> None:
        original = self.compiler.問題IR(
            "Which molecule inhibits Enzyme X?",
            ("Compound A", "Compound B", "Compound C", "Compound D"),
        )
        projected = HDSR質問射影(original)
        relation = next(r for r in projected.関係 if _条件値(r, "不足位置") == "始点")
        self.assertEqual(str(relation.種別), "阻害")
        self.assertEqual(_条件値(relation, "検索述語"), "inhibit")
        self.assertEqual(sum(1 for coord in projected.座標 if coord.座標ID.startswith("choice:")), 4)
        queries = tuple(q.casefold() for q in HDS参照問合せ候補(projected))
        for candidate in ("compound a", "compound b", "compound c", "compound d"):
            self.assertTrue(any(candidate in q and "inhibit" in q and "enzyme x" in q for q in queries), queries)

    def test_R射影は選択極性と完全質問文を検索fallbackへ残さない(self) -> None:
        original = self.compiler.問題IR(
            "Which molecule is least likely to inhibit Enzyme X?",
            ("Compound A", "Compound B", "Compound C", "Compound D"),
        )
        projected = HDSR質問射影(original)
        self.assertIn("least likely", original.原文.casefold())
        self.assertNotIn("least likely", projected.原文.casefold())
        self.assertNotIn("which", projected.原文.casefold())
        self.assertFalse(any(str(coord.種別) == "条件.検索極性" for coord in projected.座標))
        self.assertIn("inhibit", projected.原文.casefold())
        self.assertIn("enzyme x", projected.原文.casefold())
        for query in HDS参照問合せ候補(projected):
            self.assertNotIn("least likely", query.casefold())

    def test_R一般質問は検索表層を残し制御監査を捨てる(self) -> None:
        original = self.compiler.問題IR(
            "Which of the following statements best describes cellular respiration?",
            ("A", "B", "C", "D"),
        )
        projected = HDSR質問射影(original)
        nonchoice = [coord for coord in projected.座標 if not coord.座標ID.startswith("choice:")]
        self.assertTrue(any(str(coord.種別).startswith("検索.") for coord in nonchoice))
        self.assertFalse(any(str(coord.種別).startswith("制御.") for coord in nonchoice))
        self.assertFalse(any(str(coord.種別).startswith("監査.") for coord in nonchoice))
        self.assertNotIn("which of the following", projected.原文.casefold())
        queries = tuple(q.casefold() for q in HDS参照問合せ候補(projected))
        self.assertTrue(any("cellular respiration" in q for q in queries[:2]), queries[:2])

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

    def test_実体候補だけ未知端点へ代入可能とする(self) -> None:
        self.assertTrue(HDSK候補代入可能(_entity_ir("Compound A")))
        self.assertFalse(HDSK候補代入可能(_synthetic_relation_ir()))

    def test_否定や条件を持つ候補は実体句として代入しない(self) -> None:
        negative = HDSIR(
            原文="Compound A does not inhibit Enzyme X.",
            正規化文="Compound A does not inhibit Enzyme X.",
            認知世界ID="test",
            座標=(
                HDS座標("topic", "対象.主題語", "Compound A"),
                HDS座標("neg", "状態.否定", "not"),
            ),
            関係=(),
            残差=(),
            意味作用履歴=(),
            実行核=HDS実行核(),
        )
        conditional = HDSIR(
            原文="under condition X, Compound A",
            正規化文="under condition X, Compound A",
            認知世界ID="test",
            座標=(
                HDS座標("topic", "対象.主題語", "Compound A"),
                HDS座標("condition", "条件.前提", "condition X"),
            ),
            関係=(),
            残差=(),
            意味作用履歴=(),
            実行核=HDS実行核(),
        )
        self.assertFalse(HDSK候補代入可能(negative))
        self.assertFalse(HDSK候補代入可能(conditional))

    def test_Kは明示肯定関係だけを有向Fact候補へ残す(self) -> None:
        projected = HDSKData射影(_synthetic_relation_ir())
        self.assertEqual(len(projected.関係), 1)
        self.assertEqual(projected.関係[0].種別, "阻害")

    def test_Kは否定scopeを肯定関係へ潰さない(self) -> None:
        projected = HDSKData射影(_synthetic_relation_ir(conditions=("極性=否定",)))
        self.assertEqual(projected.関係, ())
        self.assertTrue(any(str(coord.内容) == "Compound A" for coord in projected.座標))
        self.assertTrue(any(str(coord.内容) == "Enzyme X" for coord in projected.座標))

    def test_Kはmodalを含む偽端点を有向関係へしない(self) -> None:
        projected = HDSKData射影(_synthetic_relation_ir(start="Compound A may"))
        self.assertEqual(projected.関係, ())
        self.assertTrue(any("Compound A" in str(coord.内容) for coord in projected.座標))

    def test_Kは不確実性scopeを関係にも独立座標にも昇格しない(self) -> None:
        scope = HDS座標("scope", "不確実性.明示", "Compound A may inhibit Enzyme X.", 値状態.推定)
        projected = HDSKData射影(_synthetic_relation_ir(extra=(scope,)))
        self.assertEqual(projected.関係, ())
        self.assertFalse(any(str(coord.種別) == "不確実性.明示" for coord in projected.座標))
        self.assertTrue(any(str(coord.内容) == "Compound A" for coord in projected.座標))
        self.assertTrue(any(str(coord.内容) == "Enzyme X" for coord in projected.座標))

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

    def test_Mは射影ではなく完全IRを保持する(self) -> None:
        original = self.compiler.問題IR(
            "Which molecule is least likely to inhibit Enzyme X?",
            ("A", "B", "C", "D"),
        )
        trinity = Trinity文脈系()
        trinity.帰還(採否結果(実行状態.保留, ("test",)), None, original)
        stored = trinity.記憶主体.IR履歴[-1]
        self.assertEqual(stored, original)
        self.assertTrue(any(str(coord.種別).startswith("制御.") for coord in stored.座標))
        self.assertTrue(any(str(coord.種別).startswith("検索.") for coord in stored.座標))
        self.assertIn("least likely", stored.原文.casefold())


if __name__ == "__main__":
    unittest.main()

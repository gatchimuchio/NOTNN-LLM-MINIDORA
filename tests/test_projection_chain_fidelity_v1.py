from __future__ import annotations

import unittest

from minidora.hds_choice_hypothesis import HDS候補代入仮説群
from minidora.hds_ir import HDSIR, HDS実行核, HDS座標, HDS関係, 値状態
from minidora.hds_language_relations import HDS英語基底関係射影
from minidora.hds_language_semantic_bridge import HDS英日意味射影
from minidora.hds_model_projection import HDSMINIDORA模型評価
from minidora.hds_runtime_projection import HDSK候補射影, HDSK質問射影
from minidora.模型 import 標準模型核
from minidora.言語基底_英日意味強化 import 英日意味フレーム抽出, 英語明示述語関係抽出


def _cond(relation: HDS関係, key: str) -> str:
    prefix = key + "="
    for raw in relation.条件:
        value = str(raw)
        if value.startswith(prefix):
            return value[len(prefix):].strip()
    return ""


def _ir(text: str, coords: tuple[HDS座標, ...], relations: tuple[HDS関係, ...] = (), *, kind: str = "一般") -> HDSIR:
    return HDSIR(
        原文=text,
        正規化文=text,
        認知世界ID="fidelity-test",
        座標=coords,
        関係=relations,
        残差=(),
        意味作用履歴=(),
        実行核=HDS実行核(),
        種別=kind,
        入力言語="en",
    )


def _question_ir(text: str, choices: tuple[str, ...]) -> HDSIR:
    coords = tuple(HDS座標(f"choice:{chr(65 + index)}", "候補.選択肢", choice) for index, choice in enumerate(choices))
    return HDS英日意味射影(_ir(text, coords, kind="knowledge_query"))


class 三層射影忠実度試験(unittest.TestCase):
    def test_未知明示述語を質問と宣言の双方で同じ基本形へ戻す(self) -> None:
        question = 英日意味フレーム抽出("Which molecule stabilizes intermediate X?")
        self.assertIsNotNone(question.関係質問)
        assert question.関係質問 is not None
        self.assertEqual(question.関係質問.種別, "開放述語")
        self.assertEqual(question.関係質問.検索述語, "stabilize")

        statement = 英語明示述語関係抽出("Molecule A stabilized intermediate X.")
        self.assertEqual(len(statement), 1)
        self.assertEqual(statement[0].種別, "開放述語")
        self.assertEqual(statement[0].検索述語, "stabilize")

    def test_数量同定とmodal_copulaをtopic_onlyへ落とさない(self) -> None:
        quantity = 英日意味フレーム抽出("How many possible products are there excluding ethene?")
        self.assertIsNotNone(quantity.関係質問)
        assert quantity.関係質問 is not None
        self.assertEqual(quantity.関係質問.種別, "数量同定")
        self.assertEqual(quantity.関係質問.検索述語, "count")

        identity = 英日意味フレーム抽出("What would be the approximate ratio of flux A to flux B?")
        self.assertIsNotNone(identity.関係質問)
        assert identity.関係質問 is not None
        self.assertEqual(identity.関係質問.種別, "同定")
        self.assertEqual(identity.関係質問.検索述語, "identify")

        negative = 英日意味フレーム抽出("Which theory never requires regularization at high energies?")
        self.assertIsNotNone(negative.関係質問)
        assert negative.関係質問 is not None
        self.assertIn(("極性", "否定"), negative.関係質問.修飾)

    def test_英語宣言関係射影は否定と条件を落とさない(self) -> None:
        base = _ir("Compound A does not alter process B under condition C.", ())
        projected = HDS英語基底関係射影(base)
        relation = next(r for r in projected.関係 if _cond(r, "検索述語") == "alter")
        self.assertEqual(relation.種別, "開放述語")
        self.assertEqual(_cond(relation, "極性"), "否定")
        self.assertIn("condition C", _cond(relation, "条件scope"))

    def test_知識選択質問はtopic_onlyを正常状態にしない(self) -> None:
        question = _question_ir("Which statement is most likely correct regarding entropy?", ("A", "B", "C", "D"))
        projected = HDSK質問射影(question)
        self.assertTrue(projected.関係)
        self.assertEqual(projected.関係[0].種別, "命題適合")
        self.assertFalse(any(r.種別 == "semantic_loss" for r in projected.残差))

        unresolved = HDSK質問射影(_question_ir("Which?", ("A", "B")))
        self.assertTrue(any(r.種別 == "semantic_loss" for r in unresolved.残差))

    def test_候補代入は問いの極性とscopeを保持する(self) -> None:
        question = _question_ir("Under condition C, which molecule does not stabilize intermediate X?", ("Molecule A", "Molecule B"))
        kq = HDSK質問射影(question)
        candidate_irs = {
            "A": HDSK候補射影(_ir("Molecule A", (HDS座標("a", "対象.実体", "Molecule A"),))),
            "B": HDSK候補射影(_ir("Molecule B", (HDS座標("b", "対象.実体", "Molecule B"),))),
        }
        hypotheses = HDS候補代入仮説群(kq, candidate_irs)
        for candidate in hypotheses.values():
            relation = next(r for r in candidate.関係 if r.由来 == "HDS候補代入仮説")
            self.assertEqual(_cond(relation, "極性"), "否定")
            self.assertIn("condition C", _cond(relation, "条件scope"))

    def test_正式模型核はHDS非依存の参照寄与で候補差を形成する(self) -> None:
        question = _ir(
            "Which molecule inhibits Enzyme X?",
            (HDS座標("unknown", "目的.未知始点", "molecule", 値状態.未観測), HDS座標("target", "対象.終点", "Enzyme X")),
            (HDS関係("q", ("unknown",), ("target",), "阻害", 条件=("検索述語=inhibit", "不足位置=始点"), 値状態=値状態.確定),),
            kind="knowledge_query",
        )
        candidates = {
            "A": _ir("Molecule A", (HDS座標("a", "対象.実体", "Molecule A"),)),
            "B": _ir("Molecule B", (HDS座標("b", "対象.実体", "Molecule B"),)),
        }
        hypotheses = HDS候補代入仮説群(question, candidates)
        evidence = _ir(
            "Molecule A inhibits Enzyme X.",
            (HDS座標("s", "対象.始点", "Molecule A"), HDS座標("o", "対象.終点", "Enzyme X")),
            (HDS関係("e", ("s",), ("o",), "阻害", 条件=("検索述語=inhibit",)),),
        )
        result = HDSMINIDORA模型評価(question, hypotheses, (evidence,), 模型核=標準模型核())
        self.assertEqual(result.状態, "APPROVE")
        self.assertEqual(result.回答ラベル, "A")
        self.assertTrue(result.模型結果.checkpoint)
        modules = {type(item).__module__.casefold() for item in 標準模型核().関係群}
        self.assertTrue(all("hds" not in name for name in modules))

        reverse_question = _ir(
            "Which molecule is least likely to inhibit Enzyme X?",
            question.座標,
            (HDS関係("q", ("unknown",), ("target",), "阻害", 条件=("検索述語=inhibit", "不足位置=始点", "選択意図=反転"), 値状態=値状態.確定),),
            kind="knowledge_query",
        )
        contradicted = _ir(
            "Molecule B does not inhibit Enzyme X.",
            (HDS座標("s", "対象.始点", "Molecule B"), HDS座標("o", "対象.終点", "Enzyme X")),
            (HDS関係("e", ("s",), ("o",), "阻害", 条件=("検索述語=inhibit", "極性=否定")),),
        )
        reverse_hypotheses = HDS候補代入仮説群(reverse_question, candidates)
        reverse = HDSMINIDORA模型評価(reverse_question, reverse_hypotheses, (evidence, contradicted), 模型核=標準模型核())
        self.assertEqual(reverse.回答ラベル, "B")


if __name__ == "__main__":
    unittest.main()

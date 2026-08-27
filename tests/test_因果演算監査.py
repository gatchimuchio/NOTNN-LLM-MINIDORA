from __future__ import annotations

import unittest

from minidora.hds_ir import HDSIR, HDS実行核, HDS座標, HDS関係
from minidora.hds_model_projection import HDSMINIDORA模型評価


def ir(text: str, coords=(), relations=()) -> HDSIR:
    return HDSIR(
        原文=text,
        正規化文=text,
        認知世界ID="causal-audit-test",
        座標=tuple(coords),
        関係=tuple(relations),
        残差=(),
        意味作用履歴=(),
        実行核=HDS実行核(),
        種別="knowledge_query",
        入力言語="en",
    )


def relation_ir(text: str, start: str, end: str, kind: str, predicate: str) -> HDSIR:
    return ir(
        text,
        (
            HDS座標("s", "対象.実体", start),
            HDS座標("o", "対象.実体", end),
        ),
        (HDS関係("r", ("s",), ("o",), kind, (f"検索述語={predicate}",)),),
    )


class 因果演算監査試験(unittest.TestCase):
    def test_因果導出が候補差へ作用した時だけAPPLIEDを記録する(self):
        question = ir("Which effect follows?")
        candidates = {
            "A": relation_ir("A", "alpha", "gamma", "問い適合", "decrease"),
            "B": relation_ir("B", "alpha", "gamma", "問い適合", "increase"),
        }
        data = (
            relation_ir("alpha increases beta", "alpha", "beta", "増加", "increase"),
            relation_ir("beta decreases gamma", "beta", "gamma", "減少", "decrease"),
        )
        result = HDSMINIDORA模型評価(question, candidates, data, 参照識別子=("r1", "r2"))
        self.assertIn("CAUSAL_DERIVATION_APPLIED", result.理由)
        self.assertTrue(any(reason.startswith("CAUSAL_DERIVATION_CONTRIBUTIONS:") for reason in result.理由))
        self.assertTrue(any(reason.startswith("CAUSAL_DERIVATION_CANDIDATES:") for reason in result.理由))

    def test_直接関係だけならNOT_APPLIEDを記録する(self):
        question = ir("Which effect follows?")
        candidates = {
            "A": relation_ir("A", "alpha", "gamma", "問い適合", "increase"),
            "B": relation_ir("B", "alpha", "gamma", "問い適合", "decrease"),
        }
        data = (relation_ir("alpha increases gamma", "alpha", "gamma", "増加", "increase"),)
        result = HDSMINIDORA模型評価(question, candidates, data, 参照識別子=("r1",))
        self.assertIn("CAUSAL_DERIVATION_NOT_APPLIED", result.理由)
        self.assertNotIn("CAUSAL_DERIVATION_APPLIED", result.理由)


if __name__ == "__main__":
    unittest.main()

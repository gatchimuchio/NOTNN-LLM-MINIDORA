from __future__ import annotations

import unittest

from minidora.hds_data_k import HDSIR知識Adapter, HDS証拠事実
from minidora.hds_ir import HDSIR, HDS実行核, HDS座標, HDS関係, 値状態
from minidora.k3_functional import K3相当能力核


def _ir(state: 値状態 = 値状態.確定) -> HDSIR:
    return HDSIR(
        原文="Alpha uses engine.",
        正規化文="Alpha uses engine.",
        認知世界ID="source-confidence-test",
        座標=(
            HDS座標("alpha", "対象.実体", "Alpha", 値状態=state),
            HDS座標("engine", "対象.実体", "engine", 値状態=state),
        ),
        関係=(HDS関係("r", ("alpha",), ("engine",), "作用", 値状態=state),),
        残差=(),
        意味作用履歴=(),
        実行核=HDS実行核("意味構造転送"),
    )


class HDSSourceConfidence試験(unittest.TestCase):
    def test_R信頼係数をHDS値状態confidenceと乗算する(self) -> None:
        core = K3相当能力核()
        result = HDSIR知識Adapter(core).投入(
            _ir(値状態.推定),
            provenance=("fixture", "doc:1"),
            信頼係数=0.5,
        )
        facts = [fact for fact in HDS証拠事実(core) if fact.predicate != "hds_residual"]
        self.assertTrue(facts)
        self.assertTrue(all(abs(fact.confidence - 0.43) < 1e-9 for fact in facts))
        self.assertEqual(result.source_confidence, 0.5)
        self.assertEqual(result.retrieval_independence, 1.0)
        self.assertTrue(all("source_confidence:0.500000" in fact.provenance for fact in facts))
        self.assertTrue(all("retrieval_independence:1.000000" in fact.provenance for fact in facts))

    def test_R信頼係数は0から1へclampする(self) -> None:
        high = K3相当能力核()
        HDSIR知識Adapter(high).投入(_ir(), provenance=("fixture", "high"), 信頼係数=2.0)
        self.assertTrue(all(fact.confidence <= 1.0 for fact in HDS証拠事実(high)))

        low = K3相当能力核()
        HDSIR知識Adapter(low).投入(_ir(), provenance=("fixture", "low"), 信頼係数=-1.0)
        self.assertTrue(all(fact.confidence == 0.0 for fact in HDS証拠事実(low)))

    def test_候補指定queryだけで発見した資料は補助証拠へ減衰する(self) -> None:
        core = K3相当能力核()
        result = HDSIR知識Adapter(core).投入(
            _ir(),
            provenance=("fixture", "doc:choice", "query_choice:A", "query_kind:choice"),
            信頼係数=0.8,
        )
        facts = [fact for fact in HDS証拠事実(core) if fact.predicate != "hds_residual"]
        self.assertTrue(facts)
        self.assertEqual(result.source_confidence, 0.8)
        self.assertEqual(result.retrieval_independence, 0.25)
        self.assertTrue(all(abs(fact.confidence - 0.2) < 1e-9 for fact in facts))
        self.assertTrue(all("source_confidence:0.800000" in fact.provenance for fact in facts))
        self.assertTrue(all("retrieval_independence:0.250000" in fact.provenance for fact in facts))

    def test_同一資料が候補非依存queryでも発見された場合は減衰しない(self) -> None:
        core = K3相当能力核()
        result = HDSIR知識Adapter(core).投入(
            _ir(),
            provenance=(
                "fixture", "doc:mixed", "query_choice:A", "query_kind:choice", "query_kind:structured",
            ),
            信頼係数=0.8,
        )
        facts = [fact for fact in HDS証拠事実(core) if fact.predicate != "hds_residual"]
        self.assertTrue(facts)
        self.assertEqual(result.retrieval_independence, 1.0)
        self.assertTrue(all(abs(fact.confidence - 0.8) < 1e-9 for fact in facts))


if __name__ == "__main__":
    unittest.main()

from __future__ import annotations

import unittest

from minidora.hds_data_k import HDSIR知識Adapter, HDS証拠事実, HDS証拠状態複製
from minidora.hds_graph_reasoning import HDS意味Graph索引構築
from minidora.hds_ir import HDSIR, HDS実行核, HDS座標, HDS関係
from minidora.k3_functional import K3相当能力核


def _ir() -> HDSIR:
    return HDSIR(
        原文="Alpha uses engine.",
        正規化文="Alpha uses engine.",
        認知世界ID="clone-test",
        座標=(
            HDS座標("alpha", "対象.実体", "Alpha"),
            HDS座標("engine", "対象.実体", "engine"),
        ),
        関係=(HDS関係("r", ("alpha",), ("engine",), "作用"),),
        残差=(),
        意味作用履歴=(),
        実行核=HDS実行核("意味構造転送"),
    )


class HDS証拠Clone試験(unittest.TestCase):
    def test_K3clone後も独立source台帳を明示複製できる(self) -> None:
        source = K3相当能力核()
        adapter = HDSIR知識Adapter(source)
        adapter.投入(_ir(), provenance=("fixture", "doc:1"))
        adapter.投入(_ir(), provenance=("fixture", "doc:2"))
        source_evidence = HDS証拠事実(source)
        self.assertGreater(len(source_evidence), 0)

        cloned = source.clone()
        self.assertEqual(HDS証拠事実(cloned), ())
        HDS証拠状態複製(source, cloned)

        cloned_evidence = HDS証拠事実(cloned)
        self.assertEqual(len(cloned_evidence), len(source_evidence))
        self.assertIsNot(cloned.K, source.K)
        self.assertEqual(
            {fact.fact_id for fact in cloned_evidence},
            {fact.fact_id for fact in source_evidence},
        )

    def test_複製先graph索引は共有せず再構築する(self) -> None:
        source = K3相当能力核()
        HDSIR知識Adapter(source).投入(_ir(), provenance=("fixture", "doc:1"))
        source_index = HDS意味Graph索引構築(source)

        cloned = source.clone()
        HDS証拠状態複製(source, cloned)
        cloned_index = HDS意味Graph索引構築(cloned)

        self.assertIsNot(source_index, cloned_index)
        self.assertEqual(source_index.revision, cloned_index.revision)
        self.assertEqual(source_index.関係Fact数, cloned_index.関係Fact数)


if __name__ == "__main__":
    unittest.main()

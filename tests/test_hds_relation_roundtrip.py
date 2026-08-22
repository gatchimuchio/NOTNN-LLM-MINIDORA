from __future__ import annotations

import unittest

from minidora.hds_data_k import HDSIR知識Adapter, HDS証拠事実
from minidora.hds_graph_reasoning import HDS意味Graph索引構築
from minidora.hds_ir import HDSIR, HDS実行核, HDS座標, HDS関係
from minidora.k3_functional import K3相当能力核


class HDS関係ラベル往復試験(unittest.TestCase):
    def test_関係記号をsanitizeで潰さずKへ保持する(self) -> None:
        ir = HDSIR(
            原文="A describes B.",
            正規化文="A describes B.",
            認知世界ID="relation-roundtrip",
            座標=(
                HDS座標("a", "対象.実体", "A"),
                HDS座標("b", "対象.実体", "B"),
            ),
            関係=(HDS関係("r", ("a",), ("b",), "記述→問い"),),
            残差=(),
            意味作用履歴=(),
            実行核=HDS実行核("意味構造転送"),
            種別="意味構造",
            閉包状態="CLOSED_FOR_SEMANTIC_TRANSFER",
        )
        core = K3相当能力核()
        HDSIR知識Adapter(core).投入(ir, provenance=("fixture", "doc:1"))

        relation_facts = [fact for fact in HDS証拠事実(core) if fact.predicate.startswith("hds_relation_")]
        self.assertEqual(len(relation_facts), 1)
        self.assertEqual(relation_facts[0].predicate, "hds_relation_記述→問い")

        graph = HDS意味Graph索引構築(core)
        relation_names = {edge.関係 for edges in graph.隣接.values() for edge in edges}
        self.assertIn("記述→問い", relation_names)
        self.assertNotIn("記述 問い", relation_names)


if __name__ == "__main__":
    unittest.main()

from __future__ import annotations

import unittest

from minidora.hds_data_k import HDSIR知識Adapter
from minidora.hds_graph_reasoning import HDS意味Graph索引構築, HDS意味経路探索
from minidora.hds_ir import HDSIR, HDS実行核, HDS座標, HDS関係, HDS残差
from minidora.k3_functional import K3相当能力核
from minidora.semantic_tokens import 意味語


def _relation_ir(target: str, residuals: tuple[HDS残差, ...] = ()) -> HDSIR:
    return HDSIR(
        原文=f"Alpha relates to {target}.",
        正規化文=f"Alpha relates to {target}.",
        認知世界ID="graph-cycle-test",
        座標=(
            HDS座標("alpha", "対象.実体", "Alpha", 原文範囲=(0, 5)),
            HDS座標("target", "対象.実体", target, 原文範囲=(18, 18 + len(target))),
        ),
        関係=(HDS関係("r", ("alpha",), ("target",), "作用"),),
        残差=residuals,
        意味作用履歴=(),
        実行核=HDS実行核("意味構造転送"),
        種別="意味構造",
        閉包状態="CLOSED_FOR_SEMANTIC_TRANSFER",
        入力言語="en",
    )


class HDSGraph単純路試験(unittest.TestCase):
    def test_直接到達を往復循環で水増ししない(self) -> None:
        core = K3相当能力核()
        adapter = HDSIR知識Adapter(core)
        adapter.投入(_relation_ir("engine"), provenance=("fixture", "doc:engine"))
        adapter.投入(_relation_ir("stone"), provenance=("fixture", "doc:stone"))

        result = HDS意味経路探索(core, 意味語("Alpha"), 意味語("stone"), 最大深さ=4)
        self.assertGreater(result.得点, 0.0)
        self.assertEqual(result.深さ, 1)
        self.assertEqual(len(result.事実ID), 1)

    def test_正当な多段単純路は維持する(self) -> None:
        core = K3相当能力核()
        adapter = HDSIR知識Adapter(core)
        adapter.投入(_relation_ir("Beta"), provenance=("fixture", "doc:1"))
        second = HDSIR(
            原文="Beta relates to Engine.",
            正規化文="Beta relates to Engine.",
            認知世界ID="graph-cycle-test",
            座標=(
                HDS座標("beta", "対象.実体", "Beta", 原文範囲=(0, 4)),
                HDS座標("engine", "対象.実体", "Engine", 原文範囲=(16, 22)),
            ),
            関係=(HDS関係("r2", ("beta",), ("engine",), "因果"),),
            残差=(),
            意味作用履歴=(),
            実行核=HDS実行核("意味構造転送"),
            種別="意味構造",
            閉包状態="CLOSED_FOR_SEMANTIC_TRANSFER",
            入力言語="en",
        )
        adapter.投入(second, provenance=("fixture", "doc:2"))

        result = HDS意味経路探索(core, 意味語("Alpha"), 意味語("Engine"), 最大深さ=4)
        self.assertGreater(result.得点, 0.0)
        self.assertEqual(result.深さ, 2)
        self.assertGreaterEqual(len(result.事実ID), 2)

    def test_graph索引はK更新まで再利用し投入後に無効化する(self) -> None:
        core = K3相当能力核()
        adapter = HDSIR知識Adapter(core)
        adapter.投入(_relation_ir("engine"), provenance=("fixture", "doc:1"))

        first = HDS意味Graph索引構築(core)
        second = HDS意味Graph索引構築(core)
        self.assertIs(first, second)

        adapter.投入(_relation_ir("stone"), provenance=("fixture", "doc:2"))
        third = HDS意味Graph索引構築(core)
        self.assertIsNot(first, third)
        self.assertGreater(third.revision, first.revision)
        self.assertGreaterEqual(third.関係Fact数, first.関係Fact数)

    def test_残差sourceと健全sourceの投入順でgraph可用性が変わらない(self) -> None:
        blocked = _relation_ir(
            "engine",
            (HDS残差("loss", "semantic_loss", "Alpha relates to engine", "意味損失"),),
        )
        good = _relation_ir("engine")

        for order in ((blocked, good), (good, blocked)):
            core = K3相当能力核()
            adapter = HDSIR知識Adapter(core)
            adapter.投入(order[0], provenance=("fixture", "doc:first"))
            adapter.投入(order[1], provenance=("fixture", "doc:second"))

            graph = HDS意味Graph索引構築(core)
            result = HDS意味経路探索(
                core,
                意味語("Alpha"),
                意味語("engine"),
                最大深さ=2,
                索引=graph,
            )
            self.assertGreater(result.得点, 0.0)
            self.assertEqual(result.深さ, 1)
            self.assertEqual(graph.関係Fact数, 1)


if __name__ == "__main__":
    unittest.main()

from __future__ import annotations

import unittest

from minidora import hds_choice_runtime
from minidora.hds_choice_runtime import _参照provenance
from minidora.hds_data_k import HDSIR知識Adapter, HDS証拠事実
from minidora.hds_ir import HDSIR, HDS実行核, HDS座標, HDS関係
from minidora.k3_functional import K3相当能力核
from minidora.参照 import 参照記録


def _record(identifier: str, content: str, label: str) -> 参照記録:
    return 参照記録(
        identifier,
        "ProteinX",
        content,
        f"fixture://{identifier}",
        "fixture-R",
        条件=(("hds_query_kind", "choice"), ("hds_query_choice", label)),
    )


def _data() -> HDSIR:
    return HDSIR(
        原文="ProteinX performs catalysis.",
        正規化文="ProteinX performs catalysis.",
        認知世界ID="route-boundary-test",
        座標=(
            HDS座標("s", "対象.始点", "ProteinX"),
            HDS座標("o", "対象.終点", "catalysis"),
        ),
        関係=(HDS関係("r", ("s",), ("o",), "機能"),),
        残差=(),
        意味作用履歴=(),
        実行核=HDS実行核(),
        入力言語="en",
    )


class HDS検索経路境界試験(unittest.TestCase):
    def test_query種別と候補はprovenanceへだけ保持する(self) -> None:
        record = _record("cat-1", "ProteinX catalysis is experimentally observed.", "A")
        provenance = _参照provenance(record)
        self.assertIn("query_kind:choice", provenance)
        self.assertIn("query_choice:A", provenance)

    def test_query経路から擬似K証拠を生成する関数を持たない(self) -> None:
        self.assertFalse(hasattr(hds_choice_runtime, "_検索経路証拠"))

    def test_query候補ラベルはFact引数へ混入しない(self) -> None:
        record = _record("cat-1", "ProteinX catalysis is experimentally observed.", "A")
        core = K3相当能力核()
        HDSIR知識Adapter(core).投入(_data(), provenance=_参照provenance(record))
        facts = HDS証拠事実(core)
        self.assertTrue(facts)
        self.assertTrue(any("query_choice:A" in tuple(str(x) for x in fact.provenance) for fact in facts))
        self.assertFalse(any("A" in tuple(str(x) for x in fact.args) for fact in facts))


if __name__ == "__main__":
    unittest.main()

from __future__ import annotations

import unittest

from minidora.hds_data_k import HDSIR知識Adapter, HDS証拠事実, HDS証拠状態複製
from minidora.hds_ir import HDSIR, HDS実行核, HDS座標, HDS関係, 値状態
from minidora.hds作業状態 import HDS一時証拠統合, HDS作業状態構築, HDS寄与Gate再照合
from minidora.k3_functional import K3相当能力核


def _weak_relation(*, negative: bool = False) -> HDSIR:
    conditions = ("極性=否定",) if negative else ()
    return HDSIR(
        原文="Alpha does not use engine." if negative else "Alpha uses engine.",
        正規化文="Alpha does not use engine." if negative else "Alpha uses engine.",
        認知世界ID="working-state-test",
        座標=(
            HDS座標("alpha", "対象.実体", "Alpha", 値状態=値状態.留保),
            HDS座標("engine", "対象.実体", "engine", 値状態=値状態.留保),
        ),
        関係=(HDS関係("use", ("alpha",), ("engine",), "作用", 条件=conditions, 値状態=値状態.留保),),
        残差=(),
        意味作用履歴=(),
        実行核=HDS実行核("意味構造転送"),
        種別="knowledge_data",
        閉包状態="CLOSED_FOR_SEMANTIC_TRANSFER",
        入力言語="en",
        手順=None,
    )


class HDS作業状態試験(unittest.TestCase):
    def _core(self, *rows: tuple[str, HDSIR]) -> K3相当能力核:
        core = K3相当能力核()
        adapter = HDSIR知識Adapter(core)
        for source, ir in rows:
            adapter.投入(ir, provenance=("fixture", "fixture://" + source, source), 信頼係数=1.0)
        return core

    def test_二独立出典の未解関係は一時証拠化するがcanonical_Kは増やさない(self) -> None:
        core = self._core(("a", _weak_relation()), ("b", _weak_relation()))
        before_k = len(getattr(core.K, "_facts", {}))
        state = HDS作業状態構築(core)
        temporary = HDS寄与Gate再照合(state)

        self.assertGreaterEqual(len(temporary), 2)
        self.assertEqual(state.統計.作業関係K昇格数, 0)
        self.assertGreater(state.統計.作業関係再利用数, 0)
        self.assertEqual(len(getattr(core.K, "_facts", {})), before_k)

        clone = core.clone()
        HDS証拠状態複製(core, clone)
        clone_before_k = len(getattr(clone.K, "_facts", {}))
        added = HDS一時証拠統合(clone, temporary)
        self.assertEqual(added, len(temporary))
        self.assertEqual(len(getattr(clone.K, "_facts", {})), clone_before_k)
        self.assertGreater(len(HDS証拠事実(clone)), len(HDS証拠事実(core)))

    def test_一出典だけでは一時証拠化しない(self) -> None:
        core = self._core(("a", _weak_relation()))
        state = HDS作業状態構築(core)
        temporary = HDS寄与Gate再照合(state)
        self.assertEqual(temporary, ())
        self.assertEqual(state.統計.作業関係K昇格数, 0)

    def test_反対関係が存在すれば再照合で一時証拠化しない(self) -> None:
        core = self._core(
            ("a", _weak_relation()),
            ("b", _weak_relation()),
            ("c", _weak_relation(negative=True)),
        )
        state = HDS作業状態構築(core)
        temporary = HDS寄与Gate再照合(state)
        positive_relations = [fact for fact in temporary if fact.predicate == "hds_relation_作用" and fact.polarity]
        self.assertEqual(positive_relations, [])
        self.assertGreater(state.統計.作業関係再検証後破棄数, 0)

    def test_checkpointは同じ入力で決定論的(self) -> None:
        core1 = self._core(("a", _weak_relation()), ("b", _weak_relation()))
        core2 = self._core(("a", _weak_relation()), ("b", _weak_relation()))
        state1 = HDS作業状態構築(core1)
        state2 = HDS作業状態構築(core2)
        HDS寄与Gate再照合(state1)
        HDS寄与Gate再照合(state2)
        self.assertEqual(
            [(cp.checkpointID, cp.段階) for cp in state1.checkpoint],
            [(cp.checkpointID, cp.段階) for cp in state2.checkpoint],
        )


if __name__ == "__main__":
    unittest.main()

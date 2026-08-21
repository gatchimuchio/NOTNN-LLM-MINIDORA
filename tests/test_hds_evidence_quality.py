from __future__ import annotations

import unittest

from minidora.hds_data_k import HDSIR知識Adapter
from minidora.hds_ir import HDSIR, HDS実行核, HDS座標, HDS関係, 値状態
from minidora.k3_functional import K3相当能力核
from minidora.k3_hds_native import HDSIRネイティブAdapter


def _ir(
    text: str,
    coords: tuple[HDS座標, ...],
    relations: tuple[HDS関係, ...] = (),
) -> HDSIR:
    return HDSIR(
        原文=text,
        正規化文=text,
        認知世界ID="evidence-test",
        座標=coords,
        関係=relations,
        残差=(),
        意味作用履歴=(),
        実行核=HDS実行核("意味構造転送"),
        種別="意味構造",
        閉包状態="CLOSED_FOR_SEMANTIC_TRANSFER",
        入力言語="en",
    )


def _question() -> HDSIR:
    return _ir(
        "What does Alpha use?",
        (
            HDS座標("alpha", "対象.実体", "Alpha", 原文範囲=(10, 15)),
            HDS座標("choice:A", "目的.候補", "engine"),
            HDS座標("choice:B", "目的.候補", "stone"),
        ),
    )


def _candidates() -> dict[str, HDSIR]:
    return {
        "A": _ir("engine", (HDS座標("a", "対象.実体", "engine", 原文範囲=(0, 6)),)),
        "B": _ir("stone", (HDS座標("b", "対象.実体", "stone", 原文範囲=(0, 5)),)),
    }


def _use_ir(obj: str, *, state: 値状態 = 値状態.確定) -> HDSIR:
    return _ir(
        f"Alpha uses {obj}.",
        (
            HDS座標("alpha", "対象.実体", "Alpha", 原文範囲=(0, 5)),
            HDS座標("obj", "対象.実体", obj, 原文範囲=(11, 11 + len(obj))),
        ),
        (HDS関係("use", ("alpha",), ("obj",), "作用", 値状態=state),),
    )


class HDS証拠品質試験(unittest.TestCase):
    def test_独立2sourceの支持を1sourceへ潰さない(self) -> None:
        core = K3相当能力核()
        adapter = HDSIR知識Adapter(core)
        adapter.投入(_use_ir("engine"), provenance=("web", "doc:engine:1"))
        adapter.投入(_use_ir("engine"), provenance=("web", "doc:engine:2"))
        adapter.投入(_use_ir("stone"), provenance=("web", "doc:stone:1"))

        result = HDSIRネイティブAdapter(core).実行(_question(), 候補IR=_candidates())
        self.assertEqual(result.状態, "APPROVE")
        self.assertEqual(result.回答ラベル, "A")
        engine_candidate = next(c for c in result.候補 if c.answer == "A")
        self.assertGreaterEqual(len(engine_candidate.proof_fact_ids), 2)

    def test_未確定関係は同一文書共起だけで確定根拠へ昇格しない(self) -> None:
        core = K3相当能力核()
        HDSIR知識Adapter(core).投入(
            _use_ir("engine", state=値状態.未確定),
            provenance=("web", "doc:uncertain"),
        )

        result = HDSIRネイティブAdapter(core).実行(_question(), 候補IR=_candidates())
        self.assertEqual(result.状態, "SUSPEND")
        self.assertIsNone(result.回答ラベル)

    def test_確定関係は同じDataで承認可能(self) -> None:
        core = K3相当能力核()
        HDSIR知識Adapter(core).投入(
            _use_ir("engine", state=値状態.確定),
            provenance=("web", "doc:confirmed"),
        )

        result = HDSIRネイティブAdapter(core).実行(_question(), 候補IR=_candidates())
        self.assertEqual(result.状態, "APPROVE")
        self.assertEqual(result.回答ラベル, "A")


if __name__ == "__main__":
    unittest.main()

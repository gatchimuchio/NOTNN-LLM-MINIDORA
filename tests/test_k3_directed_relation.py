from __future__ import annotations

import unittest

from minidora.hds_data_k import HDSIR知識Adapter
from minidora.hds_ir import HDSIR, HDS実行核, HDS座標, HDS関係
from minidora.k3_functional import K3相当能力核
from minidora.k3_hds_native import HDSIRネイティブAdapter, _edge_similarity, _意味署名


def _ir(text: str, coords: tuple[HDS座標, ...], relations: tuple[HDS関係, ...] = ()) -> HDSIR:
    return HDSIR(
        原文=text,
        正規化文=text,
        認知世界ID="directed-relation-test",
        座標=coords,
        関係=relations,
        残差=(),
        意味作用履歴=(),
        実行核=HDS実行核("意味構造転送"),
        種別="意味構造",
        閉包状態="CLOSED_FOR_SEMANTIC_TRANSFER",
        入力言語="en",
    )


def _direction_candidate(text: str, *, reverse: bool) -> HDSIR:
    starts = ("beta",) if reverse else ("alpha",)
    ends = ("alpha",) if reverse else ("beta",)
    return _ir(
        text,
        (
            HDS座標("alpha", "対象.実体", "Alpha", 原文範囲=(0, 5)),
            HDS座標("beta", "対象.実体", "Beta", 原文範囲=(6, 10)),
        ),
        (HDS関係("candidate-direction", starts, ends, "因果"),),
    )


class HDS関係方向試験(unittest.TestCase):
    def test_同じ語と関係種別でも逆向きは一致扱いしない(self) -> None:
        forward = _意味署名(_direction_candidate("Alpha causes Beta", reverse=False))
        reverse = _意味署名(_direction_candidate("Beta causes Alpha", reverse=True))
        evidence = _意味署名(_direction_candidate("Alpha causes Beta", reverse=False))

        self.assertEqual(forward.語, reverse.語)
        self.assertEqual(forward.関係種別, reverse.関係種別)
        self.assertEqual(_edge_similarity(forward.関係辺, evidence.関係辺), 1.0)
        self.assertEqual(_edge_similarity(reverse.関係辺, evidence.関係辺), 0.0)

    def test_Dataが支持する関係方向を選択する(self) -> None:
        core = K3相当能力核()
        data_ir = _ir(
            "Alpha causes Beta.",
            (
                HDS座標("alpha", "対象.実体", "Alpha", 原文範囲=(0, 5)),
                HDS座標("beta", "対象.実体", "Beta", 原文範囲=(13, 17)),
            ),
            (HDS関係("data-direction", ("alpha",), ("beta",), "因果"),),
        )
        HDSIR知識Adapter(core).投入(data_ir, provenance=("test-data", "doc:direction"))

        question_ir = _ir(
            "Which causal direction is supported?",
            (
                HDS座標("alpha", "対象.実体", "Alpha"),
                HDS座標("beta", "対象.実体", "Beta"),
                HDS座標("choice:A", "目的.候補", "Alpha causes Beta"),
                HDS座標("choice:B", "目的.候補", "Beta causes Alpha"),
            ),
        )
        candidates = {
            "A": _direction_candidate("Alpha causes Beta", reverse=False),
            "B": _direction_candidate("Beta causes Alpha", reverse=True),
        }

        result = HDSIRネイティブAdapter(core).実行(question_ir, 候補IR=candidates)

        self.assertEqual(result.状態, "APPROVE")
        self.assertEqual(result.回答ラベル, "A")
        diagnostics = {item.候補: item for item in result.候補診断}
        self.assertGreater(diagnostics["A"].証拠得点, diagnostics["B"].証拠得点)
        self.assertGreaterEqual(diagnostics["A"].識別一致出典数, 1)


if __name__ == "__main__":
    unittest.main()

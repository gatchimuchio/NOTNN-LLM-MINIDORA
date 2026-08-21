from __future__ import annotations

import unittest

from minidora.hds_effort import HDS努力水準, HDS探索方針選択
from minidora.hds_ir import HDSIR, HDS実行核, HDS座標, HDS関係, HDS残差
from minidora.k3_hds_native import HDSIRネイティブAdapter


def _ir(*, choices: int = 2, relations: int = 0, residuals: int = 0) -> HDSIR:
    coords = [HDS座標("target", "対象.実体", "Alpha")]
    for index in range(choices):
        coords.append(HDS座標(f"choice:{chr(65 + index)}", "目的.候補", f"option{index}"))
    rels = tuple(
        HDS関係(f"r{index}", ("target",), ("target",), "関連")
        for index in range(relations)
    )
    res = tuple(
        HDS残差(f"res:{index}", "unknown", "x", "unresolved")
        for index in range(residuals)
    )
    return HDSIR(
        原文="Which option belongs to Alpha?",
        正規化文="Which option belongs to Alpha?",
        認知世界ID="effort:test",
        座標=tuple(coords),
        関係=rels,
        残差=res,
        意味作用履歴=(),
        実行核=HDS実行核("choice"),
        種別="knowledge_query",
        閉包状態="CLOSED_FOR_SEMANTIC_TRANSFER",
        入力言語="en",
    )


class HDS努力制御試験(unittest.TestCase):
    def test_単純構造はlow(self) -> None:
        ir = _ir(choices=2)
        self.assertEqual(HDS努力水準(ir), "low")
        policy = HDS探索方針選択(ir)
        self.assertEqual(policy.水準, "low")
        self.assertEqual(policy.証拠上限, 3)
        self.assertEqual(policy.graph深さ上限, 6)

    def test_4候補は最低high(self) -> None:
        ir = _ir(choices=4)
        self.assertEqual(HDS努力水準(ir), "high")
        policy = HDS探索方針選択(ir)
        self.assertEqual(policy.水準, "high")
        self.assertGreaterEqual(policy.証拠上限, 5)
        self.assertGreaterEqual(policy.graph深さ上限, 8)

    def test_関係密度が高ければmax(self) -> None:
        ir = _ir(choices=4, relations=4)
        self.assertEqual(HDS努力水準(ir), "max")
        policy = HDS探索方針選択(ir)
        self.assertEqual(policy.水準, "max")
        self.assertEqual(policy.証拠上限, 8)
        self.assertEqual(policy.graph深さ上限, 10)

    def test_明示努力指定をAdapter結果へ反映する(self) -> None:
        ir = _ir(choices=2)
        result = HDSIRネイティブAdapter().実行(ir, 努力="max")
        self.assertEqual(result.状態, "SUSPEND")
        self.assertEqual(result.努力水準, "max")
        self.assertEqual(result.探索深さ上限, 10)
        self.assertEqual(result.証拠上限, 8)


if __name__ == "__main__":
    unittest.main()

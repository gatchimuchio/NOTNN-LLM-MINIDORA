from __future__ import annotations

import unittest

from minidora.k3_functional import Candidate
from minidora.k3_hds_native import HDS候補診断, _例外消去候補


def _candidate(label: str, confidence: float = 0.8) -> Candidate:
    return Candidate(
        answer=label,
        relation="test",
        confidence=confidence,
        expert="fixture",
        proof_fact_ids=(f"fact:{label}",),
        provenance=("fixture",),
    )


def _diag(label: str, sources: int = 1, proofs: int = 1) -> HDS候補診断:
    return HDS候補診断(
        候補=label,
        合計得点=3.0,
        証拠得点=3.0,
        graph得点=0.0,
        graph補正係数=0.0,
        独立出典数=sources,
        採用証拠数=1,
        graph深さ=None,
        根拠事実数=proofs,
        識別語数=1,
    )


class K3例外消去試験(unittest.TestCase):
    def test_4択中3択が独立根拠付きなら残り1択を消去できる(self) -> None:
        choices = (("A", "a"), ("B", "b"), ("C", "c"), ("D", "d"))
        scored = [(3.0, _candidate("A")), (2.9, _candidate("B")), (2.8, _candidate("C"))]
        diagnostics = (_diag("A"), _diag("B"), _diag("C"), _diag("D", sources=0, proofs=0))
        result = _例外消去候補(choices, scored, diagnostics)
        self.assertIsNotNone(result)
        self.assertEqual(result.answer, "D")
        self.assertEqual(set(result.proof_fact_ids), {"fact:A", "fact:B", "fact:C"})

    def test_未確認候補が2択残るなら消去しない(self) -> None:
        choices = (("A", "a"), ("B", "b"), ("C", "c"), ("D", "d"))
        scored = [(3.0, _candidate("A")), (2.9, _candidate("B"))]
        diagnostics = (_diag("A"), _diag("B"), _diag("C", 0, 0), _diag("D", 0, 0))
        self.assertIsNone(_例外消去候補(choices, scored, diagnostics))

    def test_全候補に根拠がある時は最小得点を例外扱いしない(self) -> None:
        choices = (("A", "a"), ("B", "b"), ("C", "c"), ("D", "d"))
        scored = [(3.0, _candidate("A")), (2.9, _candidate("B")), (2.8, _candidate("C")), (0.5, _candidate("D"))]
        diagnostics = (_diag("A"), _diag("B"), _diag("C"), _diag("D"))
        self.assertIsNone(_例外消去候補(choices, scored, diagnostics))

    def test_独立出典が無い候補は確認済みに数えない(self) -> None:
        choices = (("A", "a"), ("B", "b"), ("C", "c"))
        scored = [(3.0, _candidate("A")), (2.9, _candidate("B"))]
        diagnostics = (_diag("A"), _diag("B", sources=0), _diag("C", sources=0, proofs=0))
        self.assertIsNone(_例外消去候補(choices, scored, diagnostics))


if __name__ == "__main__":
    unittest.main()

import unittest

from minidora.hds_ir import HDSIR, HDS実行核, HDS座標
from minidora.k3_functional import K3相当能力核
from minidora.k3_hds_native import HDSIRネイティブAdapter


def _ir(question: str, choices: dict[str, str]) -> HDSIR:
    coords = tuple(HDS座標(f"choice:{label}", "目的.候補", text) for label, text in choices.items())
    return HDSIR(
        原文=question,
        正規化文=question,
        認知世界ID="test",
        座標=coords,
        関係=(),
        残差=(),
        意味作用履歴=(),
        実行核=HDS実行核("意味構造転送"),
        種別="意味構造",
        閉包状態="CLOSED_FOR_SEMANTIC_TRANSFER",
        入力言語="en",
    )


class HDSIRネイティブK3試験(unittest.TestCase):
    def test_K根拠が無ければ推測せず保留(self):
        result = HDSIRネイティブAdapter(K3相当能力核()).実行(
            _ir("What does alpha use?", {"A": "engine", "B": "stone"})
        )
        self.assertEqual(result.状態, "SUSPEND")
        self.assertIsNone(result.回答ラベル)
        self.assertIn("NO_KNOWLEDGE_EVIDENCE", result.理由)

    def test_HDS候補をK根拠で一意選択(self):
        core = K3相当能力核()
        core.知識投入(("alpha uses engine.",))
        result = HDSIRネイティブAdapter(core).実行(
            _ir("What does alpha use?", {"A": "engine", "B": "stone"})
        )
        self.assertEqual(result.状態, "APPROVE")
        self.assertEqual(result.回答ラベル, "A")
        self.assertGreater(result.根拠事実数, 0)

    def test_同率根拠は選ばない(self):
        core = K3相当能力核()
        core.知識投入(("alpha uses engine.", "alpha uses stone."))
        result = HDSIRネイティブAdapter(core).実行(
            _ir("What does alpha use?", {"A": "engine", "B": "stone"})
        )
        self.assertEqual(result.状態, "SUSPEND")
        self.assertIsNone(result.回答ラベル)
        self.assertIn("AMBIGUOUS_EVIDENCE", result.理由)


if __name__ == "__main__":
    unittest.main()

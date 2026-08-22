from __future__ import annotations

import unittest

from minidora.hds_data_k import HDSIR知識Adapter, HDS証拠事実
from minidora.hds_ir import HDSIR, HDS実行核, HDS座標, HDS関係, HDS残差
from minidora.k3_functional import K3相当能力核
from minidora.k3_hds_native import HDSIRネイティブAdapter


def _ir(
    text: str,
    coords: tuple[HDS座標, ...],
    relations: tuple[HDS関係, ...] = (),
    residuals: tuple[HDS残差, ...] = (),
) -> HDSIR:
    return HDSIR(
        原文=text,
        正規化文=text,
        認知世界ID="residual-evidence-test",
        座標=coords,
        関係=relations,
        残差=residuals,
        意味作用履歴=(),
        実行核=HDS実行核("意味構造転送"),
        種別="意味構造",
        閉包状態="CLOSED_FOR_SEMANTIC_TRANSFER",
        入力言語="en",
    )


def _question() -> tuple[HDSIR, dict[str, HDSIR]]:
    question = _ir(
        "What does Alpha use?",
        (
            HDS座標("q-alpha", "対象.実体", "Alpha", 原文範囲=(10, 15)),
            HDS座標("choice:A", "目的.候補", "engine"),
            HDS座標("choice:B", "目的.候補", "stone"),
        ),
    )
    choices = {
        "A": _ir("engine", (HDS座標("a", "対象.実体", "engine", 原文範囲=(0, 6)),)),
        "B": _ir("stone", (HDS座標("b", "対象.実体", "stone", 原文範囲=(0, 5)),)),
    }
    return question, choices


def _data(residuals: tuple[HDS残差, ...]) -> HDSIR:
    return _ir(
        "Alpha uses engine; note uncertain.",
        (
            HDS座標("alpha", "対象.実体", "Alpha", 原文範囲=(0, 5)),
            HDS座標("engine", "対象.実体", "engine", 原文範囲=(11, 17)),
            HDS座標("note", "文脈.注記", "uncertain note", 原文範囲=(19, 33)),
        ),
        (HDS関係("use", ("alpha",), ("engine",), "作用"),),
        residuals,
    )


class HDS残差証拠境界試験(unittest.TestCase):
    def test_semantic_lossはsource全体を確定証拠へ昇格させない(self) -> None:
        core = K3相当能力核()
        data = _data((HDS残差("res:loss", "semantic_loss", "Alpha uses engine", "意味構造を保持できない"),))
        ingest = HDSIR知識Adapter(core).投入(data, provenance=("fixture", "doc:loss"))
        question, choices = _question()
        result = HDSIRネイティブAdapter(core).実行(question, 候補IR=choices)

        self.assertTrue(ingest.semantic_loss)
        self.assertGreater(ingest.証拠阻害事実数, 0)
        self.assertEqual(result.状態, "SUSPEND", result.候補診断)
        self.assertIsNone(result.回答ラベル)
        self.assertTrue(any("residual_blocked:semantic_loss" in fact.provenance for fact in HDS証拠事実(core)))

    def test_影響座標だけを局所留保し無関係な確定関係は使える(self) -> None:
        core = K3相当能力核()
        data = _data((HDS残差("res:note", "note_unresolved", "uncertain note", "注記だけ未解", 影響座標=("note",)),))
        ingest = HDSIR知識Adapter(core).投入(data, provenance=("fixture", "doc:local"))
        question, choices = _question()
        result = HDSIRネイティブAdapter(core).実行(question, 候補IR=choices)

        self.assertFalse(ingest.semantic_loss)
        self.assertGreaterEqual(ingest.証拠阻害事実数, 1)
        self.assertEqual(result.状態, "APPROVE", result.候補診断)
        self.assertEqual(result.回答ラベル, "A", result.候補診断)

    def test_関係終点が残差影響ならその関係を確定根拠にしない(self) -> None:
        core = K3相当能力核()
        data = _data((HDS残差("res:engine", "entity_unresolved", "engine", "対象同定未解", 影響座標=("engine",)),))
        HDSIR知識Adapter(core).投入(data, provenance=("fixture", "doc:blocked-edge"))
        question, choices = _question()
        result = HDSIRネイティブAdapter(core).実行(question, 候補IR=choices)

        self.assertEqual(result.状態, "SUSPEND", result.候補診断)
        self.assertIsNone(result.回答ラベル)


if __name__ == "__main__":
    unittest.main()

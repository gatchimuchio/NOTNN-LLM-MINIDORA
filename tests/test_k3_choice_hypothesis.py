from __future__ import annotations

import unittest

from minidora.hds_data_k import HDSIR知識Adapter
from minidora.hds_ir import HDSIR, HDS実行核, HDS座標, HDS関係, 値状態
from minidora.k3_functional import K3相当能力核
from minidora.k3_hds_native import HDSIRネイティブAdapter, _候補仮説関係


def _ir(
    text: str,
    coords: tuple[HDS座標, ...],
    relations: tuple[HDS関係, ...] = (),
) -> HDSIR:
    return HDSIR(
        原文=text,
        正規化文=text,
        認知世界ID="choice-hypothesis-test",
        座標=coords,
        関係=relations,
        残差=(),
        意味作用履歴=(),
        実行核=HDS実行核("意味構造転送"),
        種別="意味構造",
        閉包状態="CLOSED_FOR_SEMANTIC_TRANSFER",
        入力言語="en",
    )


def _候補(label: str, text: str) -> tuple[str, HDSIR]:
    return label, _ir(text, (HDS座標("candidate", "対象.実体", text),))


class HDS候補仮説射影試験(unittest.TestCase):
    def test_未知始点へ候補を代入し同一文書内の関係差を識別する(self) -> None:
        core = K3相当能力核()
        data = _ir(
            "Regulator A activates Target X; Regulator B inhibits Target X.",
            (
                HDS座標("a", "対象.実体", "Regulator A"),
                HDS座標("b", "対象.実体", "Regulator B"),
                HDS座標("target", "対象.実体", "Target X"),
            ),
            (
                HDS関係("ra", ("a",), ("target",), "活性化"),
                HDS関係("rb", ("b",), ("target",), "阻害"),
            ),
        )
        HDSIR知識Adapter(core).投入(data, provenance=("fixture", "doc:mixed"))

        question = _ir(
            "Which regulator inhibits Target X?",
            (
                HDS座標("unknown", "目的.未知始点", "regulator", 値状態.未観測),
                HDS座標("target", "対象.終点", "Target X"),
                HDS座標("choice:A", "目的.候補", "Regulator A"),
                HDS座標("choice:B", "目的.候補", "Regulator B"),
            ),
            (
                HDS関係(
                    "q", ("unknown",), ("target",), "阻害",
                    値状態=値状態.未観測,
                    条件=("検索述語=inhibits", "不足位置=始点"),
                ),
            ),
        )
        candidates = dict((_候補("A", "Regulator A"), _候補("B", "Regulator B")))
        result = HDSIRネイティブAdapter(core).実行(question, 候補IR=candidates)
        print("HYPOTHESIS_DIAGNOSTICS", [
            {
                "label": row.候補,
                "total": row.合計得点,
                "evidence": row.証拠得点,
                "graph": row.graph得点,
                "sources": row.独立出典数,
                "distinctive_sources": row.識別一致出典数,
                "facts": row.根拠事実数,
            }
            for row in result.候補診断
        ])

        self.assertEqual(result.状態, "APPROVE")
        self.assertEqual(result.回答ラベル, "B")
        diagnostics = {row.候補: row for row in result.候補診断}
        self.assertGreater(diagnostics["B"].合計得点, diagnostics["A"].合計得点)

    def test_未知終点へ候補を代入し関係方向を保持する(self) -> None:
        core = K3相当能力核()
        data = _ir(
            "Alpha uses Engine; Alpha contains Stone.",
            (
                HDS座標("alpha", "対象.実体", "Alpha"),
                HDS座標("engine", "対象.実体", "Engine"),
                HDS座標("stone", "対象.実体", "Stone"),
            ),
            (
                HDS関係("use", ("alpha",), ("engine",), "使用"),
                HDS関係("contain", ("alpha",), ("stone",), "包含"),
            ),
        )
        HDSIR知識Adapter(core).投入(data, provenance=("fixture", "doc:mixed"))

        question = _ir(
            "What does Alpha use?",
            (
                HDS座標("alpha", "対象.始点", "Alpha"),
                HDS座標("unknown", "目的.未知終点", "object", 値状態.未観測),
                HDS座標("choice:A", "目的.候補", "Engine"),
                HDS座標("choice:B", "目的.候補", "Stone"),
            ),
            (
                HDS関係(
                    "q", ("alpha",), ("unknown",), "使用",
                    値状態=値状態.未観測,
                    条件=("検索述語=uses", "不足位置=終点"),
                ),
            ),
        )
        candidates = dict((_候補("A", "Engine"), _候補("B", "Stone")))
        result = HDSIRネイティブAdapter(core).実行(question, 候補IR=candidates)

        self.assertEqual(result.状態, "APPROVE")
        self.assertEqual(result.回答ラベル, "A")

    def test_不足位置が明示されない問いから候補関係を捏造しない(self) -> None:
        question = _ir(
            "Alpha and Beta are discussed.",
            (
                HDS座標("alpha", "対象.実体", "Alpha"),
                HDS座標("beta", "対象.実体", "Beta"),
                HDS座標("choice:A", "目的.候補", "Engine"),
                HDS座標("choice:B", "目的.候補", "Stone"),
            ),
            (HDS関係("r", ("alpha",), ("beta",), "相関"),),
        )
        relations, edges = _候補仮説関係(question, "Engine")
        self.assertEqual(relations, frozenset())
        self.assertEqual(edges, ())


if __name__ == "__main__":
    unittest.main()

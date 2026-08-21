from __future__ import annotations

import unittest

from minidora.hds_data_k import HDSIR知識Adapter
from minidora.hds_ir import HDSIR, HDS実行核, HDS座標, HDS関係
from minidora.k3_functional import K3相当能力核
from minidora.k3_hds_native import HDSIRネイティブAdapter


def _ir(text: str, coords: tuple[HDS座標, ...], relations: tuple[HDS関係, ...] = ()) -> HDSIR:
    return HDSIR(
        原文=text,
        正規化文=text,
        認知世界ID="test",
        座標=coords,
        関係=relations,
        残差=(),
        意味作用履歴=(),
        実行核=HDS実行核("意味構造転送"),
        種別="意味構造",
        閉包状態="CLOSED_FOR_SEMANTIC_TRANSFER",
        入力言語="en",
    )


class HDS構造照合試験(unittest.TestCase):
    def test_問題候補Dataを全てHDS構造で照合する(self) -> None:
        core = K3相当能力核()
        data_ir = _ir(
            "Alpha uses an engine.",
            (
                HDS座標("alpha", "対象.実体", "Alpha", 原文範囲=(0, 5)),
                HDS座標("use", "関係.述語表層", "uses", 原文範囲=(6, 10)),
                HDS座標("engine", "対象.実体", "engine", 原文範囲=(14, 20)),
            ),
            (HDS関係("r", ("alpha",), ("engine",), "作用"),),
        )
        HDSIR知識Adapter(core).投入(data_ir, provenance=("test-data", "doc:1"))

        question_ir = _ir(
            "What does Alpha use?",
            (
                HDS座標("q-alpha", "対象.実体", "Alpha", 原文範囲=(10, 15)),
                HDS座標("q-use", "関係.述語表層", "use", 原文範囲=(16, 19)),
                HDS座標("choice:A", "目的.候補", "engine"),
                HDS座標("choice:B", "目的.候補", "stone"),
            ),
            (HDS関係("qr", ("q-alpha",), ("q-use",), "記述→問い"),),
        )
        candidate_irs = {
            "A": _ir("engine", (HDS座標("a", "対象.実体", "engine", 原文範囲=(0, 6)),)),
            "B": _ir("stone", (HDS座標("b", "対象.実体", "stone", 原文範囲=(0, 5)),)),
        }

        result = HDSIRネイティブAdapter(core).実行(question_ir, 候補IR=candidate_irs)
        self.assertEqual(result.状態, "APPROVE")
        self.assertEqual(result.回答ラベル, "A")
        self.assertGreater(result.根拠事実数, 0)

    def test_複数HDS関係を跨いで候補へ到達する(self) -> None:
        core = K3相当能力核()
        first = _ir(
            "Alpha activates Beta.",
            (
                HDS座標("alpha", "対象.実体", "Alpha", 原文範囲=(0, 5)),
                HDS座標("beta", "対象.実体", "Beta", 原文範囲=(16, 20)),
            ),
            (HDS関係("r1", ("alpha",), ("beta",), "因果"),),
        )
        second = _ir(
            "Beta produces Engine.",
            (
                HDS座標("beta", "対象.実体", "Beta", 原文範囲=(0, 4)),
                HDS座標("engine", "対象.実体", "Engine", 原文範囲=(14, 20)),
            ),
            (HDS関係("r2", ("beta",), ("engine",), "因果"),),
        )
        HDSIR知識Adapter(core).投入(first, provenance=("test-data", "doc:1"))
        HDSIR知識Adapter(core).投入(second, provenance=("test-data", "doc:2"))

        question_ir = _ir(
            "What follows from Alpha?",
            (
                HDS座標("alpha", "対象.実体", "Alpha", 原文範囲=(18, 23)),
                HDS座標("choice:A", "目的.候補", "Engine"),
                HDS座標("choice:B", "目的.候補", "Stone"),
            ),
        )
        candidate_irs = {
            "A": _ir("Engine", (HDS座標("a", "対象.実体", "Engine", 原文範囲=(0, 6)),)),
            "B": _ir("Stone", (HDS座標("b", "対象.実体", "Stone", 原文範囲=(0, 5)),)),
        }
        result = HDSIRネイティブAdapter(core).実行(question_ir, 候補IR=candidate_irs)
        self.assertEqual(result.状態, "APPROVE")
        self.assertEqual(result.回答ラベル, "A")
        self.assertGreaterEqual(result.根拠事実数, 2)

    def test_関係が一致し候補差が無いなら推測しない(self) -> None:
        core = K3相当能力核()
        for doc_id, obj in (("1", "engine"), ("2", "stone")):
            data_ir = _ir(
                f"Alpha uses {obj}.",
                (
                    HDS座標("alpha", "対象.実体", "Alpha", 原文範囲=(0, 5)),
                    HDS座標("use", "関係.述語表層", "uses", 原文範囲=(6, 10)),
                    HDS座標("obj", "対象.実体", obj, 原文範囲=(11, 11 + len(obj))),
                ),
                (HDS関係("r", ("alpha",), ("obj",), "作用"),),
            )
            HDSIR知識Adapter(core).投入(data_ir, provenance=("test-data", "doc:" + doc_id))

        question_ir = _ir(
            "What does Alpha use?",
            (
                HDS座標("q-alpha", "対象.実体", "Alpha", 原文範囲=(10, 15)),
                HDS座標("choice:A", "目的.候補", "engine"),
                HDS座標("choice:B", "目的.候補", "stone"),
            ),
        )
        candidate_irs = {
            "A": _ir("engine", (HDS座標("a", "対象.実体", "engine", 原文範囲=(0, 6)),)),
            "B": _ir("stone", (HDS座標("b", "対象.実体", "stone", 原文範囲=(0, 5)),)),
        }
        result = HDSIRネイティブAdapter(core).実行(question_ir, 候補IR=candidate_irs)
        self.assertEqual(result.状態, "SUSPEND")
        self.assertIsNone(result.回答ラベル)
        self.assertIn("AMBIGUOUS_EVIDENCE", result.理由)


if __name__ == "__main__":
    unittest.main()

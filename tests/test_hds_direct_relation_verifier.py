from __future__ import annotations

import unittest

from minidora.hds_choice_hypothesis import HDS候補代入仮説群
from minidora.hds_data_k import HDSIR知識Adapter
from minidora.hds_direct_relation_verifier import HDS直接関係検証
from minidora.hds_ir import HDSIR, HDS実行核, HDS座標, HDS関係, 値状態
from minidora.k3_functional import K3相当能力核


def _ir(text: str, coords: tuple[HDS座標, ...], relations: tuple[HDS関係, ...] = ()) -> HDSIR:
    return HDSIR(
        原文=text,
        正規化文=text,
        認知世界ID="direct-relation-verifier-test",
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
            HDS座標("alpha", "対象.始点", "Alpha"),
            HDS座標("unknown", "目的.未知終点", "object", 値状態.未観測),
            HDS座標("choice:A", "目的.候補", "engine"),
            HDS座標("choice:B", "目的.候補", "stone"),
        ),
        (
            HDS関係(
                "qrel", ("alpha",), ("unknown",), "使用",
                条件=("検索述語=uses", "不足位置=終点"), 値状態=値状態.未観測,
            ),
        ),
    )


def _candidates(question: HDSIR) -> dict[str, HDSIR]:
    raw = {
        "A": _ir("engine", (HDS座標("a", "対象.実体", "engine"),)),
        "B": _ir("stone", (HDS座標("b", "対象.実体", "stone"),)),
    }
    return HDS候補代入仮説群(question, raw)


def _data(subject: str, obj: str) -> HDSIR:
    return _ir(
        f"{subject} uses {obj}.",
        (
            HDS座標("s", "対象.実体", subject),
            HDS座標("o", "対象.実体", obj),
        ),
        (HDS関係("r", ("s",), ("o",), "使用"),),
    )


class HDS直接関係検証試験(unittest.TestCase):
    def test_同じ関係種別でも始点が違えば支持しない(self) -> None:
        question = _question()
        core = K3相当能力核()
        HDSIR知識Adapter(core).投入(_data("Beta", "engine"), provenance=("fixture", "doc:beta"))
        candidate, diagnostics = HDS直接関係検証(core, _candidates(question))
        self.assertIsNone(candidate)
        self.assertTrue(all(item.得点 == 0.0 for item in diagnostics))

    def test_始点関係終点が一致した候補だけを選ぶ(self) -> None:
        question = _question()
        core = K3相当能力核()
        HDSIR知識Adapter(core).投入(_data("Alpha", "engine"), provenance=("fixture", "doc:engine"))
        candidate, diagnostics = HDS直接関係検証(core, _candidates(question))
        self.assertIsNotNone(candidate)
        assert candidate is not None
        self.assertEqual(candidate.answer, "A")
        self.assertTrue(candidate.proof_fact_ids)
        a = next(item for item in diagnostics if item.候補 == "A")
        b = next(item for item in diagnostics if item.候補 == "B")
        self.assertGreater(a.得点, b.得点)

    def test_競合候補も同じ問い関係で支持されれば決め打ちしない(self) -> None:
        question = _question()
        core = K3相当能力核()
        adapter = HDSIR知識Adapter(core)
        adapter.投入(_data("Alpha", "engine"), provenance=("fixture", "doc:engine"))
        adapter.投入(_data("Alpha", "stone"), provenance=("fixture", "doc:stone"))
        candidate, diagnostics = HDS直接関係検証(core, _candidates(question))
        self.assertIsNone(candidate)
        self.assertGreater(next(x for x in diagnostics if x.候補 == "A").得点, 0.0)
        self.assertGreater(next(x for x in diagnostics if x.候補 == "B").得点, 0.0)

    def test_同一sourceの複数Factを独立根拠として水増ししない(self) -> None:
        question = _question()
        core = K3相当能力核()
        adapter = HDSIR知識Adapter(core)
        adapter.投入(_data("Alpha", "engine"), provenance=("fixture", "doc:same"))
        adapter.投入(_data("Alpha", "engine"), provenance=("fixture", "doc:same"))
        _candidate, diagnostics = HDS直接関係検証(core, _candidates(question))
        a = next(item for item in diagnostics if item.候補 == "A")
        self.assertEqual(a.独立出典数, 1)


if __name__ == "__main__":
    unittest.main()

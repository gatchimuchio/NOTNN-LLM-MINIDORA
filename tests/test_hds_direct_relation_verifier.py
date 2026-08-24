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


def _assertion_candidate(obj: str, *, negative: bool = False, origin: str = "公開HDS Compiler") -> HDSIR:
    coords = [
        HDS座標("s", "対象.始点", "Alpha"),
        HDS座標("o", "対象.終点", obj),
    ]
    if negative:
        coords.append(HDS座標("neg", "状態.否定", "not"))
    return _ir(
        f"Alpha uses {obj}.",
        tuple(coords),
        (
            HDS関係(
                "candidate-rel", ("s",), ("o",), "使用",
                値状態=値状態.確定, 由来=origin,
            ),
        ),
    )


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

    def test_候補自身の完全命題は二独立sourceで直接検証できる(self) -> None:
        core = K3相当能力核()
        adapter = HDSIR知識Adapter(core)
        adapter.投入(_data("Alpha", "engine"), provenance=("fixture", "doc:1"))
        adapter.投入(_data("Alpha", "engine"), provenance=("fixture", "doc:2"))
        candidates = {
            "A": _assertion_candidate("engine"),
            "B": _assertion_candidate("stone"),
        }
        candidate, diagnostics = HDS直接関係検証(core, candidates)
        self.assertIsNotNone(candidate)
        assert candidate is not None
        self.assertEqual(candidate.answer, "A")
        a = next(item for item in diagnostics if item.候補 == "A")
        self.assertEqual(a.命題一致出典数, 2)
        self.assertEqual(a.仮説一致出典数, 0)

    def test_共有言語基底P由来の安全な完全命題も二独立sourceで検証する(self) -> None:
        core = K3相当能力核()
        adapter = HDSIR知識Adapter(core)
        adapter.投入(_data("Alpha", "engine"), provenance=("fixture", "doc:1"))
        adapter.投入(_data("Alpha", "engine"), provenance=("fixture", "doc:2"))
        candidates = {
            "A": _assertion_candidate("engine", origin="共有言語基底P"),
            "B": _assertion_candidate("stone", origin="共有言語基底P"),
        }
        candidate, diagnostics = HDS直接関係検証(core, candidates)
        self.assertIsNotNone(candidate)
        assert candidate is not None
        self.assertEqual(candidate.answer, "A")
        a = next(item for item in diagnostics if item.候補 == "A")
        self.assertEqual(a.命題一致出典数, 2)

    def test_Runtimeや未知由来の候補関係を命題として採用しない(self) -> None:
        core = K3相当能力核()
        adapter = HDSIR知識Adapter(core)
        adapter.投入(_data("Alpha", "engine"), provenance=("fixture", "doc:1"))
        adapter.投入(_data("Alpha", "engine"), provenance=("fixture", "doc:2"))
        candidates = {
            "A": _assertion_candidate("engine", origin="HDS Runtime K質問射影"),
            "B": _assertion_candidate("stone", origin="HDS Runtime K質問射影"),
        }
        candidate, diagnostics = HDS直接関係検証(core, candidates)
        self.assertIsNone(candidate)
        self.assertTrue(all(item.命題一致出典数 == 0 for item in diagnostics))

    def test_完全命題は単一sourceだけでは決め打ちしない(self) -> None:
        core = K3相当能力核()
        HDSIR知識Adapter(core).投入(_data("Alpha", "engine"), provenance=("fixture", "doc:1"))
        candidates = {
            "A": _assertion_candidate("engine"),
            "B": _assertion_candidate("stone"),
        }
        candidate, diagnostics = HDS直接関係検証(core, candidates)
        self.assertIsNone(candidate)
        self.assertEqual(next(item for item in diagnostics if item.候補 == "A").命題一致出典数, 1)

    def test_否定候補を肯定Dataから直接証明しない(self) -> None:
        core = K3相当能力核()
        adapter = HDSIR知識Adapter(core)
        adapter.投入(_data("Alpha", "engine"), provenance=("fixture", "doc:1"))
        adapter.投入(_data("Alpha", "engine"), provenance=("fixture", "doc:2"))
        candidates = {
            "A": _assertion_candidate("engine", negative=True),
            "B": _assertion_candidate("stone"),
        }
        candidate, diagnostics = HDS直接関係検証(core, candidates)
        self.assertIsNone(candidate)
        self.assertEqual(next(item for item in diagnostics if item.候補 == "A").得点, 0.0)


if __name__ == "__main__":
    unittest.main()

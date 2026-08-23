from __future__ import annotations

import unittest

from minidora.hds_choice_hypothesis import HDS候補代入仮説, HDS候補代入仮説群
from minidora.hds_data_k import HDSIR知識Adapter
from minidora.hds_ir import HDSIR, HDS実行核, HDS座標, HDS関係, 値状態
from minidora.k3_functional import K3相当能力核
from minidora.k3_hds_native import HDSIRネイティブAdapter


def _ir(text: str, coords: tuple[HDS座標, ...], relations: tuple[HDS関係, ...] = ()) -> HDSIR:
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


def _candidate(text: str) -> HDSIR:
    return _ir(text, (HDS座標("candidate", "対象.実体", text),))


class HDS候補代入仮説試験(unittest.TestCase):
    def test_未知終点へ候補を代入して有向関係を作る(self) -> None:
        question = _ir(
            "What does Alpha use?",
            (
                HDS座標("alpha", "対象.始点", "Alpha"),
                HDS座標("unknown", "目的.未知終点", "object", 値状態.未観測),
            ),
            (
                HDS関係(
                    "qrel", ("alpha",), ("unknown",), "使用",
                    条件=("検索述語=uses", "不足位置=終点"), 値状態=値状態.未観測,
                ),
            ),
        )
        result = HDS候補代入仮説(question, "A", _candidate("engine"))
        coords = result.座標辞書()
        hypothesis = [relation for relation in result.関係 if relation.由来 == "HDS候補代入仮説"]
        self.assertEqual(len(hypothesis), 1)
        relation = hypothesis[0]
        self.assertEqual(relation.種別, "使用")
        self.assertEqual(relation.値状態, 値状態.推定)
        self.assertEqual(str(coords[relation.始点[0]].内容), "Alpha")
        self.assertEqual(str(coords[relation.終点[0]].内容), "engine")

    def test_未知始点へ候補を代入して方向を保持する(self) -> None:
        question = _ir(
            "What produces Product?",
            (
                HDS座標("unknown", "目的.未知始点", "agent", 値状態.未観測),
                HDS座標("product", "対象.終点", "Product"),
            ),
            (
                HDS関係(
                    "qrel", ("unknown",), ("product",), "生成",
                    条件=("検索述語=produces", "不足位置=始点"), 値状態=値状態.未観測,
                ),
            ),
        )
        result = HDS候補代入仮説(question, "B", _candidate("Enzyme"))
        coords = result.座標辞書()
        relation = next(relation for relation in result.関係 if relation.由来 == "HDS候補代入仮説")
        self.assertEqual(str(coords[relation.始点[0]].内容), "Enzyme")
        self.assertEqual(str(coords[relation.終点[0]].内容), "Product")

    def test_不足位置が明示されない問いへは介入しない(self) -> None:
        question = _ir(
            "Which option applies?",
            (HDS座標("alpha", "対象.実体", "Alpha"),),
        )
        candidate = _candidate("engine")
        self.assertIs(HDS候補代入仮説(question, "A", candidate), candidate)

    def test_語集合が同一文書に共存しても関係端点で候補を分別する(self) -> None:
        core = K3相当能力核()
        data = _ir(
            "Alpha uses engine; stone is also mentioned.",
            (
                HDS座標("alpha", "対象.実体", "Alpha"),
                HDS座標("engine", "対象.実体", "engine"),
                HDS座標("stone", "対象.実体", "stone"),
            ),
            (HDS関係("rel", ("alpha",), ("engine",), "使用"),),
        )
        HDSIR知識Adapter(core).投入(data, provenance=("fixture", "doc:relation"))

        question = _ir(
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
        candidates = HDS候補代入仮説群(question, {"A": _candidate("engine"), "B": _candidate("stone")})
        result = HDSIRネイティブAdapter(core).実行(question, 候補IR=candidates)
        self.assertEqual(result.状態, "APPROVE")
        self.assertEqual(result.回答ラベル, "A")
        a = next(item for item in result.候補診断 if item.候補 == "A")
        b = next(item for item in result.候補診断 if item.候補 == "B")
        self.assertGreater(a.合計得点, b.合計得点)


if __name__ == "__main__":
    unittest.main()

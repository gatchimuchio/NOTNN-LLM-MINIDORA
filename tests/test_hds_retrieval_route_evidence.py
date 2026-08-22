from __future__ import annotations

import unittest

from minidora.hds_choice_runtime import _検索経路証拠
from minidora.hds_ir import HDSIR, HDS実行核, HDS座標, 値状態
from minidora.参照 import 参照記録


def _question() -> HDSIR:
    return HDSIR(
        原文="Which function belongs to ProteinX?",
        正規化文="Which function belongs to ProteinX?",
        認知世界ID="route-evidence-test",
        座標=(
            HDS座標("subject", "対象.実体", "ProteinX"),
            HDS座標("choice:A", "目的.候補", "catalysis"),
            HDS座標("choice:B", "目的.候補", "transport"),
        ),
        関係=(),
        残差=(),
        意味作用履歴=(),
        実行核=HDS実行核("HDS_choice_selection"),
        参照必須=True,
        種別="knowledge_query",
        閉包状態="CLOSED_FOR_OPERATION",
        入力言語="en",
    )


def _choices():
    return (
        ("A", "catalysis", 値状態.確定),
        ("B", "transport", 値状態.確定),
    )


def _record(identifier: str, content: str, label: str) -> 参照記録:
    return 参照記録(
        identifier,
        "ProteinX",
        content,
        f"fixture://{identifier}",
        "fixture-R",
        条件=(("hds_query_kind", "choice"), ("hds_query_choice", label)),
    )


class HDS検索経路証拠試験(unittest.TestCase):
    def test_候補query専用でも本文が候補差分に触れなければ証拠化しない(self) -> None:
        records = (
            _record("noise-1", "A weather report for the city.", "A"),
            _record("noise-2", "A map of the local railway network.", "A"),
        )
        self.assertEqual(_検索経路証拠(_question(), _choices(), records), ())

    def test_候補差分に触れる複数独立文書だけ弱い経路証拠へ昇格する(self) -> None:
        records = (
            _record("cat-1", "ProteinX catalysis is experimentally observed.", "A"),
            _record("cat-2", "Catalysis by ProteinX was independently reported.", "A"),
            _record("noise-b", "A generic ProteinX report.", "B"),
        )
        evidence = _検索経路証拠(_question(), _choices(), records)
        self.assertEqual(len(evidence), 2)
        self.assertTrue(all(record.識別子.startswith("cat-") for record, _ in evidence))

    def test_同じ資料が複数候補query由来なら固有経路証拠へしない(self) -> None:
        shared = 参照記録(
            "shared",
            "ProteinX",
            "ProteinX catalysis and transport are discussed together.",
            "fixture://shared",
            "fixture-R",
            条件=(
                ("hds_query_kind", "choice"),
                ("hds_query_choice", "A"),
                ("hds_query_choice", "B"),
            ),
        )
        self.assertEqual(_検索経路証拠(_question(), _choices(), (shared,)), ())


if __name__ == "__main__":
    unittest.main()

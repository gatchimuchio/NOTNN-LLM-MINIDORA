from __future__ import annotations

import unittest

from minidora.hds_ir import HDSIR, HDS実行核, HDS座標
from minidora.hds_reference import HDS参照問合せ候補, HDS参照検索, HDS参照縮退問合せ候補
from minidora.参照 import 参照記録


def _ir() -> HDSIR:
    return HDSIR(
        原文="Which process involving ProteinX under severe hypoxic stress is correct?",
        正規化文="Which process involving ProteinX under severe hypoxic stress is correct?",
        認知世界ID="fallback-test",
        座標=(
            HDS座標("protein", "対象.実体", "ProteinX"),
            HDS座標("relation", "関係.述語表層", "activates"),
            HDS座標("state", "状態.環境", "severe hypoxic stress"),
            HDS座標("choice:A", "目的.候補", "catalysis"),
            HDS座標("choice:B", "目的.候補", "transport"),
            HDS座標("choice:C", "目的.候補", "folding"),
            HDS座標("choice:D", "目的.候補", "signaling"),
        ),
        関係=(),
        残差=(),
        意味作用履歴=(),
        実行核=HDS実行核("参照回答"),
        参照必須=True,
        種別="knowledge_choice",
    )


class _FallbackOnlyProvider:
    並列安全 = True
    名称 = "fallback-only"

    def __init__(self) -> None:
        self.calls: list[str] = []

    def 検索(self, query: str, limit: int = 8):
        self.calls.append(query)
        # rich queryは0件。縮退した `ProteinX catalysis` だけが取得可能。
        if query == "ProteinX catalysis":
            return (
                参照記録("hit", "ProteinX", "ProteinX catalysis evidence", "fixture://hit", self.名称),
            )
        return ()


class HDS参照Fallback試験(unittest.TestCase):
    def test_縮退queryは全choiceを対称に保持する(self) -> None:
        queries = HDS参照縮退問合せ候補(_ir())
        for choice in ("catalysis", "transport", "folding", "signaling"):
            self.assertIn(f"ProteinX {choice}", queries)

    def test_主検索が完全0件の時だけ縮退検索へ進む(self) -> None:
        provider = _FallbackOnlyProvider()
        primary = HDS参照問合せ候補(_ir())
        self.assertNotIn("ProteinX catalysis", primary)

        records = HDS参照検索(provider, _ir())
        self.assertEqual([record.識別子 for record in records], ["hit"])
        self.assertTrue(all(query in provider.calls for query in primary))
        self.assertIn("ProteinX catalysis", provider.calls)

    def test_主検索で1件でも取れれば縮退検索を追加しない(self) -> None:
        target_primary = HDS参照問合せ候補(_ir())[0]

        class PrimaryProvider(_FallbackOnlyProvider):
            def 検索(self, query: str, limit: int = 8):
                self.calls.append(query)
                if query == target_primary:
                    return (
                        参照記録("primary", "ProteinX", "primary evidence", "fixture://primary", self.名称),
                    )
                return ()

        provider = PrimaryProvider()
        records = HDS参照検索(provider, _ir())
        self.assertEqual([record.識別子 for record in records], ["primary"])
        self.assertNotIn("ProteinX catalysis", provider.calls)


if __name__ == "__main__":
    unittest.main()

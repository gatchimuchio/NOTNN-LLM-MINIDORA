from __future__ import annotations

import unittest

from minidora.hds_choice_runtime import HDS選択推論実行
from minidora.hds_ir import HDSIR, HDS実行核, HDS座標, HDS関係, 値状態
from minidora.k3_functional import K3相当能力核
from minidora.参照 import 参照記録


def _ir(text: str, coords: tuple[HDS座標, ...], relations: tuple[HDS関係, ...] = ()) -> HDSIR:
    return HDSIR(
        原文=text,
        正規化文=text,
        認知世界ID="open-relation-v16",
        座標=coords,
        関係=relations,
        残差=(),
        意味作用履歴=(),
        実行核=HDS実行核("意味構造転送"),
        種別="knowledge_query",
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


def _entity(text: str) -> HDSIR:
    return _ir(text, (HDS座標("entity", "対象.実体", text),))


def _relation(text: str, start: str, end: str) -> HDSIR:
    return _ir(
        text,
        (
            HDS座標("s", "対象.始点", start),
            HDS座標("o", "対象.終点", end),
        ),
        (HDS関係("r", ("s",), ("o",), "使用", 値状態=値状態.確定, 由来="公開HDS Compiler"),),
    )


class _Compiler:
    並列安全 = True

    def コンパイル(self, text: str, **_kwargs) -> HDSIR:
        if text == "engine":
            return _entity("engine")
        if text == "stone":
            return _entity("stone")
        if text == "engine uses Alpha.":
            return _relation(text, "engine", "Alpha")
        if text == "Alpha uses stone.":
            return _relation(text, "Alpha", "stone")
        raise ValueError(text)


class 開放関係RuntimeV16試験(unittest.TestCase):
    def test_通常K比較も候補代入後の方向を使う(self) -> None:
        compiler = _Compiler()
        references = (
            参照記録("reverse", "engine", "engine uses Alpha.", "fixture://reverse", "fixture"),
            参照記録("forward", "stone", "Alpha uses stone.", "fixture://forward", "fixture"),
        )
        result = HDS選択推論実行(
            _question(),
            references,
            コンパイル=compiler.コンパイル,
            基礎能力核=K3相当能力核(),
        )
        self.assertIsNotNone(result.K3結果)
        assert result.K3結果 is not None
        diagnostics = {item.候補: item for item in result.K3結果.候補診断}
        self.assertGreater(diagnostics["B"].証拠得点, diagnostics["A"].証拠得点)
        self.assertEqual(result.回答ラベル, "B")


if __name__ == "__main__":
    unittest.main()

from __future__ import annotations

import unittest

from minidora.hds_ir import HDSIR, HDS実行核, HDS座標, HDS関係, HDS残差, 値状態
from minidora.hds_model_projection import (
    HDS内部言語状態,
    HDS構造固定模型核,
    HDS構造固定言語状態,
)
from minidora.模型 import 標準模型核


def ir(text, coords=(), relations=(), residuals=()):
    return HDSIR(
        原文=text,
        正規化文=text,
        認知世界ID="compiled-boundary-test",
        座標=tuple(coords),
        関係=tuple(relations),
        残差=tuple(residuals),
        意味作用履歴=(),
        実行核=HDS実行核("意味構造転送"),
        種別="意味構造",
        閉包状態="CLOSED_FOR_SEMANTIC_TRANSFER",
        入力言語="en",
    )


class HDS構文化済み模型境界試験(unittest.TestCase):
    def test_HDS構造固定状態はraw本文から関係を再生成しない(self):
        state = HDS構造固定言語状態("Alpha uses engine.", "自然言語:en", "fixed", ())
        core = HDS構造固定模型核(標準模型核())
        internal = core.言語対応.内部化(state)
        self.assertFalse(internal.関係構造)
        self.assertIn("alpha", internal.意味語集合)
        self.assertIn("engine", internal.意味語集合)

    def test_semantic_lossは模型参照で意味語も関係も復活しない(self):
        data = ir(
            "Alpha uses engine.",
            (
                HDS座標("alpha", "対象.実体", "Alpha"),
                HDS座標("engine", "対象.実体", "engine"),
            ),
            (HDS関係("use", ("alpha",), ("engine",), "使用", 値状態=値状態.確定),),
            (HDS残差("loss", "semantic_loss", "Alpha uses engine", "意味構造を保持できない"),),
        )
        state = HDS内部言語状態(data, 識別子="loss", 言語体系="自然言語:en", 証拠境界=True)
        core = HDS構造固定模型核(標準模型核())
        internal = core.言語対応.内部化(state)
        self.assertEqual(state.内容, "")
        self.assertFalse(internal.意味語集合)
        self.assertFalse(internal.関係構造)

    def test_局所残差は影響座標とその関係だけを除外する(self):
        data = ir(
            "Alpha uses engine. Beta uses stone.",
            (
                HDS座標("alpha", "対象.実体", "Alpha"),
                HDS座標("engine", "対象.実体", "engine"),
                HDS座標("beta", "対象.実体", "Beta"),
                HDS座標("stone", "対象.実体", "stone"),
            ),
            (
                HDS関係("bad", ("alpha",), ("engine",), "使用", 値状態=値状態.確定),
                HDS関係("good", ("beta",), ("stone",), "使用", 値状態=値状態.確定),
            ),
            (HDS残差("engine-res", "entity_unresolved", "engine", "対象同定未解", 影響座標=("engine",)),),
        )
        state = HDS内部言語状態(data, 識別子="local", 言語体系="自然言語:en", 証拠境界=True)
        core = HDS構造固定模型核(標準模型核())
        internal = core.言語対応.内部化(state)
        kinds = tuple((rel.始点, rel.終点) for rel in internal.関係構造)
        self.assertEqual(len(kinds), 1)
        self.assertIn("beta", internal.意味語集合)
        self.assertIn("stone", internal.意味語集合)
        self.assertNotIn("engine", internal.意味語集合)
        self.assertNotIn("alpha uses engine", state.内容.casefold())

    def test_通常の直接言語状態は従来どおり自然言語関係を解析する(self):
        core = HDS構造固定模型核(標準模型核())
        from minidora.模型 import 言語状態
        internal = core.言語対応.内部化(言語状態("Alpha uses engine.", "自然言語:en"))
        self.assertTrue(any(rel.種別 == "使用" for rel in internal.関係構造))


if __name__ == "__main__":
    unittest.main()

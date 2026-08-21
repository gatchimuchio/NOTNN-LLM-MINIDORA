from __future__ import annotations

import unittest

from minidora.hds_adapter import HDS文脈, HDS独立コンパイル
from minidora.hds_ir import HDSIR, HDS実行核


class _RecorderCompiler:
    def __init__(self) -> None:
        self.calls: list[tuple[str, object, tuple[HDSIR, ...], HDS文脈 | None]] = []

    def コンパイル(
        self,
        入力: str,
        *,
        前回結果=None,
        HDS履歴: tuple[HDSIR, ...] = (),
        文脈: HDS文脈 | None = None,
    ) -> HDSIR:
        self.calls.append((入力, 前回結果, HDS履歴, 文脈))
        return HDSIR(
            原文=入力,
            正規化文=入力,
            認知世界ID="independent-compile-test",
            実行核=HDS実行核("意味構造転送"),
            種別="意味構造",
            閉包状態="CLOSED_FOR_SEMANTIC_TRANSFER",
        )


class _LegacyCompiler:
    def __init__(self) -> None:
        self.calls: list[str] = []

    def コンパイル(self, 入力: str) -> HDSIR:
        self.calls.append(入力)
        return HDSIR(
            原文=入力,
            正規化文=入力,
            認知世界ID="legacy-independent-test",
            実行核=HDS実行核("意味構造転送"),
        )


class HDS独立コンパイル試験(unittest.TestCase):
    def test_前回結果履歴現在焦点を独立文書へ渡さない(self) -> None:
        compiler = _RecorderCompiler()
        HDS独立コンパイル(compiler, "external document")

        self.assertEqual(len(compiler.calls), 1)
        text, previous, history, context = compiler.calls[0]
        self.assertEqual(text, "external document")
        self.assertIsNone(previous)
        self.assertEqual(history, ())
        self.assertIsInstance(context, HDS文脈)
        self.assertEqual(context.記憶版, 0)
        self.assertIsNone(context.現在焦点)
        self.assertIsNone(context.直前結果)
        self.assertEqual(context.記憶引用, ())

    def test_旧式Compilerには存在しない文脈引数を押し込まない(self) -> None:
        compiler = _LegacyCompiler()
        result = HDS独立コンパイル(compiler, "legacy data")
        self.assertEqual(result.原文, "legacy data")
        self.assertEqual(compiler.calls, ["legacy data"])


if __name__ == "__main__":
    unittest.main()

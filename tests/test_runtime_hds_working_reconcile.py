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
        認知世界ID="working-reconcile-runtime-test",
        座標=coords,
        関係=relations,
        残差=(),
        意味作用履歴=(),
        実行核=HDS実行核("意味構造転送"),
        種別="knowledge_choice",
        閉包状態="CLOSED_FOR_SEMANTIC_TRANSFER",
        入力言語="en",
        手順=None,
    )


def _question() -> HDSIR:
    return _ir(
        "What does Alpha use?",
        (
            HDS座標("alpha", "対象.実体", "Alpha"),
            HDS座標("use", "関係.述語表層", "use"),
            HDS座標("choice:A", "目的.候補", "engine"),
            HDS座標("choice:B", "目的.候補", "stone"),
        ),
    )


def _candidate(text: str) -> HDSIR:
    return _ir(text, (HDS座標("candidate", "対象.実体", text),))


def _weak_data(*, negative: bool = False) -> HDSIR:
    conditions = ("極性=否定",) if negative else ()
    return _ir(
        "Alpha does not use engine." if negative else "Alpha uses engine.",
        (
            HDS座標("alpha", "対象.実体", "Alpha", 値状態=値状態.留保),
            HDS座標("engine", "対象.実体", "engine", 値状態=値状態.留保),
        ),
        (HDS関係("use", ("alpha",), ("engine",), "作用", 条件=conditions, 値状態=値状態.留保),),
    )


class _Compiler:
    並列安全 = True

    def コンパイル(self, text: str) -> HDSIR:
        if text == "What does Alpha use?":
            return _question()
        if text in {"engine", "stone"}:
            return _candidate(text)
        if text in {"weak-a", "weak-b"}:
            return _weak_data()
        if text == "weak-negative":
            return _weak_data(negative=True)
        raise ValueError(text)


class HDS再作用Runtime試験(unittest.TestCase):
    def _run(self, records: tuple[参照記録, ...]):
        compiler = _Compiler()
        return HDS選択推論実行(
            _question(),
            records,
            コンパイル=compiler.コンパイル,
            基礎能力核=K3相当能力核(),
        )

    def test_二独立出典の未解有向関係を再照合して回答できる(self) -> None:
        result = self._run(
            (
                参照記録("a", "weak-a", "weak-a", "fixture://a", "fixture"),
                参照記録("b", "weak-b", "weak-b", "fixture://b", "fixture"),
            )
        )
        self.assertEqual(result.状態, "APPROVE", result.理由)
        self.assertEqual(result.回答ラベル, "A")
        self.assertIn("WORKING_RECHECK", result.理由)
        self.assertIn("WORKING_RECHECK_SELECTED", result.理由)
        self.assertGreaterEqual(result.一時証拠数, 2)
        self.assertGreater(result.作業関係再利用数, 0)
        self.assertEqual(result.作業関係K昇格数, 0)
        self.assertEqual(result.checkpoint再活性数, 1)
        self.assertEqual(result.大域再照合数, 1)

    def test_一出典だけでは再作用しても確定しない(self) -> None:
        result = self._run((参照記録("a", "weak-a", "weak-a", "fixture://a", "fixture"),))
        self.assertEqual(result.状態, "SUSPEND")
        self.assertIsNone(result.回答ラベル)
        self.assertEqual(result.一時証拠数, 0)
        self.assertEqual(result.checkpoint再活性数, 0)
        self.assertEqual(result.作業関係K昇格数, 0)

    def test_反対関係があれば再照合で正極性を確定しない(self) -> None:
        result = self._run(
            (
                参照記録("a", "weak-a", "weak-a", "fixture://a", "fixture"),
                参照記録("b", "weak-b", "weak-b", "fixture://b", "fixture"),
                参照記録("n", "weak-negative", "weak-negative", "fixture://n", "fixture"),
            )
        )
        self.assertEqual(result.状態, "SUSPEND")
        self.assertIsNone(result.回答ラベル)
        self.assertEqual(result.一時証拠数, 0)
        self.assertGreater(result.作業関係再検証後破棄数, 0)


if __name__ == "__main__":
    unittest.main()

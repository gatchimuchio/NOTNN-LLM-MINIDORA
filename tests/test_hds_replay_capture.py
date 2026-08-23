from __future__ import annotations

import json
from pathlib import Path
import tempfile
import unittest

from minidora.hds_ir import HDSIR, HDS実行核, HDS座標
from minidora.hds_replay_capture import HDSChoiceReplay収録, ReplayJSONL保存, Replay入力問題
from minidora.参照 import 参照記録


class _Compiler:
    def __init__(self) -> None:
        self.calls: list[object] = []

    def 問題IR(self, question: str, choices: tuple[str, ...]) -> HDSIR:
        self.calls.append(("問題IR", question, choices))
        return HDSIR(
            原文=question,
            正規化文=question,
            認知世界ID="capture-test",
            座標=(
                HDS座標("subject", "対象.実体", "Alpha"),
                HDS座標("choice:A", "目的.候補", choices[0]),
                HDS座標("choice:B", "目的.候補", choices[1]),
            ),
            関係=(),
            残差=(),
            意味作用履歴=(),
            実行核=HDS実行核("意味構造転送"),
            参照必須=True,
            種別="meaning",
            閉包状態="CLOSED_FOR_SEMANTIC_TRANSFER",
        )

    def コンパイル(self, 入力: str, **kwargs) -> HDSIR:
        self.calls.append(入力)
        coords = ()
        if 入力 in {"engine", "stone"}:
            coords = (HDS座標("candidate", "対象.実体", 入力),)
        elif 入力 == "external evidence":
            coords = (HDS座標("evidence", "対象.実体", "engine"),)
        return HDSIR(
            原文=入力,
            正規化文=入力,
            認知世界ID="capture-test",
            座標=coords,
            関係=(),
            残差=(),
            意味作用履歴=(),
            実行核=HDS実行核("意味構造転送"),
            参照必須=False,
            種別="meaning",
            閉包状態="CLOSED_FOR_SEMANTIC_TRANSFER",
        )


class _Provider:
    名称 = "fixture"

    def 検索(self, query: str, limit: int = 8):
        return (
            参照記録(
                "doc:1",
                "Alpha",
                "external evidence",
                "fixture://doc1",
                self.名称,
                信頼=0.8,
                条件=(
                    ("hds_query_choice", "A"),
                    ("hds_query_kind", "choice"),
                ),
            ),
        )


class _LegacyCompiler:
    def コンパイル(self, 入力: str, **kwargs) -> HDSIR:
        return HDSIR(
            原文=入力,
            正規化文=入力,
            認知世界ID="legacy-capture-test",
            座標=(),
            関係=(),
            残差=(),
            意味作用履歴=(),
            実行核=HDS実行核("意味構造転送"),
            種別="meaning",
            閉包状態="CLOSED_FOR_SEMANTIC_TRANSFER",
        )


class HDSReplay収録試験(unittest.TestCase):
    def test_goldをCompiler検索へ渡さず通常choice問題IRとprovenanceを固定する(self) -> None:
        compiler = _Compiler()
        rows, stats = HDSChoiceReplay収録(
            (
                Replay入力問題(
                    "case:1",
                    "question text",
                    {"A": "engine", "B": "stone"},
                    gold="A",
                ),
            ),
            compiler=compiler,
            provider=_Provider(),
        )

        self.assertEqual(len(rows), 1)
        row = rows[0]
        self.assertEqual(row["gold"], "A")
        self.assertIn(("問題IR", "question text", ("engine", "stone")), compiler.calls)
        self.assertNotIn("A", [call for call in compiler.calls if isinstance(call, str) and call not in {"engine", "stone"}])
        self.assertEqual(stats.問題数, 1)
        self.assertEqual(stats.選択肢コンパイル数, 2)
        self.assertEqual(stats.Data件数, 1)
        self.assertEqual(stats.Dataコンパイル数, 1)
        self.assertEqual(row["data"][0]["source_confidence"], 0.8)
        self.assertNotIn("content", row["data"][0])
        self.assertEqual(
            row["data"][0]["provenance"],
            [
                "fixture",
                "fixture://doc1",
                "doc:1",
                "query_choice:A",
                "query_kind:choice",
                "query_kind:structured",
                "query_kind:focus",
                "query_choice:B",
            ],
        )

    def test_問題IRを持たないlegacyCompilerは通常コンパイルへfallbackする(self) -> None:
        rows, _stats = HDSChoiceReplay収録(
            (Replay入力問題("legacy", "plain question", {"A": "one", "B": "two"}),),
            compiler=_LegacyCompiler(),
            provider=None,
        )
        self.assertEqual(rows[0]["question_ir"]["原文"], "plain question")

    def test_JSONL保存は1case1行でUTF8保存する(self) -> None:
        rows = ({"schema": "minidora.hds-choice-replay.v1", "id": "日本語"},)
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "bundle.jsonl"
            ReplayJSONL保存(rows, path)
            lines = path.read_text(encoding="utf-8").splitlines()
        self.assertEqual(len(lines), 1)
        self.assertEqual(json.loads(lines[0])["id"], "日本語")


if __name__ == "__main__":
    unittest.main()

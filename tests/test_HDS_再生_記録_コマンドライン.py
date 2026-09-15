from __future__ import annotations

import json
from pathlib import Path
import subprocess
import sys
import tempfile
import textwrap
import unittest


ROOT = Path(__file__).resolve().parents[1]


class HDSReplay収録CLI試験(unittest.TestCase):
    def test_private_pluginからbundleだけ生成できる(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            plugin = root / "private_plugin.py"
            plugin.write_text(
                textwrap.dedent(
                    '''
                    from minidora import HDSIR, HDS実行核, HDS座標, HDS関係, 参照記録

                    class Compiler:
                        def コンパイル(self, 入力, **kwargs):
                            if 入力 == "Question?":
                                coords = (
                                    HDS座標("subject", "対象.実体", "Alpha"),
                                    HDS座標("choice:A", "目的.候補", "engine"),
                                    HDS座標("choice:B", "目的.候補", "stone"),
                                )
                                relations = ()
                            elif 入力 in {"engine", "stone"}:
                                coords = (HDS座標("candidate", "対象.実体", 入力),)
                                relations = ()
                            else:
                                coords = (
                                    HDS座標("alpha", "対象.実体", "Alpha"),
                                    HDS座標("engine", "対象.実体", "engine"),
                                )
                                relations = (HDS関係("r", ("alpha",), ("engine",), "作用"),)
                            return HDSIR(
                                原文=入力,
                                正規化文=入力,
                                認知世界ID="private-plugin-test",
                                座標=coords,
                                関係=relations,
                                残差=(),
                                意味作用履歴=(),
                                実行核=HDS実行核("意味構造転送"),
                                参照必須=(入力 == "Question?"),
                                種別="meaning",
                                閉包状態="CLOSED_FOR_SEMANTIC_TRANSFER",
                            )

                    class Provider:
                        名称 = "private-fixture"
                        def 検索(self, query, limit=8):
                            return (参照記録("doc:1", "Alpha", "Alpha uses engine.", "private://doc1", self.名称, 信頼=0.7),)

                    def make_compiler():
                        return Compiler()

                    def make_provider():
                        return Provider()
                    '''
                ),
                encoding="utf-8",
            )
            dataset = root / "dataset.jsonl"
            dataset.write_text(
                json.dumps(
                    {
                        "id": "case:1",
                        "question": "Question?",
                        "choices": {"A": "engine", "B": "stone"},
                        "gold": "A",
                    },
                    ensure_ascii=False,
                ) + "\n",
                encoding="utf-8",
            )
            bundle = root / "bundle.jsonl"
            stats = root / "stats.json"
            completed = subprocess.run(
                [
                    sys.executable,
                    str(ROOT / "tools" / "hds_replay_capture.py"),
                    str(dataset),
                    str(bundle),
                    "--plugin-path",
                    str(root),
                    "--compiler",
                    "private_plugin:make_compiler",
                    "--provider",
                    "private_plugin:make_provider",
                    "--stats",
                    str(stats),
                ],
                cwd=ROOT,
                text=True,
                encoding="utf-8",
                capture_output=True,
                check=False,
            )

            self.assertEqual(completed.returncode, 0, completed.stderr)
            row = json.loads(bundle.read_text(encoding="utf-8").splitlines()[0])
            summary = json.loads(stats.read_text(encoding="utf-8"))

        self.assertEqual(row["gold"], "A")
        self.assertEqual(row["data"][0]["source_confidence"], 0.7)
        self.assertNotIn("Compiler", json.dumps(row, ensure_ascii=False))
        self.assertEqual(summary["problem_count"], 1)
        self.assertEqual(summary["choice_compile_count"], 2)
        self.assertEqual(summary["data_compile_count"], 1)


if __name__ == "__main__":
    unittest.main()

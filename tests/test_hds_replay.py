from __future__ import annotations

import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

from minidora.hds_ir import HDSIR, HDS実行核, HDS座標, HDS関係, 値状態
from minidora.hds_replay import HDSIR復元, HDSIR辞書化


ROOT = Path(__file__).resolve().parents[1]


def _ir(text: str, coords: tuple[HDS座標, ...], relations: tuple[HDS関係, ...] = ()) -> HDSIR:
    return HDSIR(
        原文=text,
        正規化文=text,
        認知世界ID="replay:test",
        座標=coords,
        関係=relations,
        残差=(),
        意味作用履歴=(),
        実行核=HDS実行核("意味構造転送"),
        種別="意味構造",
        閉包状態="CLOSED_FOR_SEMANTIC_TRANSFER",
        入力言語="en",
    )


class HDSReplay試験(unittest.TestCase):
    def test_HDSIRをJSON形へ往復できる(self) -> None:
        original = _ir(
            "Alpha uses engine.",
            (
                HDS座標("alpha", "対象.実体", "Alpha", 値状態=値状態.確定, 原文範囲=(0, 5)),
                HDS座標("engine", "対象.実体", "engine", 値状態=値状態.推定),
            ),
            (HDS関係("r", ("alpha",), ("engine",), "作用"),),
        )
        restored = HDSIR復元(HDSIR辞書化(original))
        self.assertEqual(restored.原文, original.原文)
        self.assertEqual(restored.座標[1].値状態, 値状態.推定)
        self.assertEqual(restored.関係[0].始点, ("alpha",))
        self.assertEqual(restored.関係[0].終点, ("engine",))
        self.assertIsNone(restored.手順)

    def test_固定HDS_IRだけでchoice_benchmarkを再実行できる(self) -> None:
        question = _ir(
            "What does Alpha use?",
            (
                HDS座標("alpha", "対象.実体", "Alpha", 原文範囲=(10, 15)),
                HDS座標("choice:A", "目的.候補", "engine"),
                HDS座標("choice:B", "目的.候補", "stone"),
            ),
        )
        choices = {
            "A": _ir("engine", (HDS座標("a", "対象.実体", "engine", 原文範囲=(0, 6)),)),
            "B": _ir("stone", (HDS座標("b", "対象.実体", "stone", 原文範囲=(0, 5)),)),
        }
        data = _ir(
            "Alpha uses engine.",
            (
                HDS座標("alpha", "対象.実体", "Alpha", 原文範囲=(0, 5)),
                HDS座標("engine", "対象.実体", "engine", 原文範囲=(11, 17)),
            ),
            (HDS関係("use", ("alpha",), ("engine",), "作用"),),
        )
        row = {
            "schema": "minidora.hds-choice-replay.v1",
            "id": "fixture:1",
            "question_ir": HDSIR辞書化(question),
            "choices_ir": {label: HDSIR辞書化(ir) for label, ir in choices.items()},
            "data": [{"provenance": ["fixture", "doc:1"], "ir": HDSIR辞書化(data)}],
            "gold": "A",
        }

        with tempfile.TemporaryDirectory() as tmp:
            input_path = Path(tmp) / "fixture.jsonl"
            input_path.write_text(json.dumps(row, ensure_ascii=False) + "\n", encoding="utf-8")
            completed = subprocess.run(
                [sys.executable, str(ROOT / "tools" / "hds_choice_replay_benchmark.py"), str(input_path)],
                cwd=ROOT,
                text=True,
                encoding="utf-8",
                capture_output=True,
                check=False,
            )
        self.assertEqual(completed.returncode, 0, completed.stderr)
        result = json.loads(completed.stdout)
        self.assertEqual(result["total"], 1)
        self.assertEqual(result["correct"], 1)
        self.assertEqual(result["answered"], 1)
        self.assertEqual(result["suspended"], 0)
        self.assertEqual(result["details"][0]["predicted"], "A")


if __name__ == "__main__":
    unittest.main()

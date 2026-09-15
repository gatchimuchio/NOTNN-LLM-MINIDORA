from __future__ import annotations

import csv
import importlib.util
import io
import json
from pathlib import Path
import tempfile
import unittest
from contextlib import redirect_stdout
from unittest.mock import patch


ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location("projection_audit", ROOT / "tools/audit_projection_chain.py")
assert SPEC is not None and SPEC.loader is not None
audit = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(audit)


class 射影監査入力境界試験(unittest.TestCase):
    def _csv(self, path: Path, count: int = 8) -> None:
        with path.open("w", encoding="utf-8", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=(
                "Question", "Correct Answer", "Incorrect Answer 1", "Incorrect Answer 2",
                "Incorrect Answer 3", "Explanation", "gold",
            ))
            writer.writeheader()
            for _ in range(count):
                writer.writerow({
                    "Question": "Which object activates gamma?",
                    "Correct Answer": "Blue widgets",
                    "Incorrect Answer 1": "Red widgets",
                    "Incorrect Answer 2": "Green widgets",
                    "Incorrect Answer 3": "Orange widgets",
                    "Explanation": "正解解説専用の境界検出文字列",
                    "gold": "正解ラベル専用の境界検出文字列",
                })

    def test_正解出自と解説をCompilerへ渡さず全候補を保持する(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            csv_path = Path(td) / "artificial.csv"
            self._csv(csv_path)
            cases = audit.監査入力読込(csv_path)
            self.assertEqual(cases, audit.監査入力読込(csv_path))
        self.assertEqual(len(cases), 8)
        positions = set()
        for question, choices in cases:
            self.assertEqual(question, "Which object activates gamma?")
            self.assertIsInstance(choices, tuple)
            self.assertCountEqual(choices, ("Blue widgets", "Red widgets", "Green widgets", "Orange widgets"))
            positions.add(choices.index("Blue widgets"))
        self.assertGreater(len(positions), 1)

        compiler = audit.公開HDSコンパイラ()
        with patch.object(compiler, "問題IR", wraps=compiler.問題IR) as question_compile, \
             patch.object(compiler, "意味コンパイル", wraps=compiler.意味コンパイル) as semantic_compile:
            result = audit.意味被覆監査(cases, compiler)
        self.assertEqual(question_compile.call_count, 8)
        self.assertEqual(semantic_compile.call_count, 32)
        calls = repr((question_compile.call_args_list, semantic_compile.call_args_list))
        self.assertNotIn("境界検出文字列", calls)
        self.assertNotIn("Correct Answer", calls)
        self.assertEqual(result["question"]["total"], 8)
        self.assertEqual(result["candidate"]["total"], 32)
        self.assertNotIn("expert_explanation", result)
        self.assertNotIn("境界検出文字列", json.dumps(result, ensure_ascii=False))

    def test_人工意味契約の失敗は監査の失敗となる(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            path = Path(td)
            self._csv(path / "artificial.csv", count=198)
            # ここでは意味被覆の件数ではなく、失敗した契約をCIが見逃さないことを検証する。
            with patch.object(audit, "意味被覆監査", return_value={"question": {}, "candidate": {}}), \
                 patch.object(audit, "人工射影契約監査", return_value={"passed": False}), \
                 redirect_stdout(io.StringIO()):
                code = audit.main(["--csv", str(path / "artificial.csv"), "--out", str(path / "result.json")])
            self.assertEqual(code, 1)
            result = json.loads((path / "result.json").read_text(encoding="utf-8"))
            self.assertFalse(result["synthetic_projection_contracts"]["passed"])
            self.assertFalse(result["legacy_expert_explanation_comparable"])


if __name__ == "__main__":
    unittest.main()

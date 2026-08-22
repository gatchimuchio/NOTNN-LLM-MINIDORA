import os
from pathlib import Path
import subprocess
import sys
import unittest


ROOT = Path(__file__).resolve().parents[1]


def _env() -> dict[str, str]:
    env = dict(os.environ)
    src = str(ROOT / "src")
    env["PYTHONPATH"] = src if not env.get("PYTHONPATH") else src + os.pathsep + env["PYTHONPATH"]
    return env


class ベンチCLI試験(unittest.TestCase):
    def test_一覧表示は外部通信なしで利用できる(self):
        completed = subprocess.run(
            [sys.executable, "tools/benchmark.py", "--list"],
            cwd=ROOT,
            env=_env(),
            text=True,
            encoding="utf-8",
            capture_output=True,
            check=False,
        )
        self.assertEqual(completed.returncode, 0, completed.stderr)
        self.assertIn("gpqa-diamond", completed.stdout)
        self.assertIn("GPQA Diamond", completed.stdout)

    def test_GPQAヘルプは部分実行と再開を公開する(self):
        completed = subprocess.run(
            [sys.executable, "tools/benchmark.py", "gpqa-diamond", "--help"],
            cwd=ROOT,
            env=_env(),
            text=True,
            encoding="utf-8",
            capture_output=True,
            check=False,
        )
        self.assertEqual(completed.returncode, 0, completed.stderr)
        self.assertIn("--limit", completed.stdout)
        self.assertIn("--resume", completed.stdout)
        self.assertIn("--cache-dir", completed.stdout)


if __name__ == "__main__":
    unittest.main()

"""日本語基底移行後のOS間配置と旧名接続・出力の回帰。"""
from __future__ import annotations
import os
from pathlib import Path
import subprocess
import sys
import unittest

根 = Path(__file__).resolve().parents[1]


class 日本語基底配置試験(unittest.TestCase):
    def test_大小文字だけ異なる追跡経路を共存させない(self):
        完了 = subprocess.run(["git", "ls-files", "-z"], cwd=根, capture_output=True, check=True)
        経路群 = 完了.stdout.decode("utf-8").strip("\0").split("\0")
        対応 = {}
        for 経路 in 経路群:
            同一名 = 経路.casefold()
            self.assertNotIn(同一名, 対応, f"配置衝突: {対応.get(同一名)} / {経路}")
            対応[同一名] = 経路

    def test_旧名二入口は正本と同じモジュールへ接続する(self):
        命令 = (
            "import importlib, sys, minidora; "
            "assert 'minidora.HDS作業状態' not in sys.modules; "
            "assert 'minidora.HDS統一状態循環' not in sys.modules; "
            "assert 'minidora.K3機能' not in sys.modules; "
            "pairs=[('hds作業状態','HDS作業状態'),('hds統一状態循環','HDS統一状態循環')]; "
            "loaded=[(importlib.import_module('minidora.'+a),importlib.import_module('minidora.'+b)) for a,b in pairs]; "
            "assert all(a is b for a,b in loaded); "
            "assert callable(loaded[0][0].HDS作業状態構築); "
            "assert hasattr(loaded[1][0], 'HDS統一状態Session')"
        )
        完了 = subprocess.run([sys.executable, "-c", 命令], cwd=根, capture_output=True,
                              text=True, encoding="utf-8", timeout=30)
        self.assertEqual(完了.returncode, 0, 完了.stderr)

    def test_再生二入口は非UTF8環境でも日本語ヘルプを出力する(self):
        for 名前 in ("HDS再生記録", "HDS選択再生評価"):
            with self.subTest(入口=名前):
                完了 = subprocess.run([sys.executable, str(根 / "tools" / (名前 + ".py")), "--help"],
                                      cwd=根, capture_output=True, text=True, encoding="utf-8",
                                      env={**os.environ, "PYTHONIOENCODING": "cp1252"}, timeout=30)
                self.assertEqual(完了.returncode, 0, 完了.stderr)
                self.assertIn("HDS", 完了.stdout)


if __name__ == "__main__":
    unittest.main()

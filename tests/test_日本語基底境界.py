"""内部名と外部固定名を取り違えないための移行回帰試験。"""
from __future__ import annotations
import contextlib
import hashlib
import importlib.util
import io
import json
import os
from pathlib import Path
import struct
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

根 = Path(__file__).resolve().parents[1]


def 道具を読む(名前: str):
    仕様 = importlib.util.spec_from_file_location("境界試験_" + 名前, 根 / "tools" / (名前 + ".py"))
    本体 = importlib.util.module_from_spec(仕様)
    with patch.object(sys, "path", [str(根 / "tools"), *sys.path]):
        仕様.loader.exec_module(本体)
    return 本体


class 日本語基底境界試験(unittest.TestCase):
    def 監査する(self, 内容: str, 経路: str = "src/minidora/試験.py") -> list[str]:
        監査器 = 道具を読む("日本語基底詳細監査")
        with tempfile.TemporaryDirectory() as 一時:
            仮根 = Path(一時)
            対象 = 仮根 / 経路
            対象.parent.mkdir(parents=True)
            対象.write_text(内容, encoding="utf-8")
            誤り = []
            with patch.object(監査器, "根", 仮根):
                監査器.識別子監査(誤り)
            return 誤り

    def test_標準HTML解析器の固定フックだけを許可する(self):
        self.assertEqual(self.監査する("from html.parser import HTMLParser as 基底\nclass 解析器(基底):\n def handle_data(self, 本文): pass\n"), [])
        self.assertTrue(self.監査する("def handle_data(本文): pass\n"))
        self.assertTrue(self.監査する("class 基底: pass\nclass 解析器(基底):\n def handle_data(self, 本文): pass\n"))
        self.assertTrue(self.監査する("from html.parser import HTMLParser\nclass 解析器(HTMLParser):\n def handle_data(self, data): pass\n"))

    def test_対訳原文を任意の内部英語鍵の許可へ拡張しない(self):
        内容 = 'def _依頼を読む():\n 英語対象語対応 = {"the result": "その結果"}\n'
        self.assertEqual(self.監査する(内容, "src/minidora/多言語変換.py"), [])
        self.assertTrue(self.監査する(内容))
        self.assertTrue(self.監査する(内容.replace("英語対象語対応", "内部辞書"), "src/minidora/多言語変換.py"))

    def test_保存済み交換形式の例外は経路と形式と返却鍵へ限定する(self):
        内容 = 'def 断片を監査():\n return {"schema": "minidora.glm.weight_payload_audit.v1", "source_url": "https://example.invalid"}\n'
        self.assertEqual(self.監査する(内容, "tools/GLM重み流監査.py"), [])
        self.assertTrue(self.監査する(内容))
        self.assertTrue(self.監査する(内容.replace("weight_payload_audit.v1", "内部形式"), "tools/GLM重み流監査.py"))

    def test_旧置換入口は読み取り専用で全監査の失敗を伝える(self):
        入口 = 道具を読む("日本語基底正規化_実行")
        with patch.object(入口.subprocess, "run") as 実行:
            実行.return_value.returncode = 0
            self.assertEqual(入口.main(), 0)
            self.assertEqual(実行.call_count, 3)
            self.assertEqual([Path(呼出.args[0][1]).name for 呼出 in 実行.call_args_list],
                             ["日本語基底監査.py", "日本語基底詳細監査.py", "リポジトリ整合性監査.py"])
        with patch.object(入口.subprocess, "run") as 実行:
            実行.return_value.returncode = 1
            self.assertEqual(入口.main(), 1)
            self.assertEqual(実行.call_count, 3)
        一時本文 = (根 / "tools/日本語基底正規化_一時.py").read_text(encoding="utf-8")
        self.assertIn("読み取り専用", 一時本文)
        self.assertNotIn("write_text", 一時本文)
        self.assertFalse((根 / "tools/日本語基底正規化_仕上げ.py").exists())
        self.assertFalse((根 / ".github/workflows/日本語基底正規化_一時適用.yml").exists())

    def test_復元した四道具は旧入口と正本の両方で起動する(self):
        for 名前 in ("正本評価", "benchmark_strict", "GLM重み目録探索", "glm_weight_manifest_discover",
                     "GLM重み流監査", "glm_weight_stream_audit", "K3_HF同一性目録", "k3_hf_identity_inventory"):
            with self.subTest(入口=名前):
                実行 = subprocess.run([sys.executable, str(根 / "tools" / (名前 + ".py")), "--help"],
                                      capture_output=True, text=True, encoding="utf-8",
                                      env={**os.environ, "PYTHONIOENCODING": "cp1252"}, timeout=30)
                self.assertEqual(実行.returncode, 0, 実行.stderr)

    def test_監査入口は非UTF8標準出力でも日本語を保持する(self):
        for 名前 in ("リポジトリ整合性監査", "repository_consistency_check", "日本語基底監査", "日本語基底詳細監査"):
            with self.subTest(入口=名前):
                実行 = subprocess.run([sys.executable, str(根 / "tools" / (名前 + ".py"))],
                                      capture_output=True, text=True, encoding="utf-8",
                                      env={**os.environ, "PYTHONIOENCODING": "cp1252"}, timeout=60)
                self.assertEqual(実行.returncode, 0, 実行.stderr)
                self.assertIn("監査: 合格", 実行.stdout)
                self.assertNotIn("UnicodeEncodeError", 実行.stderr)

    def test_UTF8化は文字列捕捉器を壊さず実行出力に適用する(self):
        道具 = 道具を読む("標準入出力")
        with contextlib.redirect_stdout(io.StringIO()) as 捕捉, contextlib.redirect_stderr(io.StringIO()):
            道具.標準出力をUTF8化()
            print("日本語出力")
        self.assertEqual(捕捉.getvalue(), "日本語出力\n")
        出力バイト = io.BytesIO()
        出力先 = io.TextIOWrapper(出力バイト, encoding="cp1252", newline="\n")
        with contextlib.redirect_stdout(出力先), contextlib.redirect_stderr(io.StringIO()):
            道具.標準出力をUTF8化()
            print("日本語出力")
            出力先.flush()
        self.assertEqual(出力バイト.getvalue(), "日本語出力\n".encode("utf-8"))
        出力先.close()

    def test_正本評価の取得条件を固定し部分実行を許可しない(self):
        道具 = 道具を読む("正本評価")
        with tempfile.TemporaryDirectory() as 一時:
            出力先 = Path(一時) / "評価.json"
            出力先.write_text('{"評価条件": {}}', encoding="utf-8")\n            引数 = 道具.引数解析器().parse_args(["gpqa-e2e", "--out", str(出力先)])\n            with patch.object(\n                道具,\n                "GPQA中核正本を実行",\n                return_value={"評価条件": {}},\n            ) as 実行, self.assertRaises(SystemExit):\n                道具.GPQA正本を実行(引数)\n            実行.assert_called_once_with(出力先)\n            self.assertNotIn("評価契約", json.loads(出力先.read_text(encoding="utf-8")))\n            with contextlib.redirect_stderr(io.StringIO()), self.assertRaises(SystemExit):
                道具.引数解析器().parse_args(["gpqa-e2e", "--out", str(出力先), "--limit", "1"])

    def test_重み目録の外部ページングと循環拒否を保持する(self):
        道具 = 道具を読む("GLM重み目録探索")
        with patch.object(道具, "JSONを取得", side_effect=[([1], '<https://example.invalid/2>; rel="next"'), ([2], None)]):
            self.assertEqual(道具.全頁を取得("https://example.invalid/1"), [1, 2])
        with patch.object(道具, "JSONを取得", return_value=([1], '<https://example.invalid/1>; rel="next"')):
            with self.assertRaises(RuntimeError):
                道具.全頁を取得("https://example.invalid/1")

    def test_重み監査の固定形式と改変拒否を保持する(self):
        道具 = 道具を読む("GLM重み流監査")
        # safetensorsの外部形式そのものを入力標本として与える。
        ヘッダ = b'{"weight": {"dtype": "U8", "shape": [2], "data_offsets": [0, 2]}}'
        全体 = struct.pack("<Q", len(ヘッダ)) + ヘッダ + b"\x01\x02"
        仕様 = {"size": len(全体), "sha256": hashlib.sha256(全体).hexdigest(), "repo": "fixture/model", "revision": "fixed", "path": "one.safetensors"}
        def 応答を作る(*_):
            応答 = io.BytesIO(全体)
            応答.status = 200
            return 応答
        with patch.object(道具, "範囲を取得", side_effect=応答を作る):
            結果 = 道具.断片を監査(仕様)
        self.assertEqual(結果["schema"], "minidora.glm.weight_payload_audit.v1")
        self.assertEqual(結果["status"], "PASS")
        self.assertEqual(結果["bytes_read"], len(全体))
        self.assertEqual(結果["tensor_count"], 1)
        仕様["sha256"] = "0" * 64
        with patch.object(道具, "範囲を取得", side_effect=応答を作る), self.assertRaises(RuntimeError):
            道具.断片を監査(仕様)

    def test_HF取得物の原語鍵を内部名へ誤変換しない(self):
        道具 = 道具を読む("K3_HF同一性目録")
        self.assertEqual(道具.JSON値に変換({"rfilename": "one.safetensors", "lfs": {"sha256": "abc"}}),
                         {"rfilename": "one.safetensors", "lfs": {"sha256": "abc"}})


if __name__ == "__main__":
    unittest.main()

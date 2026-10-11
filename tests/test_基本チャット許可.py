"""要求単位の外部読取配送契約。人工取得とAPI単体検査は会話性能に算入しない。"""
from collections import deque
from http.client import HTTPMessage
from importlib.metadata import PackageNotFoundError, version
from io import BytesIO
import json
from pathlib import Path
import subprocess
import sys
from threading import Lock
from types import SimpleNamespace
import unittest
from unittest.mock import patch

from minidora.HDS運用.製品 import HDS製品ミニドラ
from minidora.HDS運用.セッション import 運用応答
from minidora.製品版.ADK接続 import ADK固定版, ADK製品ミニドラ
from minidora.製品版.api import APIHandler
from minidora.製品版.型 import 能力結果


try:
    ADK導入済み = version("google-adk") == ADK固定版
except PackageNotFoundError:
    ADK導入済み = False


class 空の取得器:
    """外部通信せず、取得要求の実到達と許可だけを観測する。"""

    def __init__(self):
        self.要求列 = []

    def 実行(self, 要求, *, 外部読取許可=False, 停止要求=None):
        self.要求列.append((要求, 外部読取許可))
        return 能力結果(False, "", 保留理由="試験用の資料不足")


class 基本チャット製品許可試験(unittest.TestCase):
    def setUp(self):
        self.取得器 = 空の取得器()
        self.製品 = HDS製品ミニドラ(基本チャット=True, 取得器=self.取得器, 手順形成=False)
        self.入力文 = "公開資料で試験主題について調べて、説明して"

    def test_未許可と許可と直後未許可は別の要求条件(self):
        最初 = self.製品.応答(self.入力文, セッションID="甲")
        self.assertEqual(最初.状態, "SUSPEND")
        self.assertEqual(self.取得器.要求列, [])
        許可後 = self.製品.応答(self.入力文, セッションID="甲", 外部読取許可=True)
        self.assertEqual(許可後.状態, "SUSPEND")
        self.assertGreater(len(self.取得器.要求列), 0)
        self.assertTrue(all(許可 is True for _, 許可 in self.取得器.要求列))
        回数 = len(self.取得器.要求列)
        不許可 = self.製品.応答(self.入力文, セッションID="甲", 外部読取許可=False)
        self.assertEqual(不許可.状態, "SUSPEND")
        self.assertEqual(len(self.取得器.要求列), 回数)
        省略 = self.製品.応答(self.入力文, セッションID="甲")
        self.assertEqual(省略.状態, "SUSPEND")
        self.assertEqual(len(self.取得器.要求列), 回数)
        for 応答 in (最初, 許可後, 不許可, 省略):
            self.assertTrue(self.製品.監査台帳.検証(応答.追跡ID))

    def test_別セッションへ許可を継承しない(self):
        self.製品.応答(self.入力文, セッションID="甲", 外部読取許可=True)
        回数 = len(self.取得器.要求列)
        self.assertGreater(回数, 0)
        self.製品.応答(self.入力文, セッションID="乙")
        self.assertEqual(len(self.取得器.要求列), 回数)
        self.assertIsNot(self.製品.セッション("甲"), self.製品.セッション("乙"))
        self.製品.応答(self.入力文, セッションID="乙", 外部読取許可=True)
        self.assertGreater(len(self.取得器.要求列), 回数)

    def test_許可はboolで既定製品へ要求指定を追加できない(self):
        for 値 in (0, 1, "true", [], {}):
            with self.subTest(値=値), self.assertRaises(TypeError):
                self.製品.応答(self.入力文, 外部読取許可=値)
        self.assertEqual(self.取得器.要求列, [])
        旧製品 = HDS製品ミニドラ(取得器=self.取得器, 手順形成=False)
        self.assertFalse(旧製品.要求単位外部読取)
        self.assertFalse(旧製品.セッション("旧").外部読取許可)
        for 値 in (False, True):
            with self.subTest(値=値), self.assertRaises(ValueError):
                旧製品.応答(self.入力文, セッションID="旧", 外部読取許可=値)

    def test_明示設定だけがWikipedia取得器を初期化(self):
        with patch("minidora.製品版.検索.Wikipedia知識取得器", return_value=self.取得器) as 工場:
            HDS製品ミニドラ(手順形成=False)
            工場.assert_not_called()
            HDS製品ミニドラ(基本チャット=True, 手順形成=False)
            工場.assert_called_once_with()
            HDS製品ミニドラ(基本チャット=True, 取得器=self.取得器, 手順形成=False)
            self.assertEqual(工場.call_count, 1)


@unittest.skipUnless(ADK導入済み, "google-adk固定版の導入が必要")
class 基本チャットADK許可試験(unittest.TestCase):
    def setUp(self):
        self.製品 = HDS製品ミニドラ(基本チャット=True, 取得器=空の取得器(), 手順形成=False)
        self.セッション = self.製品.セッション("配送")
        self.接続 = ADK製品ミニドラ(self.製品)

    def test_実ADKは許可を変えずHDS製品を一度だけ呼ぶ(self):
        for 許可 in (True, False):
            with self.subTest(許可=許可), patch.object(self.セッション, "応答", return_value=運用応答("SUSPEND", "契約検査")) as 主体, \
                 patch.object(self.製品, "応答", wraps=self.製品.応答) as 製品呼出:
                応答 = self.接続.応答("配送内容", セッションID="配送", 外部読取許可=許可)
                製品呼出.assert_called_once_with("配送内容", セッションID="配送", 外部読取許可=許可)
                主体.assert_called_once_with("配送内容", 外部読取許可=許可)
                self.assertEqual(応答.メタデータ["ADK"]["HDS呼出数"], 1)
                self.assertTrue(応答.メタデータ["ADK"]["通過"])
        self.assertTrue(self.接続.要求単位外部読取)

    def test_ADK省略許可はHDSの不許可規則へ配送する(self):
        with patch.object(self.セッション, "応答", return_value=運用応答("SUSPEND", "契約検査")) as 主体, \
             patch.object(self.製品, "応答", wraps=self.製品.応答) as 製品呼出:
            self.接続.応答("配送内容", セッションID="配送")
        製品呼出.assert_called_once_with("配送内容", セッションID="配送")
        主体.assert_called_once_with("配送内容", 外部読取許可=False)

    def test_ADK不正許可はHDSを駆動しない(self):
        with patch.object(self.製品, "応答") as 製品呼出:
            for 値 in (0, 1, "true", {}, []):
                with self.subTest(値=値), self.assertRaises(TypeError):
                    self.接続.応答("配送内容", 外部読取許可=値)
            製品呼出.assert_not_called()


class 基本チャットAPI許可試験(unittest.TestCase):
    """APIHandlerの実JSON入力検査。TCP/TLS/Cloud IAMは別の既存受入責任。"""

    def setUp(self):
        self.製品 = HDS製品ミニドラ(基本チャット=True, 取得器=空の取得器(), 手順形成=False)
        self.セッション = self.製品.セッション("API検査")
        self.サーバ = SimpleNamespace(app=self.製品, CloudRun境界=True,
            許可ホスト=frozenset({"minidora.example.test"}), 許可生成元=frozenset({"https://minidora.example.test"}),
            受付ロック=Lock(), 受付時刻=deque())

    def 処理器(self, 内容=None, 道="/api/chat"):
        処理 = object.__new__(APIHandler)
        処理.server, 処理.path = self.サーバ, 道
        処理.headers = HTTPMessage()
        処理.headers["Host"] = "minidora.example.test"
        処理.headers["Origin"] = "https://minidora.example.test"
        処理.headers["Content-Type"] = "application/json"
        本文 = b"" if 内容 is None else json.dumps(内容).encode()
        処理.headers["Content-Length"] = str(len(本文))
        処理.rfile = BytesIO(本文)
        return 処理

    def POSTを実行(self, 内容):
        with patch("minidora.製品版.api._json") as 応答:
            処理 = self.処理器(内容)
            処理.do_POST()
            応答.assert_called_once()
            return 応答.call_args.args[1:]

    def test_APIは不正型の許可を製品へ渡さない(self):
        with patch.object(self.製品, "応答") as 製品呼出:
            for 値 in (None, 0, 1, "true", [], {}):
                with self.subTest(値=値):
                    状態, 本文 = self.POSTを実行({"message": "配送内容", "session_id": "API検査", "external_read": 値})
                    self.assertEqual(状態, 400)
                    self.assertEqual(本文["error"], "invalid_external_read_permission")
            製品呼出.assert_not_called()

    def test_API許可と省略はHDSの要求許可へそのまま届く(self):
        with patch.object(self.セッション, "応答", return_value=運用応答("SUSPEND", "契約検査")) as 主体:
            for 指定 in (True, False, "省略"):
                内容 = {"message": "配送内容", "session_id": "API検査"}
                if 指定 != "省略":
                    内容["external_read"] = 指定
                状態, _ = self.POSTを実行(内容)
                self.assertEqual(状態, 200)
            self.assertEqual([呼出.kwargs["外部読取許可"] for 呼出 in 主体.call_args_list], [True, False, False])

    def test_基本チャット未設定ならboolでもAPI指定を拒否する(self):
        self.サーバ.app = HDS製品ミニドラ(手順形成=False)
        with patch.object(self.サーバ.app, "応答") as 製品呼出:
            for 許可 in (True, False):
                状態, 本文 = self.POSTを実行({"message": "配送内容", "external_read": 許可})
                self.assertEqual(状態, 400)
                self.assertEqual(本文["error"], "invalid_external_read_permission")
            製品呼出.assert_not_called()

    def test_capabilitiesは要求単位許可の設定を表示する(self):
        for 製品, 期待 in ((self.製品, True), (HDS製品ミニドラ(手順形成=False), False)):
            self.サーバ.app = 製品
            with patch("minidora.製品版.api._json") as 応答:
                self.処理器(道="/api/capabilities").do_GET()
            self.assertEqual(応答.call_args.args[1], 200)
            self.assertIs(応答.call_args.args[2]["request_external_read"], 期待)


class 基本チャットCLI許可試験(unittest.TestCase):
    def CLIを実行(self, *引数):
        根 = Path(__file__).resolve().parents[1]
        return subprocess.run([sys.executable, "-m", "minidora.製品版", *引数], cwd=根,
            capture_output=True, text=True, encoding="utf-8", timeout=20)

    def test_旧CloudRun指定は外部読取を引き続き拒否(self):
        結果 = self.CLIを実行("--HDS", "--ADK", "--CloudRun", "--serve", "--外部読取")
        self.assertEqual(結果.returncode, 2)
        self.assertIn("Cloud Run検証環境では外部読取を許可しません", 結果.stderr)

    def test_基本チャットはHDS指定が必要(self):
        結果 = self.CLIを実行("--基本チャット", "2+3")
        self.assertEqual(結果.returncode, 2)
        self.assertIn("--基本チャットは--HDSと共に指定してください", 結果.stderr)


if __name__ == "__main__":
    unittest.main()

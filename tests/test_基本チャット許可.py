"""管理者方針と質問単位の外部読取配送契約。人工取得を会話性能に算入しない。"""
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
        self.製品 = HDS製品ミニドラ(基本チャット=True, 公開取得方針="auto", 取得器=self.取得器, 手順形成=False)
        self.入力文 = "試験主題とは何ですか"

    def test_省略は自動方針で明示禁止は今回だけに効く(self):
        最初 = self.製品.応答(self.入力文, セッションID="甲")
        self.assertEqual(最初.状態, "SUSPEND")
        self.assertGreater(len(self.取得器.要求列), 0)
        最初の回数 = len(self.取得器.要求列)
        許可後 = self.製品.応答(self.入力文, セッションID="甲", 外部読取許可=True)
        self.assertEqual(許可後.状態, "SUSPEND")
        self.assertGreater(len(self.取得器.要求列), 最初の回数)
        self.assertTrue(all(許可 is True for _, 許可 in self.取得器.要求列))
        回数 = len(self.取得器.要求列)
        不許可 = self.製品.応答(self.入力文, セッションID="甲", 外部読取許可=False)
        self.assertEqual(不許可.状態, "SUSPEND")
        self.assertEqual(len(self.取得器.要求列), 回数)
        省略 = self.製品.応答(self.入力文, セッションID="甲")
        self.assertEqual(省略.状態, "SUSPEND")
        self.assertGreater(len(self.取得器.要求列), 回数)
        for 応答 in (最初, 許可後, 不許可, 省略):
            self.assertTrue(self.製品.監査台帳.検証(応答.追跡ID))

    def test_質問の禁止を別セッションや次質問へ継承しない(self):
        self.製品.応答(self.入力文, セッションID="甲", 外部読取許可=False)
        self.assertEqual(self.取得器.要求列, [])
        self.製品.応答(self.入力文, セッションID="乙")
        回数 = len(self.取得器.要求列)
        self.assertGreater(回数, 0)
        self.assertIsNot(self.製品.セッション("甲"), self.製品.セッション("乙"))
        self.製品.応答(self.入力文, セッションID="甲")
        self.assertGreater(len(self.取得器.要求列), 回数)

    def test_取得付属の原主題を同目的に残し許可を越えない(self):
        文 = "公開資料で試験主題について調べて、説明して"
        for 指定 in (False, None):
            前 = len(self.取得器.要求列)
            応答 = self.製品.応答(文, セッションID="取得付属", 外部読取許可=指定)
            self.assertEqual(応答.状態, "SUSPEND")
            self.assertTrue(self.製品.監査台帳.検証(応答.追跡ID))
            if 指定 is False:
                self.assertEqual(len(self.取得器.要求列), 前)
            else:
                self.assertEqual(len(self.取得器.要求列), 前 + 1)
                要求, 許可 = self.取得器.要求列[-1]
                self.assertEqual(要求.検索語, "試験主題")
                self.assertEqual(要求.必要語, ("試験主題",))
                self.assertTrue(許可)
                self.assertIn("試験用の資料不足", 応答.本文)

    def test_取得付属の既存前置主題と引用属格を保つ(self):
        群 = (
            ("試験主題は公開資料で調べて、説明して", "試験主題"),
            ("公開資料で「試験主題」について調べて、説明して", "試験主題"),
            ("公開資料で試験主題の特徴について調べて、説明して", "試験主題 特徴"),
        )
        for 番号, (文, 検索語) in enumerate(群):
            with self.subTest(文=文):
                前 = len(self.取得器.要求列)
                応答 = self.製品.応答(文, セッションID="保持取得" + str(番号))
                self.assertEqual(応答.状態, "SUSPEND")
                self.assertEqual(len(self.取得器.要求列), 前 + 1, 応答.本文)
                要求, 許可 = self.取得器.要求列[-1]
                self.assertEqual(要求.検索語, 検索語)
                self.assertEqual(要求.必要語, ("試験主題",))
                self.assertTrue(許可)
                self.assertTrue(self.製品.監査台帳.検証(応答.追跡ID))

    def test_取得付属の未確定範囲を検索へ逃がさない(self):
        群 = (
            "公開資料で試験主題について調べないで、説明して",
            "公開資料で試験主題について調べた、説明して",
            "公開資料で試験主題について調べて、別主題を説明して",
            "別主題は公開資料で試験主題について調べて、説明して",
            "公開資料で試験主題について探し出して、説明して",
        )
        for 番号, 文 in enumerate(群):
            with self.subTest(文=文):
                前 = len(self.取得器.要求列)
                応答 = self.製品.応答(文, セッションID="未確定取得" + str(番号))
                self.assertEqual(応答.状態, "SUSPEND", 応答.本文)
                self.assertEqual(len(self.取得器.要求列), 前)
                self.assertTrue(self.製品.監査台帳.検証(応答.追跡ID))

    def test_管理offは明示許可と旧起動許可でも越えない(self):
        製品 = HDS製品ミニドラ(基本チャット=True, 公開取得方針="off", 外部読取許可=True,
                            取得器=self.取得器, 手順形成=False)
        主体 = 製品.セッション("禁止")
        with patch.object(主体, "応答", return_value=運用応答("SUSPEND", "管理禁止")) as 呼出:
            for 指定 in (None, False, True):
                応答 = 製品.応答(self.入力文, セッションID="禁止", 外部読取許可=指定)
                self.assertTrue(製品.監査台帳.検証(応答.追跡ID))
                条件 = 製品.監査台帳.取得(応答.追跡ID).イベント[0]
                self.assertEqual(条件.版, "要求許可-v2")
                self.assertEqual(条件.入力, {"指定": 指定})
                self.assertEqual(条件.出力, {"許可": False, "要求単位": True, "管理方針": "off"})
        self.assertEqual([行.kwargs["外部読取許可"] for 行 in 呼出.call_args_list], [False] * 3)
        self.assertFalse(主体.外部読取許可)
        self.assertEqual(self.取得器.要求列, [])

    def test_通常HDSの実許可と既存監査契約を維持する(self):
        for 許可 in (False, True):
            製品 = HDS製品ミニドラ(外部読取許可=許可, 取得器=self.取得器, 手順形成=False)
            with self.subTest(許可=許可), patch.object(製品.セッション("通常"), "応答",
                    return_value=運用応答("SUSPEND", "配送検査")) as 主体:
                応答 = 製品.応答(self.入力文, セッションID="通常")
            主体.assert_called_once_with(self.入力文, 外部読取許可=許可)
            条件 = 製品.監査台帳.取得(応答.追跡ID).イベント[0]
            self.assertEqual(条件.版, "要求許可-v1")
            self.assertEqual(条件.入力, {"許可": 許可})
            self.assertEqual(条件.出力, {"要求単位": False})
            self.assertTrue(製品.監査台帳.検証(応答.追跡ID))

    def test_環境方針は明示基本チャットにだけ適用する(self):
        for 方針 in ("auto", "off"):
            with self.subTest(方針=方針), patch.dict("os.environ", {"MINIDORA_RETRIEVAL_POLICY": 方針}):
                製品 = HDS製品ミニドラ(基本チャット=True, 取得器=self.取得器, 手順形成=False)
                self.assertEqual(製品.公開取得方針, 方針)
                self.assertIs(製品.セッション("環境").外部読取許可, 方針 == "auto")
                for 許可 in (False, True):
                    旧製品 = HDS製品ミニドラ(外部読取許可=許可, 手順形成=False)
                    self.assertIsNone(旧製品.公開取得方針)
                    self.assertIs(旧製品.セッション("旧").外部読取許可, 許可)
        with patch.dict("os.environ", {}, clear=True):
            self.assertEqual(HDS製品ミニドラ(基本チャット=True, 取得器=self.取得器).公開取得方針, "auto")
        with patch.dict("os.environ", {"MINIDORA_RETRIEVAL_POLICY": "invalid"}):
            with self.assertRaises(ValueError):
                HDS製品ミニドラ(基本チャット=True, 取得器=self.取得器)
            HDS製品ミニドラ(手順形成=False)
        for 方針 in ("", "AUTO", True, 1, [], {}):
            with self.subTest(方針=方針), self.assertRaises(ValueError):
                HDS製品ミニドラ(基本チャット=True, 公開取得方針=方針, 取得器=self.取得器)
        with self.assertRaises(ValueError):
            HDS製品ミニドラ(公開取得方針="auto")

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
        self.製品 = HDS製品ミニドラ(基本チャット=True, 公開取得方針="auto", 取得器=空の取得器(), 手順形成=False)
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

    def test_ADK省略許可はHDSの管理方針へ配送する(self):
        with patch.object(self.セッション, "応答", return_value=運用応答("SUSPEND", "契約検査")) as 主体, \
             patch.object(self.製品, "応答", wraps=self.製品.応答) as 製品呼出:
            self.接続.応答("配送内容", セッションID="配送")
        製品呼出.assert_called_once_with("配送内容", セッションID="配送")
        主体.assert_called_once_with("配送内容", 外部読取許可=True)
        self.assertEqual(self.接続.公開取得方針, "auto")

    def test_ADK明示許可でも管理offを越えない(self):
        製品 = HDS製品ミニドラ(基本チャット=True, 公開取得方針="off", 取得器=空の取得器(), 手順形成=False)
        接続 = ADK製品ミニドラ(製品)
        with patch.object(製品.セッション("配送"), "応答", return_value=運用応答("SUSPEND", "管理禁止")) as 主体:
            接続.応答("配送内容", セッションID="配送", 外部読取許可=True)
        主体.assert_called_once_with("配送内容", 外部読取許可=False)
        self.assertEqual(接続.公開取得方針, "off")

    def test_ADK不正許可はHDSを駆動しない(self):
        with patch.object(self.製品, "応答") as 製品呼出:
            for 値 in (0, 1, "true", {}, []):
                with self.subTest(値=値), self.assertRaises(TypeError):
                    self.接続.応答("配送内容", 外部読取許可=値)
            製品呼出.assert_not_called()


class 基本チャットAPI許可試験(unittest.TestCase):
    """APIHandlerの実JSON入力検査。TCP/TLS/Cloud IAMは別の既存受入責任。"""

    def setUp(self):
        self.製品 = HDS製品ミニドラ(基本チャット=True, 公開取得方針="auto", 取得器=空の取得器(), 手順形成=False)
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
            self.assertEqual([呼出.kwargs["外部読取許可"] for 呼出 in 主体.call_args_list], [True, False, True])

    def test_API省略と明示許可は管理offを越えない(self):
        self.サーバ.app = HDS製品ミニドラ(基本チャット=True, 公開取得方針="off", 取得器=空の取得器(), 手順形成=False)
        with patch.object(self.サーバ.app.セッション("API検査"), "応答", return_value=運用応答("SUSPEND", "管理禁止")) as 主体:
            for 指定 in ("省略", True):
                内容 = {"message": "配送内容", "session_id": "API検査"}
                if 指定 != "省略":
                    内容["external_read"] = 指定
                状態, _ = self.POSTを実行(内容)
                self.assertEqual(状態, 200)
        self.assertEqual([呼出.kwargs["外部読取許可"] for 呼出 in 主体.call_args_list], [False, False])

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
            self.assertEqual(応答.call_args.args[2]["公開取得方針"], "auto" if 期待 else None)


class 基本チャットCLI許可試験(unittest.TestCase):
    def test_CLI省略と明示指定は同じ配送契約を使う(self):
        from minidora.製品版.__main__ import main
        for 引数, 期待 in (([], {}), (["--外部読取"], {"外部読取許可": True}), (["--検索しない"], {"外部読取許可": False})):
            製品 = SimpleNamespace(応答=unittest.mock.Mock(return_value=SimpleNamespace(
                本文="配送結果", 追跡ID="配送", 監査ハッシュ="監査", 状態="APPROVE")))
            with self.subTest(引数=引数), patch.object(sys, "argv", ["minidora", "--HDS", "--基本チャット", *引数, "配送内容"]), \
                 patch("minidora.HDS運用.製品.HDS製品ミニドラ", return_value=製品), patch("builtins.print"):
                self.assertEqual(main(), 0)
            製品.応答.assert_called_once_with("配送内容", セッションID="cli", **期待)

    def CLIを実行(self, *引数):
        根 = Path(__file__).resolve().parents[1]
        return subprocess.run([sys.executable, "-X", "utf8", "-m", "minidora.製品版", *引数], cwd=根,
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

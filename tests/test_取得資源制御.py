"""当回の累積資源と局所TCP境界。一般Web・会話品質の正式受入ではない。"""
from copy import deepcopy
from http.client import HTTPSConnection
from http.server import ThreadingHTTPServer
from threading import Thread
import time
import socket
import unittest
from unittest.mock import patch

from minidora.取得実行制御 import 公開取得上限, 共有取得制御, 取得資源不足
from minidora.知識取得 import 知識取得器, 知識取得要求
from minidora.公開本文取得 import 公開本文取得器, 公開JSON取得器, 本文取得失敗
from minidora.製品版.能力契約 import 能力文脈
from minidora.製品版.検索 import Wikipedia検索供給器
from minidora.能力合成 import _文脈辞書
from minidora.HDS運用.製品 import HDS製品ミニドラ
from minidora.HDS運用 import セッション as 運用セッション
from tests.test_知識取得 import BASE, 候補, document, 試験検索, 試験本文
from tests import test_公開本文取得 as 公開HTTP試験


def 制御(**設定):
    return 共有取得制御(公開取得上限(最小通信間隔秒=0, **設定))


class 累積取得契約試験(unittest.TestCase):
    def test_不正上限を黙って丸めない(self):
        for 設定 in ({"最大検索回数": True}, {"最大候補数": 0},
                     {"全体期限秒": float("nan")}, {"最小通信間隔秒": -1}):
            with self.subTest(設定=設定), self.assertRaises(ValueError):
                公開取得上限(**設定)

    def test_二取得をまたぐ検索枠と最後の許容成功を保つ(self):
        検索 = 試験検索((候補(),))
        本文 = 試験本文({BASE + "a": document()})
        元 = 知識取得器(検索, 本文)
        共有 = 制御()
        当回 = 元.制御を束縛(共有)
        要求 = 知識取得要求("試験機器", ("電圧",))
        self.assertTrue(当回.実行(要求, 外部読取許可=True).成立)
        self.assertTrue(当回.実行(要求, 外部読取許可=True).成立)
        保留 = 当回.実行(要求, 外部読取許可=True)
        self.assertFalse(保留.成立)
        self.assertEqual(保留.保留理由, "取得資源:検索回数上限")
        self.assertEqual((len(検索.calls), len(本文.calls)), (2, 2))
        self.assertIsNone(元.取得制御)
        self.assertEqual(共有.記録()["制御未対応"], ["本文供給器", "検索供給器"])

    def test_不正候補も処理枠を消費し本文失敗も戻さない(self):
        検索 = 試験検索((object(), 候補()))
        本文 = 試験本文({BASE + "a": TimeoutError()})
        共有 = 制御(最大候補数=2, 最大本文取得数=1)
        実行 = 知識取得器(検索, 本文).制御を束縛(共有)
        結果 = 実行.実行(知識取得要求("試験機器", ("電圧",)), 外部読取許可=True)
        self.assertFalse(結果.成立)
        self.assertEqual(共有.記録()["使用"]["候補数"], 2)
        self.assertEqual(共有.記録()["使用"]["本文取得数"], 1)
        再要求 = 実行.実行(知識取得要求("試験機器", ("電圧",)), 外部読取許可=True)
        self.assertFalse(再要求.成立)
        self.assertEqual((len(検索.calls), len(本文.calls)), (1, 1))

    def test_最後の取得でも未充足を成立へ変えない(self):
        共有 = 制御(最大検索回数=1, 最大候補数=1, 最大本文取得数=1)
        本文 = 試験本文({BASE + "a": document()})
        実行 = 知識取得器(試験検索((候補(),)), 本文).制御を束縛(共有)
        結果 = 実行.実行(知識取得要求("試験機器", ("電圧", "電流")), 外部読取許可=True)
        self.assertFalse(結果.成立)
        self.assertEqual(結果.データ["不足語"], ["電流"])
        self.assertEqual(結果.データ["資料数"], 1)
        self.assertEqual(結果.参照[0].本文, "電圧は120 V。")
        self.assertEqual(結果.本文, "")

    def test_制御の複製は累積を保ち意味指紋から除外する(self):
        共有 = 制御()
        文脈 = 能力文脈("試験", "資源", 取得制御=共有)
        複製 = deepcopy(文脈)
        self.assertIs(複製.取得制御, 共有)
        複製.取得制御.消費("検索回数")
        self.assertEqual(共有.記録()["使用"]["検索回数"], 1)
        self.assertEqual(_文脈辞書(文脈), _文脈辞書(能力文脈("試験", "資源")))
        self.assertNotIn("取得制御", _文脈辞書(文脈))

    def test_Wikipedia別言語と次当回でもRetryAfterを保つ(self):
        元 = Wikipedia検索供給器()
        一 = 元.制御を束縛(制御())
        二 = 元.制御を束縛(制御())
        self.assertIsNot(一, 元)
        self.assertIs(一._供給器[0]._get_json.__self__, 一)
        with patch.object(公開JSON取得器, "_一回取得", return_value=(429, {"retry-after": "600"}, b"")) as 呼出:
            self.assertEqual(一.検索("初見主題", 1), ())
            self.assertEqual(二.検索("別の主題", 1), ())
        self.assertEqual(呼出.call_count, 1)

    def test_basic当回で予算をリセットし旧normalと保存に混ぜない(self):
        検索 = 試験検索(())
        製品 = HDS製品ミニドラ(基本チャット=True, 取得器=知識取得器(検索), 手順形成=False)
        for _ in range(2):
            応答 = 製品.応答("試験主題とは何ですか", セッションID="資源")
            self.assertEqual(応答.状態, "SUSPEND")
            記録 = 応答.メタデータ["HDS"]["公開取得資源"]
            self.assertEqual(記録["使用"]["検索回数"], 2)
        self.assertEqual(len(検索.calls), 4)
        self.assertNotIn("取得上限", 製品.セッション("資源").保存())
        self.assertNotIn("取得制御", 製品.セッション("資源").保存())
        self.assertIsNone(HDS製品ミニドラ(手順形成=False).セッション("旧").取得上限)

    def test_基本だけ入口時刻から制限し通常明示期限は従来起点を保つ(self):
        for 基本, 期限済 in ((False, False), (True, True)):
            with self.subTest(基本=基本):
                会話 = HDS製品ミニドラ(基本チャット=基本, 手順形成=False).セッション("時計")
                時計 = [0.0]
                前採用証明 = 会話._前採用会話を証明
                def 証明():
                    値 = 前採用証明()
                    時計[0] = 2.0
                    return 値
                def 実行前(**引数):
                    self.assertEqual(引数["停止要求"](), 期限済)
                    raise RuntimeError("時計境界のみ観測")
                with patch.object(会話, "_前採用会話を証明", side_effect=証明), \
                     patch.object(運用セッション.time, "monotonic", side_effect=lambda: 時計[0]), \
                     patch.object(運用セッション, "HDS実行主体", side_effect=lambda *args, **kwargs: 実行前(**kwargs)), \
                     self.assertRaisesRegex(RuntimeError, "時計境界のみ観測"):
                    会話.応答("2+3", 期限秒=1)


class _資源HTTPサーバ(公開HTTP試験._HTTP試験サーバ):
    def do_GET(self):
        if self.path.startswith("/w/rest.php/v1/search/page?"):
            raw = b'{"pages":[]}'
            self.send_response(200)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Content-Length", str(len(raw)))
            self.end_headers()
            self.wfile.write(raw)
        elif self.path == "/redirect":
            self.send_response(302)
            self.send_header("Location", "/")
            self.end_headers()
        elif self.path in ("/unknown-length", "/bad-encoding"):
            raw = b"abcdefghij" if self.path == "/unknown-length" else b"\xff"
            self.send_response(200)
            self.send_header("Content-Type", "text/plain; charset=utf-8")
            self.send_header("Connection", "close")
            self.end_headers()
            self.wfile.write(raw)
        else:
            return super().do_GET()


class 資源HTTP境界試験(unittest.TestCase):
    fetch = 公開HTTP試験.本文HTTP配線試験.fetch

    @classmethod
    def setUpClass(cls):
        cls.server = ThreadingHTTPServer(("127.0.0.1", 0), _資源HTTPサーバ)
        cls.thread = Thread(target=cls.server.serve_forever, daemon=True)
        cls.thread.start()

    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown()
        cls.server.server_close()
        cls.thread.join(timeout=2)

    def test_転送各段をHTTP枠へ含める(self):
        共有 = 制御(最大HTTP開始数=2)
        doc = self.fetch("/redirect", 取得制御=共有)
        self.assertEqual(len(doc.経路), 2)
        self.assertEqual(共有.記録()["使用"]["HTTP開始数"], 2)
        self.assertEqual(共有.記録()["使用"]["総バイト数"], doc.転送バイト数)
        制限 = 制御(最大HTTP開始数=1)
        with self.assertRaises(取得資源不足):
            self.fetch("/redirect", 取得制御=制限)
        self.assertEqual(制限.記録()["使用"]["HTTP開始数"], 1)

    def test_不明長も総枠を越えて受信せず切断本文を採用しない(self):
        共有 = 制御(最大総バイト数=8)
        with self.assertRaises(取得資源不足):
            self.fetch("/unknown-length", 取得制御=共有)
        self.assertEqual(共有.記録()["使用"]["総バイト数"], 8)
        self.assertEqual(共有.残量("総バイト数"), 0)

    def test_復号失敗も累積し停止後は接続しない(self):
        共有 = 制御()
        with self.assertRaises(本文取得失敗):
            self.fetch("/bad-encoding", 取得制御=共有)
        self.assertEqual(共有.記録()["使用"]["総バイト数"], 1)
        停止 = 共有取得制御(公開取得上限(), 停止要求=lambda: True)
        with patch("minidora.公開本文取得._公開アドレス") as DNS, self.assertRaises(取得資源不足):
            公開本文取得器(取得制御=停止).取得("https://example.test/")
        DNS.assert_not_called()
        期限後 = 共有取得制御(公開取得上限(), 開始時刻=time.monotonic() - 241)
        with patch("minidora.公開本文取得._公開アドレス") as DNS, self.assertRaises(取得資源不足):
            公開本文取得器(取得制御=期限後).取得("https://example.test/")
        DNS.assert_not_called()

    def test_受信直後の停止でも既受信バイトを残す(self):
        共有 = 共有取得制御(公開取得上限(最小通信間隔秒=0),
                            停止要求=lambda: 共有.記録()["使用"]["総バイト数"] > 0)
        with self.assertRaises(取得資源不足):
            self.fetch("/bad-encoding", 取得制御=共有)
        self.assertEqual(共有.記録()["使用"]["総バイト数"], 1)

    def test_Wikipedia二言語JSONを実HTTP数に含める(self):
        original = socket.create_connection
        original_request = HTTPSConnection.request
        ctx = unittest.mock.MagicMock()
        ctx.wrap_socket.side_effect = lambda sock, server_hostname: sock
        def connect(address, timeout):
            self.assertEqual(address, ("8.8.8.8", 443))
            return original(self.server.server_address, timeout=timeout)
        def request(conn, method, target, body=None, headers=None, *, encode_chunked=False):
            return original_request(conn, method, target, body=body,
                                    headers={**(headers or {}), "Host": "127.0.0.1"},
                                    encode_chunked=encode_chunked)
        共有 = 制御(最大HTTP開始数=2)
        供給 = Wikipedia検索供給器().制御を束縛(共有)
        with patch("minidora.公開本文取得._公開アドレス", return_value="8.8.8.8"), \
             patch("minidora.公開本文取得.socket.create_connection", side_effect=connect), \
             patch("minidora.公開本文取得.ssl.create_default_context", return_value=ctx), \
             patch.object(HTTPSConnection, "request", request):
            結果, 来歴 = 供給.検索来歴付き("初見主題", 1)
        self.assertEqual(結果, ())
        self.assertEqual(len(来歴), 2)
        self.assertEqual(共有.記録()["使用"]["HTTP開始数"], 2)
        self.assertEqual(共有.記録()["使用"]["総バイト数"], len(b'{"pages":[]}') * 2)


if __name__ == "__main__":
    unittest.main()

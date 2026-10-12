"""実transportと局所TCPのCAS/送信契約。Google実機・課金受入ではない。"""
from concurrent.futures import ThreadPoolExecutor
from contextlib import contextmanager
from copy import copy, deepcopy
from datetime import datetime, timedelta, timezone
from http.client import HTTPSConnection
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
import pickle
import socket
from threading import Barrier, RLock, Thread
import unittest
from unittest.mock import MagicMock, patch
from urllib.parse import parse_qs, urlsplit

from minidora.取得実行制御 import 公開取得上限, 共有取得制御, 取得資源不足
from minidora.製品版.Google検索 import GoogleCloud検索供給器
from minidora.製品版.検索送信予算 import (
    固定保存先, 検索送信予算設定, GCS検索送信予算, 検索送信予算停止)


class _認証:
    def __init__(self):
        self.calls = []

    def 認証する(self, url, *, 取得制御, method="POST"):
        self.calls.append((url, method, 取得制御))
        return {"authorization": "Bearer LOCAL_BUDGET_TEST_TOKEN"}


class _保存検索サーバ(BaseHTTPRequestHandler):
    def _処理(self):
        server = self.server
        body = self.rfile.read(int(self.headers.get("Content-Length", "0")))
        status = 200
        with server.lock:
            server.calls.append((self.command, self.path, dict(self.headers), body))
            path = urlsplit(self.path)
            params = parse_qs(path.query)
            config = server.config
            target = config.保存先
            generation = str(server.generation)
            is_media = params.get("alt") == ["media"]
            meta = {"bucket": target.バケット, "name": target.オブジェクト,
                    "generation": generation}
            if path.path.startswith("/v1/projects/"):
                server.searches += 1
                応答値 = {"results": []}
                if server.mode == "search-fail":
                    status = 503
            elif server.mode == "missing":
                status, 応答値 = 404, {}
            elif self.command == "GET" and not is_media:
                応答値 = meta
                if server.mode == "wrong-target":
                    応答値 = {**meta, "name": "other/secret.json"}
            elif self.command == "GET":
                if server.mode == "media-race" and not server.raced:
                    server.raced = True
                    server.generation += 1
                if params.get("ifGenerationMatch") != [str(server.generation)]:
                    status, 応答値 = 412, {}
                else:
                    応答値 = json.loads(config.保存内容(server.count))
                    if server.mode == "wrong-config":
                        応答値["設定SHA256"] = "0" * 64
                    if server.mode == "boolean-count":
                        応答値["予約数"] = True
            else:
                if server.mode in {"post-race", "always-race"} and (not server.raced or server.mode == "always-race"):
                    server.raced = True
                    server.generation += 1
                if params.get("ifGenerationMatch") != [str(server.generation)]:
                    status, 応答値 = 412, {}
                else:
                    server.count = json.loads(body)["予約数"]
                    server.generation += 1
                    応答値 = {**meta, "generation": str(server.generation)}
                    if server.mode == "unknown-ack":
                        応答値 = {"private": "PRIVATE_STORAGE_RESPONSE"}
                    elif server.mode == "unknown-500":
                        status, 応答値 = 500, {}
                    elif server.mode == "disconnect":
                        self.connection.shutdown(socket.SHUT_RDWR)
                        self.connection.close()
                        return
            raw = json.dumps(応答値, ensure_ascii=False).encode()
            if server.mode == "duplicate" and is_media and self.command == "GET":
                raw = raw[:-1] + b',"' + "予約数".encode() + b'":0}'
            barrier = server.barrier if is_media and status == 200 and not server.raced else None
        if barrier is not None:
            barrier.wait(timeout=3)
            with server.lock:
                server.raced = True
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(raw)))
        self.end_headers()
        self.wfile.write(raw)

    do_GET = _処理
    do_POST = _処理

    def log_message(self, *_):
        pass


class 検索送信予算契約試験(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.server = ThreadingHTTPServer(("127.0.0.1", 0), _保存検索サーバ)
        cls.thread = Thread(target=cls.server.serve_forever, daemon=True)
        cls.thread.start()

    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown()
        cls.server.server_close()
        cls.thread.join(timeout=2)

    def setUp(self):
        now = datetime.now(timezone.utc).replace(microsecond=0)
        self.config = 検索送信予算設定("local-cas", "minidora-507702", "local-test",
            固定保存先("minidora-local-budget", "budget/search.json"),
            now - timedelta(hours=1), now + timedelta(hours=1), 累積上限=2)
        self.server.config = self.config
        self.server.lock = RLock()
        self.server.generation, self.server.count = 100, 0
        self.server.mode, self.server.raced, self.server.barrier = "ok", False, None
        self.server.calls, self.server.searches = [], 0
        self.auth = _認証()

    def shared(self, **values):
        return 共有取得制御(公開取得上限(最小通信間隔秒=0, **values))

    def 送信予算(self):
        return GCS検索送信予算(self.config, self.auth)

    def provider(self, control):
        return GoogleCloud検索供給器("minidora-507702", "local-test", self.auth,
            送信予算=self.送信予算(), 許可ホスト=("source.example.test",)).制御を束縛(control)

    @contextmanager
    def transport(self):
        original, original_request = socket.create_connection, HTTPSConnection.request
        ctx = MagicMock()
        ctx.wrap_socket.side_effect = lambda sock, server_hostname: sock
        def connect(address, timeout):
            self.assertEqual(address, ("8.8.8.8", 443))
            return original(self.server.server_address, timeout=timeout)
        def request(conn, method, target, body=None, headers=None, *, encode_chunked=False):
            return original_request(conn, method, target, body=body,
                headers={**(headers or {}), "Host": "127.0.0.1"}, encode_chunked=encode_chunked)
        with patch("minidora.公開本文取得._公開アドレス", return_value="8.8.8.8") as DNS, \
             patch("minidora.公開本文取得.socket.create_connection", side_effect=connect), \
             patch("minidora.公開本文取得.ssl.create_default_context", return_value=ctx), \
             patch.object(HTTPSConnection, "request", request):
            yield DNS

    def test_予約成功後だけPOSTし再構築後も累積上限を維持する(self):
        with self.transport():
            for _ in range(2):
                control = self.shared()
                _, 来歴 = self.provider(control).検索来歴付き("局所予算検査", 1)
                self.assertEqual(来歴[0]["状態"], "取得")
                self.assertEqual(control.記録()["使用"]["HTTP開始数"], 4)
            _, 来歴 = self.provider(self.shared()).検索来歴付き("局所予算検査", 1)
        self.assertEqual((self.server.count, self.server.searches), (2, 2))
        self.assertEqual(来歴[0]["種類"], "検索送信予算停止")
        self.assertEqual([c[0] for c in self.server.calls],
                         ["GET", "GET", "POST", "POST"] * 2 + ["GET", "GET"])
        upload = self.server.calls[2]
        self.assertIn("ifGenerationMatch=100", upload[1])
        self.assertNotIn("局所予算検査", upload[3].decode())
        for value in ("LOCAL_BUDGET_TEST_TOKEN", "authorization"):
            self.assertNotIn(value, json.dumps(来歴))

    def test_既知412だけ読取から最大二回試みる(self):
        for mode, expected in (("media-race", 5), ("post-race", 6), ("always-race", 6)):
            with self.subTest(mode=mode):
                self.setUp()
                self.server.mode = mode
                control = self.shared()
                with self.transport():
                    _, 来歴 = self.provider(control).検索来歴付き("局所予算検査", 1)
                self.assertEqual(len([c for c in self.server.calls if not c[1].startswith("/v1/")]), expected)
                self.assertEqual(self.server.searches, 0 if mode == "always-race" else 1)
                self.assertEqual(来歴[0]["状態"], "失敗" if mode == "always-race" else "取得")

    def test_二つの当回が同じ世代を読んでも予約数を失わない(self):
        self.server.barrier = Barrier(2)
        with self.transport(), ThreadPoolExecutor(max_workers=2) as pool:
            results = list(pool.map(lambda _: self.provider(self.shared()).検索来歴付き("同時枠検査", 1), range(2)))
        self.assertEqual((self.server.count, self.server.searches), (2, 2))
        self.assertTrue(all(来歴[0]["状態"] == "取得" for _, 来歴 in results))
        self.assertEqual(len([c for c in self.server.calls if c[0] == "POST" and c[1].startswith("/upload/")]), 3)

    def test_保存欠損破損設定違いで検索や初期作成をしない(self):
        for mode in ("missing", "wrong-target", "wrong-config", "boolean-count", "duplicate"):
            with self.subTest(mode=mode):
                self.setUp()
                self.server.mode = mode
                with self.transport():
                    _, 来歴 = self.provider(self.shared()).検索来歴付き("局所予算検査", 1)
                self.assertEqual((self.server.count, self.server.searches), (0, 0))
                self.assertTrue(all(c[0] == "GET" for c in self.server.calls))
                self.assertEqual(来歴[0]["種類"], "検索送信予算停止")

    def test_更新成功の応答不明で枠を返さず再送も検索もしない(self):
        for mode in ("unknown-ack", "unknown-500", "disconnect"):
            with self.subTest(mode=mode):
                self.setUp()
                self.server.mode = mode
                with self.transport():
                    _, 来歴 = self.provider(self.shared()).検索来歴付き("局所予算検査", 1)
                self.assertEqual((self.server.count, self.server.searches), (1, 0))
                self.assertEqual(len(self.server.calls), 3)
                self.assertNotIn("PRIVATE_STORAGE_RESPONSE", json.dumps(来歴))
                # 次の新当回は残る予約を読んで新しい枠を予約。旧許可を復元しない。
                self.server.mode = "ok"
                with self.transport():
                    self.provider(self.shared()).検索来歴付き("別の局所検査", 1)
                self.assertEqual((self.server.count, self.server.searches), (2, 1))

    def test_検索応答失敗後も確定予約を返さない(self):
        self.server.mode = "search-fail"
        with self.transport():
            _, 来歴 = self.provider(self.shared()).検索来歴付き("局所予算検査", 1)
        self.assertEqual((self.server.count, self.server.searches), (1, 1))
        self.assertEqual(来歴[0]["状態"], "失敗")

    def test_当回停止とHTTP枠不足ではCAS後も検索を送らない(self):
        with self.transport() as DNS:
            control = 共有取得制御(公開取得上限(), 停止要求=lambda: True)
            with self.assertRaises(取得資源不足):
                self.provider(control).検索来歴付き("局所予算検査", 1)
            DNS.assert_not_called()
            control = self.shared(最大HTTP開始数=3)
            with self.assertRaises(取得資源不足):
                self.provider(control).検索来歴付き("局所予算検査", 1)
        self.assertEqual((self.server.count, self.server.searches), (1, 0))

    def test_期限は予約前と一回許可の消費時に再確認する(self):
        control = self.shared()
        body = b'{"query":"local","pageSize":1}'
        with self.transport():
            receipt = self.送信予算().予約する(self.config.検索URL, body, control)
        with patch("minidora.製品版.検索送信予算.datetime") as clock:
            clock.now.return_value = self.config.終了UTC
            with self.assertRaises(検索送信予算停止):
                receipt.消費(self.config.検索URL, body, control)
            before = len(self.server.calls)
            with self.transport():
                self.provider(self.shared()).検索来歴付き("局所予算検査", 1)
            self.assertEqual(len(self.server.calls), before)
        self.assertEqual((self.server.count, self.server.searches), (1, 0))

    def test_許可は本文URL当回へ束縛しコピー再送と保存を拒否する(self):
        control, body = self.shared(), b'{"query":"local","pageSize":1}'
        with self.transport():
            receipt = self.送信予算().予約する(self.config.検索URL, body, control)
        for url, payload, 当回 in ((self.config.検索URL + "?secret", body, control),
                                   (self.config.検索URL, b"other", control),
                                   (self.config.検索URL, body, self.shared())):
            with self.assertRaises(検索送信予算停止):
                receipt.消費(url, payload, 当回)
        self.assertIs(copy(receipt), receipt)
        self.assertIs(deepcopy(receipt), receipt)
        receipt.消費(self.config.検索URL, body, control)
        with self.assertRaises(検索送信予算停止):
            copy(receipt).消費(self.config.検索URL, body, control)
        with self.assertRaises(TypeError):
            pickle.dumps(receipt)

    def test_CAS接続中の期限到達でも更新POSTを送らない(self):
        current = [self.config.開始UTC + timedelta(minutes=1)]
        count = [0]
        def 文脈():
            ctx = MagicMock()
            def wrap(sock, server_hostname):
                count[0] += 1
                if count[0] == 3:
                    current[0] = self.config.終了UTC
                return sock
            ctx.wrap_socket.side_effect = wrap
            return ctx
        with patch("minidora.製品版.検索送信予算.datetime") as clock, self.transport():
            clock.now.side_effect = lambda *_: current[0]
            with patch("minidora.公開本文取得.ssl.create_default_context", side_effect=文脈):
                _, 来歴 = self.provider(self.shared()).検索来歴付き("局所予算検査", 1)
        self.assertEqual((self.server.count, self.server.searches), (0, 0))
        self.assertEqual([row[0] for row in self.server.calls], ["GET", "GET"])
        self.assertEqual(来歴[0]["種類"], "検索送信予算停止")

    def test_固定保存先は別用途履歴世代初期作成を拒否する(self):
        target = self.config.保存先
        for url, method in ((target.メタデータURL(), "POST"),
                (target.メタデータURL().replace("search.json", "other.json"), "GET"),
                (target.本文URL("100") + "&generation=100", "GET"),
                (target.更新URL("100").replace("Match=100", "Match=0"), "POST"),
                (target.更新URL("100"), "PUT"),
                (target.本文URL("100").replace("storage.googleapis.com", "other.test"), "GET")):
            with self.subTest(url=url, method=method), self.assertRaises(検索送信予算停止):
                target.要求を確認(url, method)
        with self.assertRaises(ValueError):
            GoogleCloud検索供給器("minidora-507702", "other-app", self.auth,
                送信予算=self.送信予算(), 許可ホスト=("source.example.test",))


if __name__ == "__main__":
    unittest.main()

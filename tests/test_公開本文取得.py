"""公開URL・DNS固定・本文抽出の契約試験。公開インターネットへのLIVE試験ではない。"""
from hashlib import sha256
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import socket
import ssl
from threading import Thread
import unittest
from unittest.mock import MagicMock, patch

from minidora.公開本文取得 import 公開URL, 公開本文取得器, 本文取得失敗, 本文を復号, _公開アドレス

BASE = "https://example.test/"


def parse(body, content_type="text/html; charset=utf-8", headers=None):
    return 本文を復号(BASE, (BASE,), headers or {"content-type": content_type},
                     body.encode() if isinstance(body, str) else body)


class 公開本文契約試験(unittest.TestCase):
    def test_公開URLの正規化(self):
        self.assertEqual(公開URL("https://EXAMPLE.test:443/a#part"), "https://example.test/a")
        self.assertEqual(公開URL("https://example.test/日本語?q=本文"),
                         "https://example.test/%E6%97%A5%E6%9C%AC%E8%AA%9E?q=%E6%9C%AC%E6%96%87")
        self.assertEqual(公開URL("https://example.test."), BASE)

    def test_禁止URL(self):
        bad = ("http://example.test", "file:///etc/passwd", "ftp://example.test", "https://u:p@example.test",
               "https://example.test:8443", "https://127.0.0.1", "https://10.1.1.1", "https://169.254.169.254",
               "https://100.64.0.1", "https://[::1]", "https://[::ffff:127.0.0.1]", "https://224.0.0.1",
               "https://example.test/\nhi", "https://example.test/a b", "https://example.test\\@127.0.0.1",
               "https://[fe80::1%25eth0]", "https://", None, "x" * 4097)
        for url in bad:
            with self.subTest(url=url), self.assertRaises(ValueError):
                公開URL(url)

    def test_公開DNSと固定接続先(self):
        rows = [(socket.AF_INET, socket.SOCK_STREAM, 6, "", ("8.8.8.8", 443))]
        with patch("minidora.公開本文取得.socket.getaddrinfo", return_value=rows):
            self.assertEqual(_公開アドレス("example.test"), "8.8.8.8")

    def test_DNSの一部だけが非公開でも拒否(self):
        for ip in ("127.0.0.1", "192.168.1.1", "100.64.1.1", "::1", "ff02::1"):
            rows = [(2, 1, 6, "", ("8.8.8.8", 443)), (2, 1, 6, "", (ip, 443))]
            with self.subTest(ip=ip), patch("minidora.公開本文取得.socket.getaddrinfo", return_value=rows):
                with self.assertRaises(ValueError):
                    _公開アドレス("example.test")

    def test_DNS空応答(self):
        with patch("minidora.公開本文取得.socket.getaddrinfo", return_value=[]), self.assertRaises(ValueError):
            _公開アドレス("example.test")

    def test_本文からscript等を除外し題名を分離(self):
        doc = parse('<html><head><title>題名 &amp; 仕様</title><style>秘密999</style></head>'
                    '<body><p>電圧は120 V。</p><script>send(999)</script><p>電流は5 A。</p></body></html>')
        self.assertEqual(doc.題名, "題名 & 仕様")
        self.assertEqual(doc.本文, "電圧は120 V。\n電流は5 A。")
        self.assertNotIn("999", doc.本文)
        self.assertEqual(doc.本文SHA256, sha256(doc.本文.encode()).hexdigest())

    def test_表の平坦化を本文に混ぜない(self):
        d = parse('<p>本文10。</p><table><tr><td>999</td></tr></table><p>末尾20。</p>')
        self.assertEqual(d.本文, "本文10。\n末尾20。")
        self.assertIn("table", d.除外要素)

    def test_除外要素の入れ子と未閉鎖(self):
        a = parse('<template><div><span>削除</span></div></template><p>採用</p>')
        self.assertEqual(a.本文, "採用")
        b = parse('<p>採用</p><template><div>後続を勝手に復活させない')
        self.assertEqual(b.本文, "採用")

    def test_文字参照と段落境界(self):
        d = parse('<div>A&amp;B<br>C</div><p>D&#x3002;</p><!-- コメント -->')
        self.assertEqual(d.本文, "A&B\nC\nD。")

    def test_プレーン本文は原文の空白を維持(self):
        d = parse("a  b\r\nc\r\nd", "text/plain; charset=utf-8")
        self.assertEqual(d.本文, "a  b\nc\nd")

    def test_文字コード指定とmeta(self):
        d = parse("日本語".encode("cp932"), "text/plain; charset=cp932")
        self.assertEqual(d.本文, "日本語")
        d = parse('<meta charset="shift_jis"><p>本文</p>'.encode("shift_jis"), "text/html")
        self.assertEqual(d.本文, "本文")

    def test_不明文字コードや復号失敗を置換文字にしない(self):
        for mime, raw in (("text/plain; charset=utf-8", b"\xff"), ("text/plain; charset=base64", b"a")):
            with self.subTest(mime=mime), self.assertRaises(ValueError):
                parse(raw, mime)

    def test_未知MIMEや圧縮を成功にしない(self):
        for headers in ({"content-type": "application/pdf"}, {"content-type": "image/png"},
                        {"content-type": "text/plain", "content-encoding": "gzip"}, {}):
            with self.subTest(headers=headers), self.assertRaises(ValueError):
                本文を復号(BASE, (BASE,), headers, b"text")

    def test_空本文とJSのみのページ(self):
        for body in ("", "   ", "<script>document.write('内容')</script>"):
            with self.subTest(body=body), self.assertRaises(ValueError):
                parse(body)

    def test_転送先再検査と最終URL記録(self):
        f = 公開本文取得器()
        with patch.object(f, "_一回取得", side_effect=[(302, {"location": "/b"}, b""),
                   (200, {"content-type": "text/plain"}, b"hello")]):
            r = f.取得(BASE)
            self.assertEqual(r.経路, (BASE, BASE + "b"))
            self.assertEqual((r.要求URL, r.最終URL), (BASE, BASE + "b"))

    def test_転送先が非公開またはHTTPなら接続しない(self):
        for url in ("https://127.0.0.1/", "http://example.test/x", "file:///secret"):
            f = 公開本文取得器()
            with self.subTest(url=url), patch.object(f, "_一回取得", return_value=(302, {"location": url}, b"")) as call:
                with self.assertRaises(ValueError):
                    f.取得(BASE)
                self.assertEqual(call.call_count, 1)

    def test_転送循環と上限とlocation欠落(self):
        f = 公開本文取得器(最大転送数=1)
        for responses in ([(302, {"location": BASE}, b"")], [(302, {}, b"")],
                          [(302, {"location": "/b"}, b""), (302, {"location": "/c"}, b"")]):
            with self.subTest(), patch.object(f, "_一回取得", side_effect=responses), self.assertRaises(ValueError):
                f.取得(BASE)

    def test_許可ホストは完全一致し転送にも適用(self):
        f = 公開本文取得器(許可ホスト=("example.test",))
        with patch.object(f, "_一回取得") as call:
            with self.assertRaises(ValueError):
                f.取得("https://example.test.evil.test/")
            call.assert_not_called()
        with patch.object(f, "_一回取得", return_value=(302, {"location": "https://other.test/"}, b"")) as call:
            with self.assertRaises(ValueError):
                f.取得(BASE)
            self.assertEqual(call.call_count, 1)

    def test_取得失敗を本文にしない(self):
        for status in (401, 403, 404, 500):
            f = 公開本文取得器()
            with self.subTest(status=status), patch.object(f, "_一回取得", return_value=(status, {}, b"fake")):
                with self.assertRaises(ValueError):
                    f.取得(BASE)

    def test_バイト上限(self):
        f = 公開本文取得器(最大バイト数=4)
        with patch.object(f, "_一回取得", return_value=(200, {"content-type": "text/plain"}, b"12345")), self.assertRaises(ValueError):
            f.取得(BASE)

    def test_設定値を黙って丸めない(self):
        for kwargs in ({"timeout": True}, {"timeout": 0}, {"timeout": float("nan")},
                       {"最大バイト数": 0}, {"最大転送数": -1}, {"許可ホスト": ["x.test"]},
                       {"許可ホスト": ("x.test/path",)}):
            with self.subTest(kwargs=kwargs), self.assertRaises(ValueError):
                公開本文取得器(**kwargs)


class _HTTP試験サーバ(BaseHTTPRequestHandler):
    def do_GET(self):
        body = "<head><title>接続試験</title></head><p>電圧は120 V。</p>".encode()
        self.send_response(200)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        if self.path == "/large":
            body = b"x" * 10000
        self.send_header("Content-Length", str(len(body) + (100 if self.path == "/short" else 0)))
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, *args):
        pass


class 本文HTTP配線試験(unittest.TestCase):
    """TCPとhttp.clientは実物。DNS・TLSだけを局所差替えするため公開TLS実証ではない。"""
    @classmethod
    def setUpClass(cls):
        cls.server = ThreadingHTTPServer(("127.0.0.1", 0), _HTTP試験サーバ)
        cls.thread = Thread(target=cls.server.serve_forever, daemon=True)
        cls.thread.start()

    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown()
        cls.server.server_close()
        cls.thread.join(timeout=2)

    def fetch(self, path="/", size=500_000):
        original = socket.create_connection
        ctx = MagicMock()
        ctx.wrap_socket.side_effect = lambda sock, server_hostname: sock
        def connect(address, timeout):
            self.assertEqual(address, ("8.8.8.8", 443))
            return original(self.server.server_address, timeout=timeout)
        with patch("minidora.公開本文取得._公開アドレス", return_value="8.8.8.8"), \
             patch("minidora.公開本文取得.socket.create_connection", side_effect=connect), \
             patch("minidora.公開本文取得.ssl.create_default_context", return_value=ctx):
            result = 公開本文取得器(timeout=2, 最大バイト数=size).取得("https://example.test" + path)
            self.assertEqual(ctx.wrap_socket.call_args.kwargs["server_hostname"], "example.test")
            return result

    def test_実HTTP受信から本文まで(self):
        self.assertEqual(self.fetch().本文, "電圧は120 V。")

    def test_ContentLength上限超過(self):
        with self.assertRaises(ValueError):
            self.fetch("/large", 1000)

    def test_受信不足を黙って採用しない(self):
        with self.assertRaises(ValueError):
            self.fetch("/short")

    def test_TLS失敗時に平文へ降格しない(self):
        sock = MagicMock()
        ctx = MagicMock()
        ctx.wrap_socket.side_effect = ssl.SSLError("test certificate failure")
        with patch("minidora.公開本文取得._公開アドレス", return_value="8.8.8.8"), \
             patch("minidora.公開本文取得.socket.create_connection", return_value=sock), \
             patch("minidora.公開本文取得.ssl.create_default_context", return_value=ctx):
            with self.assertRaises(ssl.SSLError):
                公開本文取得器().取得(BASE)
            sock.close.assert_called()


if __name__ == "__main__":
    unittest.main()

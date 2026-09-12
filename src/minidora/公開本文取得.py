"""公開HTTPSから静的な本文を読む。検索・知識の採否・ブラウザ操作とは別責任。"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from email.message import Message
from hashlib import sha256
from html.parser import HTMLParser
from http.client import HTTPSConnection
import ipaddress
import math
import re
import socket
import ssl
import time
from urllib.parse import quote, urljoin, urlsplit, urlunsplit

本文取得版 = "MINIDORA-公開本文取得-v0.1"


class 本文取得失敗(ValueError):
    """例外本文にサーバ応答や認証情報を混ぜず、理由コードだけを持つ。"""


def 公開URL(値: str) -> str:
    if type(値) is not str or not 0 < len(値) <= 4096:
        raise 本文取得失敗("URL型・長さ不正")
    if re.search(r"[\s\x00-\x1f\x7f\\]", 値):
        raise 本文取得失敗("URL制御文字")
    try:
        u = urlsplit(値)
        if u.scheme != "https" or not u.hostname or u.username is not None or u.password is not None:
            raise ValueError()
        if u.port not in (None, 443) or "%" in u.hostname:
            raise ValueError()
        host = u.hostname.encode("idna").decode("ascii").lower().rstrip(".")
        try:
            address = ipaddress.ip_address(host)
        except ValueError:
            if len(host) > 253 or not all(re.fullmatch(r"[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?", x)
                                          for x in host.split(".")):
                raise ValueError()
        else:
            if not address.is_global or address.is_multicast:
                raise ValueError()
        authority = f"[{host}]" if ":" in host else host
        return urlunsplit(("https", authority, quote(u.path or "/", safe="/%:@!$&'()*+,;=-._~"),
                           quote(u.query, safe="%=&?/:@!$'()*+,;+-._~"), ""))
    except (ValueError, UnicodeError) as exc:
        raise 本文取得失敗("公開HTTPSの標準ポートURLが必要") from exc


def _公開アドレス(host: str) -> str:
    """DNS結果をすべて検査し、接続先をその検査済みIPへ固定する。"""
    rows = socket.getaddrinfo(host, 443, type=socket.SOCK_STREAM)
    addresses = sorted({row[4][0] for row in rows})
    if not addresses:
        raise 本文取得失敗("DNS結果なし")
    for value in addresses:
        ip = ipaddress.ip_address(value)
        if not ip.is_global or ip.is_multicast:
            raise 本文取得失敗("非公開アドレスへの接続禁止")
    return addresses[0]


class _本文抽出(HTMLParser):
    _除外 = {"head", "script", "style", "noscript", "template", "svg", "canvas", "table"}
    _非文字 = {"img", "iframe", "object", "embed", "audio", "video"}
    _区切 = {"p", "div", "section", "article", "main", "h1", "h2", "h3", "h4", "li", "ul", "ol", "pre", "blockquote", "br", "hr"}
    _空要素 = {"area", "base", "br", "col", "embed", "hr", "img", "input", "link", "meta", "param", "source", "track", "wbr"}

    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.抑止: list[str] = []
        self.除外: set[str] = set()
        self.断片: list[str] = []
        self.題名: list[str] = []
        self._題名内 = False

    def handle_starttag(self, tag, attrs):
        if tag in self._非文字:
            # 明示した空alt画像以外を、意味的に無関係とは決め付けない。
            if tag != "img" or dict(attrs).get("alt") != "":
                self.除外.add(tag)
        if tag == "title":
            self._題名内 = True
        if tag in self._除外:
            self.除外.add(tag)
            self.抑止.append(tag)
        elif self.抑止 and tag not in self._空要素:
            self.抑止.append(tag)
        elif not self.抑止 and tag in self._区切:
            self.断片.append("\n")

    def handle_startendtag(self, tag, attrs):
        self.handle_starttag(tag, attrs)
        self.handle_endtag(tag)

    def handle_endtag(self, tag):
        if tag == "title":
            self._題名内 = False
        if self.抑止:
            if tag in self.抑止:
                # 対応する最後の開始タグまで閉じる。未閉鎖の除外域は保守的に残す。
                i = len(self.抑止) - 1 - self.抑止[::-1].index(tag)
                del self.抑止[i:]
        elif tag in self._区切:
            self.断片.append("\n")

    def handle_data(self, data):
        if self._題名内:
            self.題名.append(data)
        elif not self.抑止:
            self.断片.append(data)

    def 本文(self) -> str:
        return "\n".join(x for line in "".join(self.断片).splitlines() if (x := " ".join(line.split())))


@dataclass(frozen=True, slots=True)
class 取得本文:
    要求URL: str
    最終URL: str
    題名: str
    本文: str
    取得時刻: str
    内容種別: str
    文字コード: str
    転送バイト数: int
    転送SHA256: str
    本文SHA256: str
    経路: tuple[str, ...]
    除外要素: tuple[str, ...] = ()


def 本文を復号(要求URL: str, 経路: tuple[str, ...], headers: dict[str, str], raw: bytes) -> 取得本文:
    msg = Message()
    msg["content-type"] = headers.get("content-type", "application/octet-stream")
    mime = msg.get_content_type()
    if mime not in ("text/html", "text/plain", "text/markdown"):
        raise 本文取得失敗("未対応内容種別")
    if headers.get("content-encoding", "identity").lower() not in ("", "identity"):
        raise 本文取得失敗("圧縮応答は未対応")
    encoding = msg.get_content_charset()
    if encoding is None and mime == "text/html":
        meta = re.search(br'<meta\b[^>]*\bcharset\s*=\s*[\x22\x27]?([a-zA-Z0-9_-]+)', raw[:4096], re.I)
        encoding = meta[1].decode("ascii") if meta else None
    encoding = encoding or "utf-8-sig"
    if encoding.lower().replace("_", "-") not in (
        "utf-8", "utf-8-sig", "ascii", "us-ascii", "shift-jis", "sjis", "cp932", "euc-jp", "iso-8859-1"):
        raise 本文取得失敗("未対応文字コード")
    try:
        text = raw.decode(encoding, errors="strict")
    except (LookupError, UnicodeError) as exc:
        raise 本文取得失敗("本文復号失敗") from exc
    title, excluded = "", ()
    if mime == "text/html":
        parser = _本文抽出()
        parser.feed(text)
        parser.close()
        text = parser.本文()
        title = " ".join("".join(parser.題名).split())
        if parser.抑止:
            parser.除外.add("未閉鎖除外域")
        excluded = tuple(sorted(parser.除外))
    else:
        text = text.replace("\r\n", "\n").replace("\r", "\n").strip()
    if not text.strip():
        raise 本文取得失敗("取得本文が空")
    return 取得本文(要求URL, 経路[-1], title, text, datetime.now(timezone.utc).isoformat(),
                    mime, encoding, len(raw), sha256(raw).hexdigest(),
                    sha256(text.encode("utf-8")).hexdigest(), 経路, excluded)


class 公開本文取得器:
    """公開HTTPS専用・読取専用。DNS待ちの強制中断やブラウザ描画は提供しない。"""

    def __init__(self, *, timeout: float = 8.0, 最大バイト数: int = 500_000,
                 最大転送数: int = 3, 許可ホスト: tuple[str, ...] = ()):
        if type(timeout) not in (int, float) or not math.isfinite(timeout) or not 0 < timeout <= 60:
            raise ValueError("timeout範囲不正")
        if type(最大バイト数) is not int or not 1 <= 最大バイト数 <= 2_000_000:
            raise ValueError("最大バイト数範囲不正")
        if type(最大転送数) is not int or not 0 <= 最大転送数 <= 5:
            raise ValueError("最大転送数範囲不正")
        if type(許可ホスト) is not tuple:
            raise ValueError("許可ホストはtuple")
        hosts = []
        for host in 許可ホスト:
            if type(host) is not str or not host or any(c in host for c in "/?#@:"):
                raise ValueError("許可ホスト不正")
            hosts.append(urlsplit(公開URL("https://" + host)).hostname)
        self.timeout, self.最大バイト数, self.最大転送数 = float(timeout), 最大バイト数, 最大転送数
        self.許可ホスト = tuple(hosts)

    def _一回取得(self, url: str) -> tuple[int, dict[str, str], bytes]:
        host = urlsplit(url).hostname
        ip = _公開アドレス(host)
        context = ssl.create_default_context()
        conn = HTTPSConnection(host, 443, timeout=self.timeout, context=context)
        raw_socket = socket.create_connection((ip, 443), timeout=self.timeout)
        try:
            tls_socket = context.wrap_socket(raw_socket, server_hostname=host)
            conn.sock = tls_socket
            u = urlsplit(url)
            conn.request("GET", u.path + ("?" + u.query if u.query else ""), headers={
                "User-Agent": "MINIDORA/knowledge-retrieval-0.1",
                "Accept": "text/html, text/plain, text/markdown",
                "Accept-Encoding": "identity", "Connection": "close"})
            with conn.getresponse() as response:
                headers = {k.lower(): v for k, v in response.getheaders()}
                if response.status != 200:
                    return response.status, headers, b""
                length = headers.get("content-length")
                if length is not None and (not length.isdecimal() or int(length) > self.最大バイト数):
                    raise 本文取得失敗("本文サイズ上限")
                chunks, size = [], 0
                deadline = time.monotonic() + self.timeout
                while not response.isclosed():
                    remaining = deadline - time.monotonic()
                    if remaining <= 0:
                        raise 本文取得失敗("本文読取時間上限")
                    tls_socket.settimeout(remaining)
                    chunk = response.read1(min(65536, self.最大バイト数 + 1 - size))
                    if not chunk:
                        break
                    chunks.append(chunk)
                    size += len(chunk)
                    if size > self.最大バイト数:
                        raise 本文取得失敗("本文サイズ上限")
                data = b"".join(chunks)
                if length is not None and len(data) != int(length):
                    raise 本文取得失敗("本文受信長不一致")
                return response.status, headers, data
        finally:
            conn.close()
            raw_socket.close()

    def 取得(self, url: str) -> 取得本文:
        first = current = 公開URL(url)
        route = []
        for _ in range(self.最大転送数 + 1):
            current = 公開URL(current)
            host = urlsplit(current).hostname
            if self.許可ホスト and host not in self.許可ホスト:
                raise 本文取得失敗("許可ホスト外")
            if current in route:
                raise 本文取得失敗("転送循環")
            route.append(current)
            status, headers, data = self._一回取得(current)
            if status in (301, 302, 303, 307, 308):
                target = headers.get("location")
                if not target:
                    raise 本文取得失敗("転送先なし")
                current = urljoin(current, target)
                continue
            if status != 200:
                raise 本文取得失敗(f"HTTP状態:{status}")
            if len(data) > self.最大バイト数:
                raise 本文取得失敗("本文サイズ上限")
            return 本文を復号(first, tuple(route), headers, data)
        raise 本文取得失敗("転送回数上限")

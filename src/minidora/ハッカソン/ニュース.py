from __future__ import annotations

from collections.abc import Sequence
from datetime import datetime
from email.utils import parsedate_to_datetime
from hashlib import sha256
from html import unescape
from html.parser import HTMLParser
import re
from typing import Protocol
from urllib.request import Request, urlopen
import xml.etree.ElementTree as ET
from zoneinfo import ZoneInfo

from .型 import ニュース項目


ニュースモジュール版 = "ニュースRSS-v0.1"
既定RSS = ("https://news.google.com/rss?hl=ja&gl=JP&ceid=JP:ja",)


class ニュース供給器(Protocol):
    def 取得(self, 問合せ: str, *, 上限: int = 8) -> tuple[ニュース項目, ...]: ...


class _本文抽出器(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.parts: list[str] = []

    def handle_data(self, data: str) -> None:
        text = data.strip()
        if text:
            self.parts.append(text)


def _HTML除去(value: str) -> str:
    parser = _本文抽出器()
    try:
        parser.feed(unescape(value or ""))
        text = " ".join(parser.parts)
    except Exception:
        text = re.sub(r"<[^>]+>", " ", value or "")
    return re.sub(r"\s+", " ", text).strip()


def _時刻(value: str) -> datetime | None:
    if not value:
        return None
    try:
        parsed = parsedate_to_datetime(value)
        return parsed if parsed.tzinfo is not None else parsed.replace(tzinfo=ZoneInfo("UTC"))
    except (TypeError, ValueError, OverflowError):
        return None


def _識別子(title: str, url: str, guid: str) -> str:
    material = guid or url or title
    return sha256(material.encode("utf-8", errors="replace")).hexdigest()[:20]


class RSSニュース供給器:
    def __init__(self, RSS一覧: Sequence[str] = 既定RSS, *, timeout: float = 8.0) -> None:
        self.RSS一覧 = tuple(str(item) for item in RSS一覧)
        self.timeout = float(timeout)

    def _取得XML(self, url: str) -> bytes:
        request = Request(url, headers={"User-Agent": "MINIDORA-Hackathon/0.1 (+traceable-chat)"})
        with urlopen(request, timeout=self.timeout) as response:
            return response.read()

    @staticmethod
    def 解析(xml_bytes: bytes) -> tuple[ニュース項目, ...]:
        root = ET.fromstring(xml_bytes)
        items: list[ニュース項目] = []
        for node in root.findall(".//item"):
            title = (node.findtext("title") or "").strip()
            link = (node.findtext("link") or "").strip()
            guid = (node.findtext("guid") or "").strip()
            description = _HTML除去(node.findtext("description") or "")
            source = (node.findtext("source") or "").strip() or "RSS"
            published = _時刻((node.findtext("pubDate") or "").strip())
            if not title or not link:
                continue
            items.append(ニュース項目(_識別子(title, link, guid), title, description, source, link, published))
        return tuple(items)

    def 取得(self, 問合せ: str, *, 上限: int = 8) -> tuple[ニュース項目, ...]:
        del 問合せ  # 現行v0.1は主要ニュースRSSを参照する。検索語化は次版の外部境界。
        collected: list[ニュース項目] = []
        errors: list[Exception] = []
        for url in self.RSS一覧:
            try:
                collected.extend(self.解析(self._取得XML(url)))
            except Exception as exc:  # 外部I/O境界。全feed失敗時だけ上位へ返す。
                errors.append(exc)
        if not collected and errors:
            raise RuntimeError("ニュースRSSを取得できませんでした") from errors[-1]

        seen: set[str] = set()
        unique: list[ニュース項目] = []
        for item in collected:
            key = re.sub(r"\s+", "", item.題名).casefold()
            if key in seen:
                continue
            seen.add(key)
            unique.append(item)

        tokyo = ZoneInfo("Asia/Tokyo")
        today = datetime.now(tokyo).date()
        today_items = [item for item in unique if item.公開時刻 and item.公開時刻.astimezone(tokyo).date() == today]
        candidates = today_items or unique
        candidates.sort(key=lambda item: item.公開時刻 or datetime.min.replace(tzinfo=tokyo), reverse=True)
        return tuple(candidates[: max(1, int(上限))])


class 固定ニュース供給器:
    """試験・デモ固定用。外部通信を行わない。"""

    def __init__(self, items: Sequence[ニュース項目]) -> None:
        self.items = tuple(items)

    def 取得(self, 問合せ: str, *, 上限: int = 8) -> tuple[ニュース項目, ...]:
        del 問合せ
        return self.items[: max(1, int(上限))]

from __future__ import annotations

from hashlib import sha256
import json
import os
import re
from typing import Protocol
from urllib.parse import urlencode
from urllib.request import Request, urlopen

from .型 import 参照資料, 能力結果

検索版 = "local-web-search-v1"


class Web検索供給器(Protocol):
    def 検索(self, query: str, limit: int = 5) -> tuple[参照資料, ...]: ...


class SearXNG検索供給器:
    """ローカルSearXNGのJSON Search APIを外部Data参照として利用する。"""

    def __init__(self, base_url: str | None = None, timeout: float = 10.0) -> None:
        self.base_url = (
            base_url
            or os.environ.get("MINIDORA_SEARXNG_URL")
            or "http://127.0.0.1:8888"
        ).rstrip("/")
        self.timeout = timeout

    def _get(self, url: str) -> dict:
        req = Request(
            url,
            headers={
                "User-Agent": "MINIDORA/0.5 local-web-search",
                "Accept": "application/json",
            },
        )
        with urlopen(req, timeout=self.timeout) as response:
            return json.loads(response.read(2_000_000).decode("utf-8"))

    @staticmethod
    def _text(value: object) -> str:
        text = str(value or "")
        text = re.sub(r"<[^>]+>", "", text)
        return re.sub(r"\s+", " ", text).strip()

    def 検索(self, query: str, limit: int = 5) -> tuple[参照資料, ...]:
        q = str(query or "").strip()
        if not q:
            return ()
        limit = max(1, min(int(limit), 10))
        params = urlencode(
            {
                "q": q,
                "format": "json",
                "language": "ja-JP",
                "safesearch": "0",
            }
        )
        data = self._get(f"{self.base_url}/search?{params}")
        out: list[参照資料] = []
        for item in data.get("results", []) or []:
            if len(out) >= limit:
                break
            if not isinstance(item, dict):
                continue
            title = self._text(item.get("title"))
            url = str(item.get("url") or "").strip()
            if not title or not url:
                continue
            content = self._text(item.get("content"))
            engines = item.get("engines")
            if isinstance(engines, list):
                source = ", ".join(self._text(x) for x in engines if self._text(x))
            else:
                source = self._text(item.get("engine"))
            source = source or "Web"
            key = sha256((title + "\n" + url).encode("utf-8")).hexdigest()[:20]
            out.append(参照資料(key, title, source, url, None, content))
        return tuple(out)


class 固定Web検索供給器:
    def __init__(self, items: tuple[参照資料, ...]) -> None:
        self.items = items

    def 検索(self, query: str, limit: int = 5) -> tuple[参照資料, ...]:
        return self.items[: max(1, int(limit))]


class Web検索Module本体:
    版 = 検索版

    def __init__(self, provider: Web検索供給器, limit: int = 5) -> None:
        self.provider = provider
        self.limit = max(1, min(int(limit), 10))

    def 実行(self, query: str) -> 能力結果:
        q = str(query or "").strip()
        if not q:
            return 能力結果(False, "", 保留理由="検索語が空")
        try:
            refs = self.provider.検索(q, self.limit)
        except Exception as exc:
            return 能力結果(False, "", 保留理由=f"Web検索失敗:{type(exc).__name__}")
        if not refs:
            return 能力結果(False, "", 保留理由="Web検索結果が見つからない")

        rows: list[str] = []
        for index, ref in enumerate(refs, 1):
            row = f"{index}. {ref.題名}"
            if ref.本文:
                row += f"\n   {ref.本文}"
            if ref.URL:
                row += f"\n   {ref.URL}"
            rows.append(row)
        body = "Web検索結果:\n" + "\n".join(rows)
        return 能力結果(
            True,
            body,
            根拠=tuple(ref.識別子 for ref in refs),
            参照=refs,
            データ={
                "検索語": q,
                "参照数": len(refs),
                "検索基盤": type(self.provider).__name__,
            },
        )

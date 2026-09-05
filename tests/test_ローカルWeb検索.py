from __future__ import annotations

import unittest
from urllib.parse import parse_qs, urlparse

from minidora.製品版 import 製品ミニドラ, 固定Web検索供給器, SearXNG検索供給器
from minidora.製品版.型 import 参照資料

WEB = (
    参照資料("w1", "MINIDORA overview", "duckduckgo", "https://example.com/minidora", None, "MINIDORAの概要。"),
    参照資料("w2", "MINIDORA repository", "github", "https://example.com/repo", None, "実装リポジトリ。"),
)


class CaptureProvider:
    def __init__(self) -> None:
        self.query = ""
    def 検索(self, query: str, limit: int = 5):
        self.query = query
        return WEB[:limit]


class FakeSearXNG(SearXNG検索供給器):
    def __init__(self) -> None:
        super().__init__("http://127.0.0.1:8888")
        self.request_url = ""
    def _get(self, url: str) -> dict:
        self.request_url = url
        return {
            "results": [
                {
                    "title": "<b>MINIDORA</b>",
                    "url": "https://example.com/minidora",
                    "content": "非ニューラル <b>LLM</b> の検索結果",
                    "engines": ["duckduckgo", "brave"],
                }
            ]
        }


class LocalWebSearchTests(unittest.TestCase):
    def test_web_search_route_and_references(self):
        app = 製品ミニドラ(検索供給器=固定Web検索供給器(WEB))
        result = app.応答("MINIDORAをWebで検索して", セッションID="web")
        self.assertEqual(result.経路, "Web検索")
        self.assertEqual(len(result.参照), 2)
        self.assertIn("MINIDORA overview", result.本文)

    def test_query_cleanup(self):
        provider = CaptureProvider()
        app = 製品ミニドラ(検索供給器=provider)
        result = app.応答("MINIDORAをWebで検索して", セッションID="query")
        self.assertEqual(result.経路, "Web検索")
        self.assertEqual(provider.query, "MINIDORA")

    def test_search_then_summary_uses_search_references(self):
        app = 製品ミニドラ(検索供給器=固定Web検索供給器(WEB))
        first = app.応答("MINIDORAを検索して", セッションID="summary")
        self.assertEqual(first.経路, "Web検索")
        second = app.応答("3行で要約して", セッションID="summary")
        self.assertEqual(second.経路, "要約")
        self.assertEqual(len(second.参照), 2)
        self.assertIn("MINIDORA", second.本文)

    def test_searxng_json_mapping(self):
        provider = FakeSearXNG()
        refs = provider.検索("MINIDORA", 3)
        self.assertEqual(len(refs), 1)
        self.assertEqual(refs[0].題名, "MINIDORA")
        self.assertEqual(refs[0].出典, "duckduckgo, brave")
        self.assertEqual(refs[0].本文, "非ニューラル LLM の検索結果")
        params = parse_qs(urlparse(provider.request_url).query)
        self.assertEqual(params["q"], ["MINIDORA"])
        self.assertEqual(params["format"], ["json"])

    def test_search_failure_holds_without_core(self):
        app = 製品ミニドラ(検索供給器=固定Web検索供給器(()))
        result = app.応答("存在しないものを検索して", セッションID="empty")
        self.assertEqual(result.経路, "Web検索")
        self.assertEqual(result.状態, "保留")


if __name__ == "__main__":
    unittest.main()

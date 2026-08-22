from __future__ import annotations

import unittest
from urllib.parse import parse_qs, urlparse

from minidora.europe_pmc_reference import EuropePMC参照供給器


class _FakeEuropePMC:
    def __init__(self) -> None:
        self.urls: list[str] = []

    def __call__(self, url: str, headers, timeout: float):
        self.urls.append(url)
        parsed = urlparse(url)
        self.assertions(parsed)
        return {
            "resultList": {
                "result": [
                    {
                        "source": "MED",
                        "id": "12345678",
                        "pmid": "12345678",
                        "doi": "10.1000/example",
                        "title": "Catalysis by ProteinX",
                        "abstractText": "ProteinX promotes catalytic turnover in the measured reaction.",
                        "journalTitle": "Journal of Example Biology",
                        "firstPublicationDate": "2024-05-01",
                        "pubTypeList": {"pubType": ["Journal Article"]},
                    },
                    {
                        "source": "MED",
                        "id": "87654321",
                        "title": "Title only observation",
                        "abstractText": "",
                        "pubYear": "2023",
                    },
                    {
                        "source": "MED",
                        "id": "99999999",
                        "title": "Retracted observation",
                        "abstractText": "This should not be used.",
                        "isRetracted": True,
                    },
                ]
            }
        }

    @staticmethod
    def assertions(parsed) -> None:
        if not parsed.path.endswith("/webservices/rest/search"):
            raise AssertionError(parsed.path)
        params = parse_qs(parsed.query)
        if params.get("resultType") != ["core"]:
            raise AssertionError("resultType=core missing")
        if params.get("format") != ["json"]:
            raise AssertionError("format=json missing")
        if params.get("query") != ["ProteinX catalysis"]:
            raise AssertionError("query missing")


class EuropePMC参照供給器試験(unittest.TestCase):
    def test_core検索をabstract参照記録へ変換する(self) -> None:
        fake = _FakeEuropePMC()
        provider = EuropePMC参照供給器(JSON取得=fake)
        records = provider.検索("ProteinX catalysis", 8)

        self.assertEqual(len(records), 2)
        first = records[0]
        self.assertEqual(first.識別子, "europepmc:MED:12345678")
        self.assertIn("ProteinX promotes catalytic turnover", first.内容)
        self.assertEqual(first.信頼, provider.ABSTRACT信頼)
        self.assertEqual(first.時点, "2024-05-01")
        self.assertEqual(first.由来, "https://doi.org/10.1000/example")
        self.assertIn(("evidence_scope", "abstract"), first.条件)

    def test_title_onlyはabstractより低confidence(self) -> None:
        provider = EuropePMC参照供給器(JSON取得=_FakeEuropePMC())
        records = provider.検索("ProteinX catalysis", 8)
        self.assertEqual(records[1].信頼, provider.TITLE_ONLY信頼)
        self.assertLess(records[1].信頼, records[0].信頼)
        self.assertIn(("evidence_scope", "title"), records[1].条件)

    def test_retractedフラグ付きレコードを除外する(self) -> None:
        provider = EuropePMC参照供給器(JSON取得=_FakeEuropePMC())
        records = provider.検索("ProteinX catalysis", 8)
        self.assertFalse(any(record.識別子.endswith("99999999") for record in records))

    def test_API障害は空集合へ閉じる(self) -> None:
        def failing(url, headers, timeout):
            raise OSError("network down")

        provider = EuropePMC参照供給器(JSON取得=failing)
        self.assertEqual(provider.検索("ProteinX", 4), ())
        self.assertIn("OSError", provider.最後のエラー or "")


if __name__ == "__main__":
    unittest.main()

from __future__ import annotations

import unittest

from minidora import (
    Crossref参照供給器,
    EuropePMC参照供給器,
    OpenAlex参照供給器,
    Wikipedia参照供給器,
    一般知識参照供給器,
    複合参照供給器,
)


class 標準一般知識R試験(unittest.TestCase):
    def test_既定はEuropePMC_Crossref_Wikipediaを複合する(self) -> None:
        provider = 一般知識参照供給器(OpenAlex_API_key=None, Wikipedia言語=("en",))
        self.assertIsInstance(provider, 複合参照供給器)
        children = provider._供給器群
        self.assertEqual(len(children), 3)
        self.assertIsInstance(children[0], EuropePMC参照供給器)
        self.assertIsInstance(children[1], Crossref参照供給器)
        self.assertIsInstance(children[2], Wikipedia参照供給器)

    def test_OpenAlex_keyありは4Providerを複合する(self) -> None:
        provider = 一般知識参照供給器(OpenAlex_API_key="test-key", Wikipedia言語=("en",))
        self.assertIsInstance(provider, 複合参照供給器)
        children = provider._供給器群
        self.assertEqual(len(children), 4)
        self.assertIsInstance(children[0], OpenAlex参照供給器)
        self.assertIsInstance(children[1], EuropePMC参照供給器)
        self.assertIsInstance(children[2], Crossref参照供給器)
        self.assertIsInstance(children[3], Wikipedia参照供給器)

    def test_EuropePMCとCrossrefは個別に無効化できる(self) -> None:
        provider = 一般知識参照供給器(
            OpenAlex_API_key=None,
            EuropePMC有効=False,
            Crossref有効=False,
            Wikipedia言語=("en",),
        )
        self.assertIsInstance(provider, Wikipedia参照供給器)
        self.assertEqual(provider.言語, "en")

    def test_Wikipedia複数言語の重複を除去する(self) -> None:
        provider = 一般知識参照供給器(Wikipedia言語=("en", "EN", "ja"))
        self.assertIsInstance(provider, 複合参照供給器)
        languages = [child.言語 for child in provider._供給器群 if isinstance(child, Wikipedia参照供給器)]
        self.assertEqual(languages, ["en", "ja"])

    def test_EuropePMC単独でも構成できる(self) -> None:
        provider = 一般知識参照供給器(
            OpenAlex_API_key=None,
            EuropePMC有効=True,
            Crossref有効=False,
            Wikipedia言語=(),
        )
        self.assertIsInstance(provider, EuropePMC参照供給器)

    def test_Crossref単独でも構成できる(self) -> None:
        provider = 一般知識参照供給器(
            OpenAlex_API_key=None,
            EuropePMC有効=False,
            Crossref有効=True,
            Wikipedia言語=(),
        )
        self.assertIsInstance(provider, Crossref参照供給器)

    def test_Providerなしは明示失敗する(self) -> None:
        with self.assertRaises(ValueError):
            一般知識参照供給器(
                OpenAlex_API_key=None,
                EuropePMC有効=False,
                Crossref有効=False,
                Wikipedia言語=(),
            )


if __name__ == "__main__":
    unittest.main()

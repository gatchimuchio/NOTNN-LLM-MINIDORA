from __future__ import annotations

import unittest

from minidora.hds_compiler import 公開HDSコンパイラ
from minidora.hds_reference import HDS参照問合せ候補


class HDS構造問合せ優先試験(unittest.TestCase):
    def setUp(self) -> None:
        self.compiler = 公開HDSコンパイラ()

    def test_四択でも全文より構造化queryを先に使う(self) -> None:
        ir = self.compiler.問題IR(
            "Which molecule causes apoptosis under hypoxia?",
            ("Protein A", "Protein B", "Protein C", "Protein D"),
        )
        queries = HDS参照問合せ候補(ir)
        self.assertEqual(len(queries), 6)
        first = queries[0].casefold()
        self.assertIn("apoptosis", first)
        self.assertIn("causes", first)
        self.assertIn("under hypoxia", first)
        self.assertFalse(first.startswith("which molecule"))

    def test_制御用の反転ラベルを外部検索語へ漏らさない(self) -> None:
        ir = self.compiler.問題IR(
            "Which mechanism is least likely to increase ATP production?",
            ("oxidative phosphorylation", "glycolysis", "fermentation", "beta oxidation"),
        )
        queries = HDS参照問合せ候補(ir)
        self.assertTrue(queries)
        joined = " ".join(queries)
        self.assertNotIn("反転", joined)
        self.assertNotIn("通常", joined)

    def test_全候補を対称に個別queryへ残す(self) -> None:
        choices = ("Protein A", "Protein B", "Protein C", "Protein D")
        ir = self.compiler.問題IR("Which protein inhibits kinase X?", choices)
        queries = HDS参照問合せ候補(ir)
        for choice in choices:
            self.assertEqual(sum(choice.casefold() in q.casefold() for q in queries), 1)


if __name__ == "__main__":
    unittest.main()

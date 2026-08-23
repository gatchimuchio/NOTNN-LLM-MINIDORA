from __future__ import annotations

import unittest

from minidora.hds_candidate_reconcile import HDS候補証拠, HDS候補横断調停


class HDS候補横断調停試験(unittest.TestCase):
    def test_同一sourceのfactとdocumentを二重加点しない(self) -> None:
        result = HDS候補横断調停(
            ("A", "B"),
            (
                HDS候補証拠("A", "doc:1", 5.0, ("f1",), "fact"),
                HDS候補証拠("A", "doc:1", 4.5, ("f1", "f2"), "document"),
            ),
            証拠重み=(1.0, 0.5, 0.25),
            証拠上限=3,
        )
        self.assertEqual(result["A"].独立出典数, 1)
        self.assertEqual(len(result["A"].採用証拠), 1)
        self.assertAlmostEqual(result["A"].合計得点, 5.0)
        self.assertEqual(result["A"].採用証拠[0].経路, "fact")

    def test_全候補共通sourceはmarginとprovenanceへ残さない(self) -> None:
        result = HDS候補横断調停(
            ("A", "B"),
            (
                HDS候補証拠("A", "common", 4.0, ("a-common",), "fact"),
                HDS候補証拠("B", "common", 4.0, ("b-common",), "fact"),
                HDS候補証拠("A", "exclusive-a", 3.0, ("a-only",), "fact"),
            ),
            証拠重み=(1.0, 0.5),
            証拠上限=2,
        )
        self.assertFalse(any(x.出典ID == "common" for x in result["A"].採用証拠))
        self.assertFalse(any(x.出典ID == "common" for x in result["B"].採用証拠))
        self.assertEqual(result["A"].独立出典数, 1)
        self.assertEqual(result["B"].独立出典数, 0)
        self.assertAlmostEqual(result["A"].合計得点, 3.0)
        self.assertEqual(result["B"].合計得点, 0.0)

    def test_僅差の共通sourceは相対差だけを残す(self) -> None:
        result = HDS候補横断調停(
            ("A", "B", "C", "D"),
            (
                HDS候補証拠("A", "common", 10.0, ("a",), "fact"),
                HDS候補証拠("B", "common", 9.8, ("b",), "fact"),
                HDS候補証拠("C", "common", 9.7, ("c",), "fact"),
                HDS候補証拠("D", "common", 9.6, ("d",), "fact"),
                HDS候補証拠("D", "exclusive-d", 3.0, ("d-only",), "fact"),
            ),
            証拠重み=(1.0, 0.5),
            証拠上限=2,
        )
        common_a = next(x for x in result["A"].採用証拠 if x.出典ID == "common")
        self.assertGreater(common_a.識別係数, 0.0)
        self.assertLess(common_a.識別係数, 0.02)
        self.assertEqual(result["B"].合計得点, 0.0)
        self.assertEqual(result["C"].合計得点, 0.0)
        self.assertGreater(result["D"].合計得点, result["A"].合計得点)

    def test_独立sourceは別々に加点する(self) -> None:
        result = HDS候補横断調停(
            ("A", "B"),
            (
                HDS候補証拠("A", "doc:1", 4.0, ("f1",), "fact"),
                HDS候補証拠("A", "doc:2", 3.0, ("f2",), "fact"),
            ),
            証拠重み=(1.0, 0.5),
            証拠上限=2,
        )
        self.assertEqual(result["A"].独立出典数, 2)
        self.assertAlmostEqual(result["A"].合計得点, 5.5)
        self.assertEqual(result["B"].合計得点, 0.0)

    def test_候補専用queryだけで取得した自己支持sourceは弱化する(self) -> None:
        source_a = "document:provider|origin|id-a|query_choice:A|query_kind:choice"
        result = HDS候補横断調停(
            ("A", "B"),
            (
                HDS候補証拠("A", source_a, 10.0, ("a",), "document"),
                HDS候補証拠("B", "general-b", 3.0, ("b",), "document"),
            ),
            証拠重み=(1.0,),
            証拠上限=1,
        )
        self.assertAlmostEqual(result["A"].合計得点, 1.8)
        self.assertAlmostEqual(result["B"].合計得点, 3.0)

    def test_一般queryでも取得したsourceは自己支持でも弱化しない(self) -> None:
        source_a = "document:provider|origin|id-a|query_choice:A|query_kind:choice|query_kind:structured"
        result = HDS候補横断調停(
            ("A", "B"),
            (HDS候補証拠("A", source_a, 10.0, ("a",), "document"),),
            証拠重み=(1.0,),
            証拠上限=1,
        )
        self.assertAlmostEqual(result["A"].合計得点, 10.0)

    def test_複数候補queryで取得したsourceは単一候補の自己選択とは扱わない(self) -> None:
        shared = "document:provider|origin|id-x|query_choice:A|query_choice:B|query_kind:choice"
        result = HDS候補横断調停(
            ("A", "B"),
            (HDS候補証拠("A", shared, 6.0, ("a",), "document"),),
            証拠重み=(1.0,),
            証拠上限=1,
        )
        self.assertAlmostEqual(result["A"].合計得点, 6.0)

    def test_A用queryで得たsourceがBを支持する場合は対抗証拠として弱化しない(self) -> None:
        source_a = "document:provider|origin|id-a|query_choice:A|query_kind:fallback_choice"
        result = HDS候補横断調停(
            ("A", "B"),
            (HDS候補証拠("B", source_a, 7.0, ("b",), "document"),),
            証拠重み=(1.0,),
            証拠上限=1,
        )
        self.assertAlmostEqual(result["B"].合計得点, 7.0)


if __name__ == "__main__":
    unittest.main()

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

    def test_全候補共通sourceは識別力を減衰する(self) -> None:
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
        common_a = next(x for x in result["A"].採用証拠 if x.出典ID == "common")
        common_b = next(x for x in result["B"].採用証拠 if x.出典ID == "common")
        self.assertLess(common_a.識別係数, 1.0)
        self.assertAlmostEqual(common_a.識別係数, common_b.識別係数)
        self.assertGreater(result["A"].合計得点, result["B"].合計得点)

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


if __name__ == "__main__":
    unittest.main()

from __future__ import annotations

import unittest

from minidora.科学専門能力 import 科学専門能力解決


class 科学専門能力拡張V2試験(unittest.TestCase):
    def test_円軌道transit確率比を一般式で解ける(self) -> None:
        question = (
            "Two planets move on circular orbits. The orbital period of Planet_1 is four times shorter "
            "than that of Planet_2. The star hosting Planet_1 has a mass that is twice that of the star "
            "hosting Planet_2. Both host stars have the same radii. Which planet has the higher "
            "probability to transit?"
        )
        choices = (
            "Planet_2 is preferred due to its ~1.4 times higher probability to transit.",
            "Planet_1 is preferred due to its ~2.0 times higher probability to transit.",
            "Planet_1 is preferred due to its ~3.0 times higher probability to transit.",
            "Planet_2 is preferred due to its ~2.0 times higher probability to transit.",
        )
        result = 科学専門能力解決(question, choices)
        self.assertIsNotNone(result)
        self.assertEqual(result.index, 1)
        self.assertEqual(result.solver, "circular_transit_probability_ratio")

    def test_元素記号と中性子数から核の全エネルギーを解ける(self) -> None:
        question = (
            "What is the total energy so that the speed of the nucleus X is equal to 0.8c? "
            "X is defined as C with 6 neutrons."
        )
        choices = ("18.63 GeV", "12.00 GeV", "23.00 GeV", "7.00 GeV")
        result = 科学専門能力解決(question, choices)
        self.assertIsNotNone(result)
        self.assertEqual(result.index, 0)
        self.assertEqual(result.solver, "relativistic_nucleus_total_energy")

    def test_円形極限の最初の二暗環間隔を解ける(self) -> None:
        question = (
            "A monochromatic wave passes through an N-sided polygon aperture whose apothem is r. "
            "In the Fraunhofer far field, what is the angular distance between the first two minima "
            "when N is infinitely large?"
        )
        choices = ("0.507 lambda/r", "0.610 lambda/r", "1.220 lambda/r", "0.400 lambda/r")
        result = 科学専門能力解決(question, choices)
        self.assertIsNotNone(result)
        self.assertEqual(result.index, 0)
        self.assertEqual(result.solver, "circular_aperture_minima_separation")

    def test_支持候補が無ければ近似だけで確定しない(self) -> None:
        question = (
            "A monochromatic wave passes through an N-sided polygon aperture whose apothem is r. "
            "In the Fraunhofer far field, what is the angular distance between the first two minima "
            "when N is infinitely large?"
        )
        choices = ("0.40 lambda/r", "0.61 lambda/r", "1.00 lambda/r", "1.22 lambda/r")
        self.assertIsNone(科学専門能力解決(question, choices))

    def test_無関係な問いでは発火しない(self) -> None:
        self.assertIsNone(
            科学専門能力解決(
                "Which historical source best supports this interpretation?",
                ("A", "B", "C", "D"),
            )
        )


if __name__ == "__main__":
    unittest.main()

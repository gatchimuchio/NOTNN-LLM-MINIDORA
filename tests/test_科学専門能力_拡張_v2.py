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

    def test_接地導体球の鏡像エネルギーを選べる(self) -> None:
        question = "A charge q is placed distance d from the center of a grounded conducting sphere of radius R. Calculate the potential energy."
        choices = (
            "U=- (1/2) *kq^2 R/(d^2-R^2)",
            "U=- kq^2 d/(d^2-R^2)",
            "U=(1/2) kq^2 R/(d^2+R^2)",
            "U=-(1/2) kq^2 R^2/(d^2-R^2)",
        )
        result = 科学専門能力解決(question, choices)
        self.assertIsNotNone(result)
        self.assertEqual(result.index, 0)
        self.assertEqual(result.solver, "grounded_sphere_image_energy")

    def test_振動角周波数から光子運動量を解ける(self) -> None:
        question = "A diatomic molecule has angular frequency of vibration = 5*10^14 rad/s. What photon momentum is required?"
        choices = ("1.76*10^-28 N s", "5.0*10^-27 N s", "3.0*10^-29 N s", "1.0*10^-26 N s")
        result = 科学専門能力解決(question, choices)
        self.assertIsNotNone(result)
        self.assertEqual(result.index, 0)
        self.assertEqual(result.solver, "vibrational_photon_momentum")

    def test_LaTeX寿命表記から崩壊距離を解ける(self) -> None:
        question = (
            r"A decay has proper lifetime \tau_0=1\times10^{-15}s. What minimum resolution is needed "
            "to observe at least 30% of the decays? The energy is 20 GeV and the mass is 4 GeV."
        )
        choices = ("1.77*10^-6 m", "1.0*10^-8 m", "2.0*10^-3 m", "5.0*10^-5 m")
        result = 科学専門能力解決(question, choices)
        self.assertIsNotNone(result)
        self.assertEqual(result.index, 0)
        self.assertEqual(result.solver, "decay_resolution")

    def test_固有時間から外部系移動距離を解ける(self) -> None:
        question = (
            "In one inertial reference frame the target is moving at 90000 km/s. "
            "What distance is traveled in the other reference frame when 10 seconds pass in the moving reference frame?"
        )
        target = 90000 / (1 - (90000 / 299792.458) ** 2) ** 0.5 * 10
        choices = (f"{target:.0f} km", "900000 km", "500000 km", "1500000 km")
        result = 科学専門能力解決(question, choices)
        self.assertIsNotNone(result)
        self.assertEqual(result.index, 0)
        self.assertEqual(result.solver, "proper_time_distance")

    def test_LaTeX_micrometer表記でZeeman桁比較できる(self) -> None:
        question = r"For a magnetic field B=2T, compare the paramagnetic coupling with transition energy at wavelength \lambda=0.500\mu m."
        choices = (r"<H> \ll Delta E", r"<H> \gg Delta E", r"<H> = Delta E", r"<H> > Delta E")
        result = 科学専門能力解決(question, choices)
        self.assertIsNotNone(result)
        self.assertEqual(result.index, 0)
        self.assertEqual(result.solver, "zeeman_vs_transition")

    def test_Lyman_alphaの地上光学しきい値を数値で選べる(self) -> None:
        question = "Lyman alpha at 1216 Angstrom is absorbed by a cloud. Estimate the lower limit on redshift detectable with optical ground-based telescopes."
        choices = ("2.0", "3.0", "1.0", "4.0")
        result = 科学専門能力解決(question, choices)
        self.assertIsNotNone(result)
        self.assertEqual(result.index, 0)
        self.assertEqual(result.solver, "lyman_alpha_optical_threshold_numeric")

    def test_四体消滅の娘粒子速度を解ける(self) -> None:
        question = r"Consider the annihilation p+\bar{p} -> 2A+ + 2A-. The antiproton is slowly moving and m_A c^2=300 MeV. What is the velocity of A?"
        choices = ("0.77c", "0.20c", "0.95c", "0.50c")
        result = 科学専門能力解決(question, choices)
        self.assertIsNotNone(result)
        self.assertEqual(result.index, 0)
        self.assertEqual(result.solver, "four_body_annihilation_velocity")

    def test_軸対称四重極放射の角度比と波長次数を選べる(self) -> None:
        question = (
            r"An oscillating charge distribution is spheroid with symmetry axis z. The radiated power in the radiation zone "
            r"is a function of wavelength \lambda and angle \theta. If maximum power is A, what fraction is radiated at \theta=30 degrees?"
        )
        choices = (r"1/2, \lambda^(-4)", r"3/4, \lambda^(-6)", r"1/4, \lambda^(-4)", r"1/4, \lambda^(-3)")
        result = 科学専門能力解決(question, choices)
        self.assertIsNotNone(result)
        self.assertEqual(result.index, 1)
        self.assertEqual(result.solver, "axisymmetric_electric_quadrupole_radiation")

    def test_正二十面体配置のCoulomb最小エネルギーを解ける(self) -> None:
        question = (
            "Consider an isolated system of 13 identical particles each with charge 1e. "
            "12 of these charges are constrained to stay at 1 m from point P. The 13th charge is fixed at P. "
            "What is the minimum energy in Joules?"
        )
        choices = ("1.4111e-26", "5.0e-27", "3.0e-26", "1.0e-25")
        result = 科学専門能力解決(question, choices)
        self.assertIsNotNone(result)
        self.assertEqual(result.index, 0)
        self.assertEqual(result.solver, "icosahedral_coulomb_minimum")

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

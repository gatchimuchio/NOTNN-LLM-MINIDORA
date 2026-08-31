from __future__ import annotations

import unittest

from minidora.科学専門能力 import 科学専門能力解決


class 科学構造作用試験(unittest.TestCase):
    def assert_solver(self, question, choices, expected):
        row = 科学専門能力解決(question, choices)
        self.assertIsNotNone(row)
        self.assertEqual(row.index, expected)

    def test_指数減衰は時間単位と経過時間に依存せず未来確率を出す(self):
        q = (
            'A radioactive nucleus has decay probability 36% within 80 minutes. '
            'It has survived for 17 minutes. What is the probability of decay in the next 200 minutes?'
        )
        target = 1 - (1 - 0.36) ** (200 / 80)
        self.assert_solver(q, ('10%', f'{100*target:.3f}%', '80%', '36%'), 1)

    def test_磁気単極子はFaradayと磁気Gaussを変更する(self):
        q = (
            'In a hypothetical universe magnetic monopoles exist as isolated North or South poles. '
            'Which Maxwell equations change?'
        )
        choices = (
            'The curl of the magnetic field and divergence of the electric field.',
            'The circulation of the electric field and the divergence of the magnetic field.',
            'Only the divergence of the magnetic field.',
            'Only the circulation of the magnetic field.',
        )
        self.assert_solver(q, choices, 1)

    def test_次元解析は候補順に依存しない(self):
        q = (
            r'Given L_int = kappa \bar{\psi}\sigma_{\mu\nu}\psi F^{\mu\nu}. '
            r'What is the mass dimension of kappa and is the theory renormalizable?'
        )
        choices = (
            'The mass dimension [kappa]_M=1. The theory is renormalizable.',
            'The mass dimension [kappa]_M=-1. The theory is not renormalizable.',
            'The mass dimension [kappa]_M=1. The theory is not renormalizable.',
            'The mass dimension [kappa]_M=-1. The theory is renormalizable.',
        )
        self.assert_solver(q, choices, 1)

    def test_行列分類は成分から判定する(self):
        q = (
            'The study of quantum mechanics uses matrices. '
            'W = (0, 0, 1; 0, 1, 0; 1, 0, 0), '
            'X = (i, -1, 2i; 1, 0, 1; 2i, -1, -i), '
            'Y = (0.5, 0.1, 0.2; 0.1, 0.25, 0.1; 0.2, 0.1, 0.25), '
            'Z = (3, 2i, 5; -2i, -2, -4i; 5, 4i, 4). Which statement is true?'
        )
        choices = (
            'Z and X represent observables.',
            'There exists a vector to which if one multiplies e^X, the norm changes.',
            '(e^X)*Y*(e^{-X}) represents a quantum state.',
            'W and X represent the evolution operator of some quantum system.',
        )
        self.assert_solver(q, choices, 2)

    def test_三次元射影測定は任意の対角演算子でも解ける(self):
        q = (
            'The state of a system at time t is given by the column matrix having elements (1, 2, 1). '
            'An observable is represented by matrix operator P having elements in the first row as (1, 0, 0), '
            'in the second row as (0, 0, 0) and in the third row as (0, 0, -1). '
            'Calculate the probability that the measurement will yield 0 at time t.'
        )
        self.assert_solver(q, ('1/3', '2/3', '1/6', '1'), 1)

    def test_連続射影測定はBorn則と崩壊を積算する(self):
        q = (
            'The state of a system at time t is given by the column matrix having elements (1, 2, 1), and operators P and Q are matrices. '
            'The matrix corresponding to operator P has the elements in first row as (1, 0, 0), elements in the second row as (0, 0, 0) and that in third row as (0, 0, -1). '
            'The matrix operator for Q is represented by the square matrix having elements in the first row as (0, 0, 0), second row as (0, -1, 0) and third row as (0, 0, 1). '
            'If someone measures Q just after the measurement of P, what is the probability of getting 0 for P and -1 for Q in the respective measurements?'
        )
        self.assert_solver(q, ('1/6', '2/3', '1/3', '1'), 1)

    def test_黒体光度比は半径と視線速度を同時補正する(self):
        q = (
            'Two stars have the same observed wavelength at peak brightness. Star_1 has radius 2 times that of Star_2. '
            'Their radial velocities are 0 and 1000 km/s. Assuming black bodies, by what factor is the luminosity of Star_1 greater?'
        )
        beta = 1000 / 299792.458
        d2 = ((1 + beta) / (1 - beta)) ** 0.5
        target = 4 / d2 ** 4
        self.assert_solver(q, ('4.00', f'{target:.3f}', '2.00', '8.00'), 1)

    def test_無関係な行列文へは発火しない(self):
        self.assertIsNone(
            科学専門能力解決(
                'A matrix is mentioned in a chemistry question.',
                ('a', 'b', 'c', 'd'),
            )
        )


if __name__ == '__main__':
    unittest.main()

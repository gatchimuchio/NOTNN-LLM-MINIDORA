from __future__ import annotations

import unittest

from minidora.科学専門能力 import 科学専門能力解決


class 追加科学専門能力健全性試験(unittest.TestCase):
    def assert_solver(self, question, choices, expected):
        result = 科学専門能力解決(question, choices)
        self.assertIsNotNone(result)
        self.assertEqual(result.index, expected)

    def test_LaTeX指数付き光子対生成閾値(self):
        q = r'For gamma gamma electron-positron pair creation, the average photon energy is $2\times10^{-3}eV$. What gamma-ray threshold follows?'
        self.assert_solver(q, ('3.0e4 GeV', '1.31e5 GeV', '8.0e5 GeV', '1.0e3 GeV'), 1)

    def test_EDTA綴り揺れでも平衡式を解く(self):
        q = 'What is the concentration of calcium ions in 0.08 M stochiometric Ca-EDTA complex? KCa-EDTA = 2x10^11.'
        self.assert_solver(q, ('8e-2 M', '6.3e-7 M', '4e-4 M', '2e-9 M'), 1)

    def test_波動関数の未知係数名に依存しない(self):
        q = 'The wave function is ( b / sqrt(2 + x) ) - 0.25*i. No particle occurs at x<2 or x>5. What is the numerical value of b?'
        self.assert_solver(q, ('0.42', '1.205', '2.2', '5.0'), 1)

    def test_LaTeX寿命表記から空間分解能を計算(self):
        q = r'A decay has proper lifetime \tau_{0}=9\times10^{-16}s. What minimum resolution is needed to observe at least 25% of the decays? The energy is 30GeV and mass is 4GeV.'
        self.assert_solver(q, ('2.78e-6 m', '2.78e-3 m', '2.78e-9 m', '2.78e-1 m'), 0)

    def test_qPCRはCtとコピー数の向きを検査(self):
        q = ('A qPCR calibration reports: At the concentration of 10000 copies per ul, ct of triplicate results were 31.0, 31.2, 31.4.\n'
             'At the concentration of 1000 copies per ul, ct of triplicate results were 27.7, 27.9, 28.1.\n'
             'At the concentration of 100 copies per ul, ct of triplicate results were 24.4, 24.6, 24.8. What explains the discrepancy?')
        choices = ('Technical replicates are always invalid', 'Ct values are not in agreement with the amount of target nucleic acid', 'qPCR cannot quantify nucleic acid', 'Nothing is inconsistent')
        self.assert_solver(q, choices, 1)

    def test_ブラックホール角径からエントロピー桁を求める(self):
        q = 'The angular size of the event horizon of a black hole at distance d=10^9 parsecs is theta=2x10^-16 degrees. Find the order of magnitude of the entropy.'
        self.assert_solver(q, ('10^58 J/K', '10^63 J/K', '10^68 J/K', '10^71 J/K'), 1)

    def test_同期サイクロトロンの添字波括弧を許容(self):
        q = r'A synchrocyclotron reaches T{1}=600MeV. How many revolutions? Data: \Phi{0}=\frac{\pi}{3}, U{0}=150kV.'
        self.assert_solver(q, ('2000', '3000', '4000', '8000'), 2)

    def test_相対論的核分裂補正を一般式で計算(self):
        q = ('A nucleus has rest-mass energy of 500 GeV. In spontaneous fission one fragment is 3 times more massive than the other. '
             'The sum of rest-masses is 98% of the initial mass. For the more massive fragment, what is the difference between the correct kinetic energy and the classical approximation?')
        self.assert_solver(q, ('5 MeV', '50 MeV', '500 MeV', '2 MeV'), 1)

    def test_Pauliハミルトニアンは余分なhbar係数を除く(self):
        q = r'Consider a Hamiltonian operator H = epsilon sigma.n, where n is a unit vector and sigma are Pauli spin matrices. What are the eigenvalues of the Hamiltonian operator?'
        self.assert_solver(q, ('+epsilon,-epsilon', '+epsilon*hbar/2,-epsilon*hbar/2', '+hbar/2,-hbar/2', '+1,-1'), 0)

    def test_菱面体111面間隔を数値計算(self):
        q = r'Consider a rhombohedral crystal with interatomic distance of 12 Angstrom and angles \alpha=\beta=\gamma=60^{0}. What is the interplanar distance of the (111) plane?'
        self.assert_solver(q, ('7.1 Angstrom', '9.80 Angstrom', '12.0 Angstrom', '4.9 Angstrom'), 1)

    def test_導体外部場は大文字Lを保持(self):
        q = 'An uncharged spherical conductor has a cavity with charge q inside. What is the electric field outside the spherical conductor? L is distance from conductor centre and l from cavity centre.'
        self.assert_solver(q, ('E=kq/l^2', 'E=kq/L^2', 'E=kq/(l-s)^2', 'E=0'), 1)

    def test_無関係な一般科学文へ誤発火しない(self):
        result = 科学専門能力解決('A black hole is mentioned in a qualitative history question.', ('one', 'two', 'three', 'four'))
        self.assertIsNone(result)


if __name__ == '__main__':
    unittest.main()

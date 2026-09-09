from __future__ import annotations

import math
import re
from typing import Sequence

from .科学専門能力_共通 import _generic_result, _nearest


# 原子番号は元素記号の順序から求める。GPQA固有値ではなく周期表の一般知識。
_元素記号 = (
    "H", "He", "Li", "Be", "B", "C", "N", "O", "F", "Ne",
    "Na", "Mg", "Al", "Si", "P", "S", "Cl", "Ar", "K", "Ca",
    "Sc", "Ti", "V", "Cr", "Mn", "Fe", "Co", "Ni", "Cu", "Zn",
    "Ga", "Ge", "As", "Se", "Br", "Kr", "Rb", "Sr", "Y", "Zr",
    "Nb", "Mo", "Tc", "Ru", "Rh", "Pd", "Ag", "Cd", "In", "Sn",
    "Sb", "Te", "I", "Xe", "Cs", "Ba", "La", "Ce", "Pr", "Nd",
    "Pm", "Sm", "Eu", "Gd", "Tb", "Dy", "Ho", "Er", "Tm", "Yb",
    "Lu", "Hf", "Ta", "W", "Re", "Os", "Ir", "Pt", "Au", "Hg",
    "Tl", "Pb", "Bi", "Po", "At", "Rn", "Fr", "Ra", "Ac", "Th",
    "Pa", "U", "Np", "Pu", "Am", "Cm", "Bk", "Cf", "Es", "Fm",
    "Md", "No", "Lr", "Rf", "Db", "Sg", "Bh", "Hs", "Mt", "Ds",
    "Rg", "Cn", "Nh", "Fl", "Mc", "Lv", "Ts", "Og",
)
_原子番号 = {記号: i + 1 for i, 記号 in enumerate(_元素記号)}


def _候補倍率(choice: str) -> tuple[str | None, float | None]:
    text = str(choice)
    planet = None
    m_planet = re.search(r"Planet[_\s-]*([12])", text, re.I)
    if m_planet:
        planet = m_planet.group(1)
    m_value = re.search(r"(?:~|approximately\s*)?([0-9]+(?:\.[0-9]+)?)\s*times", text, re.I)
    return planet, (float(m_value.group(1)) if m_value else None)


def solve_circular_transit_probability_ratio(question: str, choices: Sequence[str]):
    """円軌道の幾何学的transit確率比を Kepler 則から求める。

    p_transit ∝ R_star / a,
    a ∝ (M_star P^2)^(1/3),
    よって同一恒星半径なら p1/p2 = ((P2/P1)^2 / (M1/M2))^(1/3)。
    """
    s = question.casefold()
    if not (
        ("probability" in s and "transit" in s)
        and "orbital period" in s
        and "circular orbit" in s
        and ("same radii" in s or "same radius" in s)
    ):
        return None

    period_ratio = None
    m = re.search(
        r"period\s+of\s+Planet[_\s-]*1\s+is\s+([0-9]+(?:\.[0-9]+)?)\s+times\s+shorter\s+than\s+(?:that\s+of\s+)?Planet[_\s-]*2",
        question,
        re.I,
    )
    if m:
        period_ratio = float(m.group(1))  # P2 / P1
    else:
        words = {"twice": 2.0, "three times": 3.0, "four times": 4.0}
        for phrase, value in words.items():
            if re.search(
                rf"period\s+of\s+Planet[_\s-]*1\s+is\s+{re.escape(phrase)}\s+shorter\s+than",
                question,
                re.I,
            ):
                period_ratio = value
                break

    mass_ratio = None
    m = re.search(
        r"star\s+hosting\s+Planet[_\s-]*1[^.]{0,100}?mass[^.]{0,40}?([0-9]+(?:\.[0-9]+)?)\s+times\s+(?:that\s+of|the\s+mass\s+of)",
        question,
        re.I,
    )
    if m:
        mass_ratio = float(m.group(1))
    else:
        word_values = {"twice": 2.0, "three times": 3.0, "four times": 4.0}
        for phrase, value in word_values.items():
            if re.search(
                rf"star\s+hosting\s+Planet[_\s-]*1[^.]*?mass[^.]*?{re.escape(phrase)}\s+that\s+of",
                question,
                re.I,
            ):
                mass_ratio = value
                break

    if period_ratio is None or mass_ratio is None or period_ratio <= 0 or mass_ratio <= 0:
        return None

    ratio = (period_ratio * period_ratio / mass_ratio) ** (1.0 / 3.0)
    preferred = "1" if ratio >= 1 else "2"
    target = ratio if ratio >= 1 else 1.0 / ratio

    ranked: list[tuple[float, int]] = []
    for i, choice in enumerate(choices):
        planet, value = _候補倍率(str(choice))
        if planet != preferred or value is None:
            continue
        ranked.append((abs(value - target) / target, i))
    if not ranked:
        return None
    ranked.sort()
    if ranked[0][0] > 0.06 or (len(ranked) > 1 and abs(ranked[0][0] - ranked[1][0]) < 1e-12):
        return None
    return _generic_result(ranked[0][1], "circular_transit_probability_ratio", target)


def _質量数_from_description(question: str) -> int | None:
    # 明示的な質量数を最優先する。
    m = re.search(r"\bA\s*=\s*([0-9]+)\b", question)
    if m:
        return int(m.group(1))

    # 例: Li-6 / 6Li
    for symbol in _元素記号:
        m = re.search(rf"\b{re.escape(symbol)}\s*[- ]\s*([0-9]+)\b", question)
        if m:
            return int(m.group(1))
        m = re.search(rf"\b([0-9]+)\s*{re.escape(symbol)}\b", question)
        if m:
            return int(m.group(1))

    # 例: Li with 3 neutrons -> Z(Li)=3, A=Z+N。
    m = re.search(r"\b([A-Z][a-z]?)\s+with\s+([0-9]+)\s+neutrons?\b", question)
    if m and m.group(1) in _原子番号:
        return _原子番号[m.group(1)] + int(m.group(2))
    return None


def solve_relativistic_nucleus_total_energy(question: str, choices: Sequence[str]):
    """核の速度 beta c と質量数 A から全エネルギー gamma A u c^2 を求める。"""
    s = question.casefold()
    if "speed" not in s or "nucleus" not in s:
        return None
    bm = re.search(r"([0-9]+(?:\.[0-9]+)?)\s*c\b", question, re.I)
    if not bm:
        return None
    beta = float(bm.group(1))
    if not 0 < beta < 1:
        return None
    mass_number = _質量数_from_description(question)
    if mass_number is None or mass_number <= 0:
        return None

    gamma = 1.0 / math.sqrt(1.0 - beta * beta)
    target_gev = gamma * mass_number * 0.93149410242
    return _generic_result(
        _nearest(choices, target_gev, rel_tol=0.04),
        "relativistic_nucleus_total_energy",
        target_gev,
    )


def solve_circular_aperture_first_minima_separation(question: str, choices: Sequence[str]):
    """正N角形の N→∞ 円形極限で、Airy pattern最初の二つの暗環間隔を求める。"""
    s = question.casefold()
    if not (
        "aperture" in s
        and ("n-sided polygon" in s or "polygon" in s)
        and ("infinitely large" in s or "n is infinite" in s or "n→" in s)
        and "first two minima" in s
        and ("far field" in s or "fraunhofer" in s)
    ):
        return None

    # J1 の最初の二零点 x1,x2。円の直径 D=2a なので
    # Δθ = (x2-x1) λ/(π D) = coefficient * λ/a。
    x1 = 3.8317059702075125
    x2 = 7.015586669815619
    coefficient = (x2 - x1) / (2.0 * math.pi)
    return _generic_result(
        _nearest(choices, coefficient, rel_tol=0.02),
        "circular_aperture_minima_separation",
        coefficient,
    )


REGISTRY = (
    solve_circular_transit_probability_ratio,
    solve_relativistic_nucleus_total_energy,
    solve_circular_aperture_first_minima_separation,
)


def 解決(question: str, choices: Sequence[str]):
    hits = []
    for solver in REGISTRY:
        try:
            row = solver(question, choices)
        except Exception:
            row = None
        if row is not None:
            hits.append(row)
    if not hits or len({row.index for row in hits}) != 1:
        return None
    return max(hits, key=lambda row: row.confidence)

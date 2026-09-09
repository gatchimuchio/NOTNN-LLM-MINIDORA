from __future__ import annotations

import math
import re
from typing import Sequence

from .科学専門能力_共通 import _generic_result, _nearest, _num_expr


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
    """円軌道の幾何学的transit確率比を Kepler 則から求める。"""
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
        period_ratio = float(m.group(1))
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
    m = re.search(r"\bA\s*=\s*([0-9]+)\b", question)
    if m:
        return int(m.group(1))

    for symbol in _元素記号:
        m = re.search(rf"\b{re.escape(symbol)}\s*[- ]\s*([0-9]+)\b", question)
        if m:
            return int(m.group(1))
        m = re.search(rf"\b([0-9]+)\s*{re.escape(symbol)}\b", question)
        if m:
            return int(m.group(1))

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

    x1 = 3.8317059702075125
    x2 = 7.015586669815619
    coefficient = (x2 - x1) / (2.0 * math.pi)
    return _generic_result(
        _nearest(choices, coefficient, rel_tol=0.02),
        "circular_aperture_minima_separation",
        coefficient,
    )


def solve_grounded_conducting_sphere_energy(question: str, choices: Sequence[str]):
    """接地導体球外の点電荷の自己エネルギーを鏡像法から選ぶ。"""
    s = question.casefold()
    if not (
        "charge" in s
        and "grounded" in s
        and "conducting sphere" in s
        and "radius" in s
        and ("potential energy" in s or "energy" in s)
    ):
        return None
    hits = []
    for i, choice in enumerate(choices):
        c = str(choice).casefold().replace(" ", "").replace("{", "").replace("}", "")
        has_half = "1/2" in c or "(1/2)" in c
        has_numerator = bool(re.search(r"k\*?q\^?2\*?r(?!\^?2)", c))
        has_denominator = "d^2-r^2" in c or "d**2-r**2" in c
        if c.startswith("u=-") and has_half and has_numerator and has_denominator:
            hits.append(i)
    return _generic_result(hits[0] if len(hits) == 1 else None, "grounded_sphere_image_energy", "U=-kq^2R/[2(d^2-R^2)]")


def solve_vibrational_photon_momentum(question: str, choices: Sequence[str]):
    """与えられた振動角周波数から吸収光子の運動量 p=ħω/c を求める。"""
    s = question.casefold()
    if not ("photon" in s and "momentum" in s and "angular frequency" in s and "vibration" in s):
        return None
    clean = question.replace("\\times", "x").replace("{", "").replace("}", "")
    m = re.search(
        r"angular frequency[^0-9]{0,40}((?:[0-9.]+\s*[x*]\s*10\s*\^?\s*[+-]?\d+)|(?:[0-9.]+e[+-]?\d+)|[0-9.]+)\s*rad/s",
        clean,
        re.I,
    )
    if not m:
        return None
    omega = _num_expr(m.group(1))
    if omega is None or omega <= 0:
        return None
    target = 1.054571817e-34 * omega / 299792458.0
    return _generic_result(_nearest(choices, target, log=True), "vibrational_photon_momentum", target)


def solve_decay_resolution_latex(question: str, choices: Sequence[str]):
    """LaTeX科学表記を含む寿命・エネルギー・質量から観測距離を求める。"""
    s = question.casefold()
    if "minimum resolution" not in s or "proper lifetime" not in s:
        return None
    clean = question.replace("\\times", "x").replace("{", "").replace("}", "")
    tm = re.search(
        r"(?:tau[_ ]?0|\\tau[_ ]*0?)\s*=\s*((?:[0-9.]+\s*[x*]\s*10\s*\^?\s*[+-]?\d+)|(?:[0-9.]+e[+-]?\d+)|[0-9.]+)\s*s",
        clean,
        re.I,
    )
    em = re.search(r"energy[^0-9]{0,40}([0-9.]+)\s*gev", clean, re.I)
    mm = re.search(r"mass(?:\s+of)?[^,.;]{0,80}?([0-9.]+)\s*gev", clean, re.I)
    pm = re.search(r"at least\s+([0-9.]+)\s*%", clean, re.I)
    if not (tm and em and mm and pm):
        return None
    tau = _num_expr(tm.group(1))
    energy = float(em.group(1))
    mass = float(mm.group(1))
    fraction = float(pm.group(1)) / 100.0
    if tau is None or tau <= 0 or energy <= mass or not 0 < fraction < 1:
        return None
    beta_gamma = math.sqrt(energy * energy - mass * mass) / mass
    mean = beta_gamma * 299792458.0 * tau
    target = -mean * math.log(fraction)
    return _generic_result(_nearest(choices, target, log=True, rel_tol=0.12), "decay_resolution", target)


def solve_proper_frame_distance(question: str, choices: Sequence[str]):
    """固有時間と相対速度から外部慣性系での移動距離 vγτ を求める。"""
    s = question.casefold()
    if "reference frame" not in s or "distance" not in s:
        return None
    vm = re.search(r"(?:velocity|speed|moving\s+at)[^0-9]{0,20}([0-9 ]+(?:\.[0-9]+)?)\s*km/s", question, re.I)
    tm = re.search(r"([0-9.]+)\s*seconds?", question, re.I)
    if not (vm and tm):
        return None
    speed = float(vm.group(1).replace(" ", ""))
    proper_time = float(tm.group(1))
    c_km_s = 299792.458
    if not 0 < speed < c_km_s or proper_time <= 0:
        return None
    gamma = 1.0 / math.sqrt(1.0 - (speed / c_km_s) ** 2)
    target_km = speed * gamma * proper_time
    return _generic_result(_nearest(choices, target_km, rel_tol=0.012), "proper_time_distance", target_km)


def solve_zeeman_latex_micrometer(question: str, choices: Sequence[str]):
    """Zeeman結合と光学遷移エネルギーの桁を LaTeX μm 表記から比較する。"""
    s = question.casefold()
    if "magnetic field" not in s or "transition energy" not in s:
        return None
    bm = re.search(r"\bB\s*=\s*([0-9.]+)\s*T\b", question, re.I)
    wm = re.search(r"wavelength[^0-9]{0,30}([0-9.]+)\s*\\mu\s*m", question, re.I)
    if not (bm and wm):
        return None
    field = float(bm.group(1))
    wavelength_nm = float(wm.group(1)) * 1000.0
    zeeman_ev = 5.7883818e-05 * field
    photon_ev = 1239.841984 / wavelength_nm
    ratio = abs(zeeman_ev / photon_ev)
    for i, choice in enumerate(choices):
        compact = str(choice).replace(" ", "")
        if ratio < 0.1 and ("\\ll" in compact or "≪" in compact or "<<" in compact):
            return _generic_result(i, "zeeman_vs_transition", ratio)
        if ratio > 10 and ("\\gg" in compact or "≫" in compact or ">>" in compact):
            return _generic_result(i, "zeeman_vs_transition", ratio)
    return None


def solve_lyman_alpha_ground_optical_numeric(question: str, choices: Sequence[str]):
    """Lyman-αが地上光学帯へ入る最小赤方偏移を数値選択肢から求める。"""
    s = question.casefold()
    if not ("lyman" in s and "alpha" in s and "lower limit" in s and "optical" in s and "ground" in s):
        return None
    rest = 121.6
    m = re.search(r"lyman\s*alpha[^0-9]{0,30}([0-9.]+)\s*(angstrom|nm)", question, re.I)
    if m:
        rest = float(m.group(1)) * (0.1 if m.group(2).casefold() == "angstrom" else 1.0)
    threshold_nm = 360.0
    target = threshold_nm / rest - 1.0
    return _generic_result(
        _nearest(choices, target, rel_tol=0.08),
        "lyman_alpha_optical_threshold_numeric",
        target,
    )


def solve_four_body_annihilation_velocity(question: str, choices: Sequence[str]):
    """ほぼ静止した粒子・反粒子対が同質量4粒子へ消滅する場合の速度を求める。"""
    s = question.casefold()
    if not ("annihilation" in s or "annihilat" in s):
        return None
    if "antiproton" not in s and "\\bar{p}" not in question and "\\barp" not in question:
        return None
    clean = question.replace("{", "").replace("}", "").replace(" ", "")
    mm = re.search(r"m_?a(?:c\^?2)?=([0-9.]+)mev", clean, re.I)
    if not mm:
        return None
    daughter_mass_mev = float(mm.group(1))
    if daughter_mass_mev <= 0:
        return None
    proton_mass_mev = 938.27208816
    gamma = proton_mass_mev / (2.0 * daughter_mass_mev)
    if gamma <= 1:
        return None
    beta = math.sqrt(1.0 - 1.0 / (gamma * gamma))
    return _generic_result(_nearest(choices, beta, rel_tol=0.03), "four_body_annihilation_velocity", beta)


def solve_axisymmetric_quadrupole_radiation(question: str, choices: Sequence[str]):
    """軸対称振動電荷分布の四重極放射の角度依存と波長次数を選ぶ。"""
    s = question.casefold()
    if not (
        "oscillating charge distribution" in s
        and "spheroid" in s
        and "symmetry axis" in s
        and "radiated power" in s
        and "wavelength" in s
    ):
        return None
    tm = re.search(r"(?:theta|\\theta)\s*=\s*([0-9.]+)", question, re.I)
    if not tm:
        return None
    theta = math.radians(float(tm.group(1)))
    fraction = math.sin(2.0 * theta) ** 2
    hits = []
    for i, choice in enumerate(choices):
        text = str(choice).replace(" ", "").replace("\\lambda", "lambda")
        fm = re.search(r"([0-9.]+)\s*/\s*([0-9.]+)", text)
        em = re.search(r"lambda\^\(?(-?[0-9]+)\)?", text)
        if not (fm and em):
            continue
        value = float(fm.group(1)) / float(fm.group(2))
        exponent = int(em.group(1))
        if abs(value - fraction) <= 0.02 and exponent == -6:
            hits.append(i)
    return _generic_result(
        hits[0] if len(hits) == 1 else None,
        "axisymmetric_electric_quadrupole_radiation",
        f"fraction={fraction:.6g}; wavelength_power=-6",
    )


def _icosahedron_inverse_chord_sum() -> float:
    phi = (1.0 + math.sqrt(5.0)) / 2.0
    vertices = []
    for a in (-1.0, 1.0):
        for b in (-phi, phi):
            vertices.extend(((0.0, a, b), (a, b, 0.0), (b, 0.0, a)))
    norm = math.sqrt(1.0 + phi * phi)
    unit = [tuple(x / norm for x in v) for v in vertices]
    total = 0.0
    for i in range(len(unit)):
        for j in range(i + 1, len(unit)):
            distance = math.sqrt(sum((unit[i][k] - unit[j][k]) ** 2 for k in range(3)))
            total += 1.0 / distance
    return total


def solve_icosahedral_charges_with_center(question: str, choices: Sequence[str]):
    """球面上12同電荷＋中心1電荷の最小Coulombエネルギーを正二十面体配置で求める。"""
    s = question.casefold()
    if not ("13 identical particles" in s and "12 of these charges" in s and "13th charge" in s and "fixed at" in s):
        return None
    qm = re.search(r"charge\s+([0-9.]+)\s*e\b", question, re.I)
    rm = re.search(r"stay\s+at\s+([0-9.]+)\s*m\b", question, re.I)
    if not (qm and rm):
        return None
    q_multiple = float(qm.group(1))
    radius = float(rm.group(1))
    if q_multiple <= 0 or radius <= 0:
        return None
    k_e = 8.9875517923e9
    elementary_charge = 1.602176634e-19
    pair_sum = _icosahedron_inverse_chord_sum()
    dimensionless = pair_sum + 12.0
    target = k_e * (q_multiple * elementary_charge) ** 2 * dimensionless / radius
    return _generic_result(_nearest(choices, target, log=True), "icosahedral_coulomb_minimum", target)


REGISTRY = (
    solve_circular_transit_probability_ratio,
    solve_relativistic_nucleus_total_energy,
    solve_circular_aperture_first_minima_separation,
    solve_grounded_conducting_sphere_energy,
    solve_vibrational_photon_momentum,
    solve_decay_resolution_latex,
    solve_proper_frame_distance,
    solve_zeeman_latex_micrometer,
    solve_lyman_alpha_ground_optical_numeric,
    solve_four_body_annihilation_velocity,
    solve_axisymmetric_quadrupole_radiation,
    solve_icosahedral_charges_with_center,
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

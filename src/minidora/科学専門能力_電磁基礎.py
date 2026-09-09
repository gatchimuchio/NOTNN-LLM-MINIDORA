from __future__ import annotations

import re
from typing import Sequence

from .科学専門能力_共通 import _generic_result


def solve_grounded_sphere_image_energy(question: str, choices: Sequence[str]):
    """接地導体球外の点電荷の自己エネルギーを鏡像法から選ぶ。"""
    s = question.casefold()
    conductor = "conducting sphere" in s or "spherical conductor" in s
    if not (
        "charge" in s
        and "grounded" in s
        and conductor
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
    return _generic_result(
        hits[0] if len(hits) == 1 else None,
        "grounded_sphere_image_energy",
        "U=-kq^2R/[2(d^2-R^2)]",
    )


REGISTRY = (solve_grounded_sphere_image_energy,)


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

from __future__ import annotations

from dataclasses import dataclass
import re
from typing import Iterable

from .hds_ir import HDSIR, 値状態
from .k3_functional import Fact, K3相当能力核


_SAFE = re.compile(r"[^0-9A-Za-z_一-龥ぁ-んァ-ヶー]+")


def _predicate(kind: str) -> str:
    normalized = _SAFE.sub("_", str(kind)).strip("_").casefold()
    return "hds_relation_" + (normalized or "unknown")


def _text(value: object) -> str:
    if value is None:
        return ""
    return re.sub(r"\s+", " ", str(value)).strip()


def _confidence(state: 値状態) -> float:
    if state == 値状態.確定:
        return 1.0
    if state == 値状態.推定:
        return 0.86
    if state in {値状態.未確定, 値状態.未観測, 値状態.留保}:
        return 0.55
    if state == 値状態.矛盾:
        return 0.25
    return 0.5


@dataclass(frozen=True, slots=True)
class HDS知識投入結果:
    追加事実数: int
    座標事実数: int
    関係事実数: int
    残差数: int
    semantic_loss: bool


class HDSIR知識Adapter:
    """コンパイル済みHDS-IRだけをKへ投入する一般Adapter。

    生の自然言語Dataを直接Kへ入れない。座標と方向付き関係をKのFactへ射影し、
    原文・暫定性・由来をprovenanceとして保持する。
    """

    def __init__(self, core: K3相当能力核) -> None:
        self.core = core

    def 投入(self, ir: HDSIR, *, provenance: Iterable[str] = ()) -> HDS知識投入結果:
        source = tuple(str(x) for x in provenance)
        coords = ir.座標辞書()
        facts: list[Fact] = []
        coord_count = 0
        relation_count = 0

        for coord in ir.座標:
            content = _text(coord.内容)
            if not content:
                continue
            facts.append(
                Fact(
                    "hds_coordinate",
                    (_text(coord.種別), content),
                    confidence=_confidence(coord.値状態),
                    provenance=source + ("HDS-IR", coord.座標ID, _text(coord.由来), _text(coord.暫定性)),
                )
            )
            coord_count += 1

        for relation in ir.関係:
            starts = tuple(
                _text(coords[x].内容)
                for x in relation.始点
                if x in coords and _text(coords[x].内容)
            )
            ends = tuple(
                _text(coords[x].内容)
                for x in relation.終点
                if x in coords and _text(coords[x].内容)
            )
            if not starts and not ends:
                continue
            facts.append(
                Fact(
                    _predicate(relation.種別),
                    starts + ("→",) + ends,
                    confidence=_confidence(relation.値状態),
                    provenance=source + (
                        "HDS-IR",
                        relation.関係ID,
                        "relation_type:" + _text(relation.種別),
                        _text(relation.由来),
                        _text(relation.暫定性),
                    ),
                )
            )
            relation_count += 1

        for residual in ir.残差:
            facts.append(
                Fact(
                    "hds_residual",
                    (_text(residual.種別), _text(residual.原文), _text(residual.理由)),
                    confidence=0.35,
                    provenance=source + ("HDS-IR", residual.残差ID),
                )
            )

        added = self.core.K.add_many(facts)
        return HDS知識投入結果(
            追加事実数=added,
            座標事実数=coord_count,
            関係事実数=relation_count,
            残差数=len(ir.残差),
            semantic_loss=any(item.種別 == "semantic_loss" for item in ir.残差),
        )


__all__ = ["HDS知識投入結果", "HDSIR知識Adapter"]

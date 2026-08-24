from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable

from .hds_ir import HDS関係


_SCOPE_KEYS = ("極性", "様相", "量化", "比較", "条件種別", "条件表層", "蓋然性")
_DEFAULT_POLARITY = "肯定"


@dataclass(frozen=True, slots=True)
class HDS関係Scope:
    極性: str = _DEFAULT_POLARITY
    様相: str = ""
    量化: str = ""
    比較: str = ""
    条件種別: str = ""
    条件表層: str = ""
    蓋然性: str = ""

    @property
    def 非既定(self) -> bool:
        return (
            self.極性 != _DEFAULT_POLARITY
            or bool(self.様相)
            or bool(self.量化)
            or bool(self.比較)
            or bool(self.条件種別)
            or bool(self.条件表層)
            or bool(self.蓋然性)
        )

    def 署名(self) -> tuple[str, ...]:
        return (
            self.極性,
            self.様相,
            self.量化,
            self.比較,
            self.条件種別,
            _正規化表層(self.条件表層),
            self.蓋然性,
        )

    def ラベル(self) -> tuple[str, ...]:
        labels: list[str] = []
        if self.極性 != _DEFAULT_POLARITY:
            labels.append(self.極性)
        if self.様相:
            labels.append("様相:" + self.様相)
        if self.量化:
            labels.append("量化:" + self.量化)
        if self.比較:
            labels.append("比較:" + self.比較)
        if self.条件種別:
            labels.append("条件:" + self.条件種別)
        if self.条件表層:
            labels.append("条件表層:" + _正規化表層(self.条件表層))
        if self.蓋然性:
            labels.append("蓋然性:" + self.蓋然性)
        return tuple(labels)


def _正規化表層(value: object) -> str:
    return " ".join(str(value).casefold().split()).strip(" ,;:。！？?.")


def _条件辞書(conditions: Iterable[object]) -> dict[str, str]:
    out: dict[str, str] = {}
    for raw in conditions:
        value = str(raw).strip()
        if "=" not in value:
            continue
        key, item = value.split("=", 1)
        key = key.strip()
        if key in _SCOPE_KEYS and key not in out:
            out[key] = item.strip()
    return out


def _scope_from_mapping(values: dict[str, str]) -> HDS関係Scope:
    return HDS関係Scope(
        極性=values.get("極性") or _DEFAULT_POLARITY,
        様相=values.get("様相", ""),
        量化=values.get("量化", ""),
        比較=values.get("比較", ""),
        条件種別=values.get("条件種別", ""),
        条件表層=values.get("条件表層", ""),
        蓋然性=values.get("蓋然性", ""),
    )


def HDS関係Scope抽出(relation: HDS関係) -> HDS関係Scope:
    return _scope_from_mapping(_条件辞書(relation.条件))


def K事実関係Scope抽出(fact: object) -> HDS関係Scope:
    values: dict[str, str] = {}
    prefix = "relation_condition:"
    for raw in getattr(fact, "provenance", ()):
        marker = str(raw)
        if not marker.startswith(prefix):
            continue
        payload = marker[len(prefix):]
        if "=" not in payload:
            continue
        key, item = payload.split("=", 1)
        key = key.strip()
        if key in _SCOPE_KEYS and key not in values:
            values[key] = item.strip()
    return _scope_from_mapping(values)


def HDS関係Scope一致(left: HDS関係Scope, right: HDS関係Scope) -> bool:
    """構造的な直接一致ではscopeを推論せず、観測された意味条件をそのまま比較する。"""
    return left.署名() == right.署名()


def HDS実効関係名(kind: object, scope: HDS関係Scope) -> str:
    """Kの粗い関係型でもscope付き関係を無条件関係へ潰さないための安定ラベル。"""
    base = " ".join(str(kind).split()).strip() or "unknown"
    labels = scope.ラベル()
    if not labels:
        return base
    # 条件表層は長大化・表記揺れが大きいためpredicate名には含めず、provenanceで厳密照合する。
    coarse = tuple(label for label in labels if not label.startswith("条件表層:"))
    return ".".join((*coarse, base)) if coarse else "条件付き." + base


__all__ = [
    "HDS関係Scope",
    "HDS関係Scope抽出",
    "K事実関係Scope抽出",
    "HDS関係Scope一致",
    "HDS実効関係名",
]

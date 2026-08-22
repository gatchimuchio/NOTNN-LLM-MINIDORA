from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable, Mapping, Sequence


_CHANNEL_PRIORITY = {
    "direct": 3,
    "fact": 2,
    "document": 1,
}


@dataclass(frozen=True, slots=True)
class HDS候補証拠:
    候補: str
    出典ID: str
    得点: float
    事実ID: tuple[str, ...]
    経路: str


@dataclass(frozen=True, slots=True)
class HDS調停済証拠:
    候補: str
    出典ID: str
    元得点: float
    調停得点: float
    競合得点: float
    識別係数: float
    事実ID: tuple[str, ...]
    経路: str


@dataclass(frozen=True, slots=True)
class HDS候補調停結果:
    候補: str
    合計得点: float
    採用証拠: tuple[HDS調停済証拠, ...]

    @property
    def 独立出典数(self) -> int:
        return len({item.出典ID for item in self.採用証拠})


def _collapse_by_source(items: Iterable[HDS候補証拠]) -> dict[tuple[str, str], HDS候補証拠]:
    """同一候補・同一sourceでは最強の一経路だけを残す。

    factとdocument集約、directとfact等が同じsourceを二重加点しないための境界。
    同点なら direct > fact > document を優先する。
    """
    best: dict[tuple[str, str], HDS候補証拠] = {}
    for item in items:
        key = (item.候補, item.出典ID)
        old = best.get(key)
        if old is None:
            best[key] = item
            continue
        if item.得点 > old.得点:
            best[key] = item
            continue
        if item.得点 == old.得点 and _CHANNEL_PRIORITY.get(item.経路, 0) > _CHANNEL_PRIORITY.get(old.経路, 0):
            best[key] = item
    return best


def HDS候補横断調停(
    候補群: Sequence[str],
    証拠群: Iterable[HDS候補証拠],
    *,
    証拠重み: Sequence[float],
    証拠上限: int,
) -> Mapping[str, HDS候補調停結果]:
    """source単位で候補横断比較し、識別力の低い共通証拠を減衰する。

    一候補だけを支持するsourceは係数1.0。複数候補を同程度に支持するsourceは
    下限0.35まで減衰するが、負の証拠へは変換しない。したがって推測を生成せず、
    共通知識による過大marginだけを抑える。
    """
    labels = tuple(dict.fromkeys(str(x) for x in 候補群))
    collapsed = _collapse_by_source(証拠群)

    by_source: dict[str, dict[str, float]] = {}
    for (label, source_id), item in collapsed.items():
        by_source.setdefault(source_id, {})[label] = max(0.0, float(item.得点))

    reconciled: dict[str, list[HDS調停済証拠]] = {label: [] for label in labels}
    for (label, source_id), item in collapsed.items():
        source_scores = by_source.get(source_id, {})
        competitors = [score for other, score in source_scores.items() if other != label]
        competitor = max(competitors, default=0.0)
        own = max(0.0, float(item.得点))
        if own <= 0:
            continue
        if competitor <= 0:
            discrimination = 1.0
        else:
            specificity = own / (own + competitor)
            discrimination = 0.35 + 0.65 * specificity
        adjusted = own * discrimination
        reconciled.setdefault(label, []).append(
            HDS調停済証拠(
                候補=label,
                出典ID=source_id,
                元得点=own,
                調停得点=adjusted,
                競合得点=competitor,
                識別係数=discrimination,
                事実ID=item.事実ID,
                経路=item.経路,
            )
        )

    out: dict[str, HDS候補調停結果] = {}
    for label in labels:
        rows = sorted(
            reconciled.get(label, ()),
            key=lambda item: (-item.調停得点, item.出典ID, -_CHANNEL_PRIORITY.get(item.経路, 0)),
        )[: max(0, 証拠上限)]
        total = sum(weight * item.調停得点 for weight, item in zip(証拠重み, rows))
        out[label] = HDS候補調停結果(label, total, tuple(rows))
    return out


__all__ = [
    "HDS候補証拠",
    "HDS調停済証拠",
    "HDS候補調停結果",
    "HDS候補横断調停",
]

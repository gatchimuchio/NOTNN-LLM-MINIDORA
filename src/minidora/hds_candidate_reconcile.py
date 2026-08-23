from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable, Mapping, Sequence


_CHANNEL_PRIORITY = {
    "direct": 3,
    "fact": 2,
    "document": 1,
}
_CANDIDATE_QUERY_KINDS = {"choice", "fallback_choice", "fallback_choice_only"}
_SELF_QUERY_EVIDENCE_FACTOR = 0.18


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


def _検索由来(source_id: str) -> tuple[frozenset[str], frozenset[str]]:
    """source provenanceから候補queryとquery種別を復元する。

    source IDはHDS投入時に `query_choice:*` / `query_kind:*` を保持する。
    ここでは検索経路を真偽へ昇格させず、選択バイアスの監査にだけ利用する。
    """
    choices: set[str] = set()
    kinds: set[str] = set()
    for raw in str(source_id).split("|"):
        token = raw.strip()
        if token.startswith("query_choice:"):
            value = token.split(":", 1)[1].strip()
            if value:
                choices.add(value)
        elif token.startswith("query_kind:"):
            value = token.split(":", 1)[1].strip()
            if value:
                kinds.add(value)
    return frozenset(choices), frozenset(kinds)


def _検索選択偏り係数(label: str, source_id: str) -> float:
    """候補自身を入れた検索だけで発見されたsourceの自己支持を弱化する。

    候補Aをqueryへ含めた結果Aを含む資料が得られること自体は、Aが正しい証拠ではない。
    そのため、A専用queryだけから得たsourceがAを支持する場合は弱い発見証拠に留める。

    次は弱化しない。
    - 一般queryでも同じsourceが取得された
    - 複数候補queryで同じsourceが取得された
    - A用queryで得たsourceが別候補Bを支持する（反証・対抗証拠）
    - query provenanceを持たない既存/外部Fact
    """
    query_choices, query_kinds = _検索由来(source_id)
    if not query_choices or label not in query_choices:
        return 1.0
    if len(query_choices) != 1:
        return 1.0
    if any(kind not in _CANDIDATE_QUERY_KINDS for kind in query_kinds):
        return 1.0
    return _SELF_QUERY_EVIDENCE_FACTOR


def _識別係数(own: float, competitor: float, *, 支持候補数: int, 全候補数: int) -> float:
    """同一source内で候補を実際に識別できる差分だけを返す。

    一候補だけを支持するsourceは従来どおり1.0。同じsourceが複数候補を支持する場合は、
    絶対一致量ではなく最大競合候補に対する相対優位だけを識別力とする。完全同点または
    競合側が同等以上なら、そのsourceは当該候補の選択marginへ寄与しない。

    これにより「全候補へ同じ資料が高一致した」という共通知識を、検索順位や僅かな共通語差で
    擬似的な正答根拠へ昇格させない。
    """
    if own <= 0:
        return 0.0
    if competitor <= 0:
        return 1.0

    relative_advantage = max(0.0, (own - competitor) / max(own, competitor))
    if relative_advantage <= 0:
        return 0.0

    if 全候補数 <= 1:
        breadth_penalty = 1.0
    else:
        common_ratio = max(0.0, min(1.0, (支持候補数 - 1) / (全候補数 - 1)))
        breadth_penalty = 1.0 - 0.35 * common_ratio
    return max(0.0, min(1.0, relative_advantage * breadth_penalty))


def HDS候補横断調停(
    候補群: Sequence[str],
    証拠群: Iterable[HDS候補証拠],
    *,
    証拠重み: Sequence[float],
    証拠上限: int,
) -> Mapping[str, HDS候補調停結果]:
    """source単位で候補横断比較し、共通知識と検索選択バイアスを分離する。

    source得点へ先に検索選択偏り係数を適用し、その後で同一source内の候補差だけを識別力として
    調停する。検索経路そのものを正答根拠にせず、一般query・複数候補query・対抗証拠は保持する。
    """
    labels = tuple(dict.fromkeys(str(x) for x in 候補群))
    collapsed = _collapse_by_source(証拠群)

    effective: dict[tuple[str, str], float] = {}
    by_source: dict[str, dict[str, float]] = {}
    for (label, source_id), item in collapsed.items():
        score = max(0.0, float(item.得点)) * _検索選択偏り係数(label, source_id)
        effective[(label, source_id)] = score
        by_source.setdefault(source_id, {})[label] = score

    reconciled: dict[str, list[HDS調停済証拠]] = {label: [] for label in labels}
    for (label, source_id), item in collapsed.items():
        source_scores = by_source.get(source_id, {})
        competitors = [score for other, score in source_scores.items() if other != label]
        competitor = max(competitors, default=0.0)
        own = effective.get((label, source_id), 0.0)
        if own <= 0:
            continue
        discrimination = _識別係数(
            own,
            competitor,
            支持候補数=sum(score > 0 for score in source_scores.values()),
            全候補数=len(labels),
        )
        adjusted = own * discrimination
        if adjusted <= 0:
            continue
        reconciled.setdefault(label, []).append(
            HDS調停済証拠(
                候補=label,
                出典ID=source_id,
                元得点=max(0.0, float(item.得点)),
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

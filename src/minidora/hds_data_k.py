from __future__ import annotations

from dataclasses import dataclass
import re
from typing import Iterable

from .hds_compiler_records import HDS_COMPILER_META_PREFIXES
from .hds_ir import HDSIR, HDS関係, 値状態
from .k3_functional import Fact, K3相当能力核


_SURFACE_ONLY_KINDS = {
    "source_text",
    "language.input",
    "language.normalized",
    "対象.原文保持",
    "文脈.言語",
}
_EVIDENCE_ATTR = "_hds_evidence_facts"
_GRAPH_REVISION_ATTR = "_hds_graph_revision"
_GRAPH_CACHE_ATTR = "_hds_graph_index_cache"


def _predicate(kind: str) -> str:
    normalized = re.sub(r"\s+", " ", str(kind)).strip()
    return "hds_relation_" + (normalized or "unknown")


def _text(value: object) -> str:
    if value is None:
        return ""
    return re.sub(r"\s+", " ", str(value)).strip()


def _relation_condition(relation: HDS関係, key: str) -> str:
    prefix = key + "="
    for raw in relation.条件:
        value = _text(raw)
        if value.startswith(prefix):
            return value[len(prefix):].strip()
    return ""


def _effective_relation_kind(relation: HDS関係) -> str:
    """Kのgraphで意味の異なる関係を同じ辺へ潰さないための実効関係名。"""
    kind = _text(relation.種別) or "unknown"
    if _relation_condition(relation, "極性") == "否定":
        return "否定." + kind
    return kind


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


def _source_confidence(value: float) -> float:
    return min(1.0, max(0.0, float(value)))


def _combined_confidence(state: 値状態, source_confidence: float) -> float:
    return _confidence(state) * _source_confidence(source_confidence)


def _state_marker(state: 値状態) -> str:
    return "value_state:" + state.value


def _source_marker(value: float) -> str:
    return f"source_confidence:{_source_confidence(value):.6f}"


def _証拠台帳(core: K3相当能力核) -> dict[str, Fact]:
    ledger = getattr(core.K, _EVIDENCE_ATTR, None)
    if ledger is None:
        ledger = {}
        setattr(core.K, _EVIDENCE_ATTR, ledger)
    return ledger


def _graph索引無効化(core: K3相当能力核) -> None:
    revision = int(getattr(core.K, _GRAPH_REVISION_ATTR, 0)) + 1
    setattr(core.K, _GRAPH_REVISION_ATTR, revision)
    if hasattr(core.K, _GRAPH_CACHE_ATTR):
        delattr(core.K, _GRAPH_CACHE_ATTR)


def HDS証拠事実(core: K3相当能力核) -> tuple[Fact, ...]:
    ledger = getattr(core.K, _EVIDENCE_ATTR, {})
    return tuple(ledger.values())


def HDS証拠状態複製(source: K3相当能力核, destination: K3相当能力核) -> None:
    ledger = getattr(source.K, _EVIDENCE_ATTR, None)
    if ledger is not None:
        setattr(destination.K, _EVIDENCE_ATTR, dict(ledger))
    revision = int(getattr(source.K, _GRAPH_REVISION_ATTR, 0))
    setattr(destination.K, _GRAPH_REVISION_ATTR, revision)
    if hasattr(destination.K, _GRAPH_CACHE_ATTR):
        delattr(destination.K, _GRAPH_CACHE_ATTR)


def _残差阻害(ir: HDSIR) -> tuple[bool, dict[str, tuple[str, ...]]]:
    source_blocked = any(item.種別 == "semantic_loss" for item in ir.残差)
    impacted: dict[str, list[str]] = {}
    for residual in ir.残差:
        for coordinate_id in residual.影響座標:
            impacted.setdefault(str(coordinate_id), []).append(str(residual.種別))
    return source_blocked, {key: tuple(values) for key, values in impacted.items()}


def _残差marker(source_blocked: bool, kinds: Iterable[str]) -> tuple[str, ...]:
    kinds_tuple = tuple(str(kind) for kind in kinds)
    blocked = source_blocked or bool(kinds_tuple)
    markers: list[str] = []
    if blocked:
        markers.append("value_state:留保")
    if source_blocked:
        markers.append("residual_blocked:semantic_loss")
    markers.extend("residual_blocked:" + kind for kind in kinds_tuple)
    return tuple(dict.fromkeys(markers))


@dataclass(frozen=True, slots=True)
class HDS知識投入結果:
    追加事実数: int
    座標事実数: int
    関係事実数: int
    残差数: int
    semantic_loss: bool
    証拠事実数: int = 0
    証拠阻害事実数: int = 0
    source_confidence: float = 1.0


class HDSIR知識Adapter:
    """コンパイル済みHDS-IRをKへ投入する一般Adapter。

    HDSの値状態confidenceとR側のsource confidenceを分離して受け取り、Kへ入るFact強度は
    その積とする。関係の極性・検索述語・条件等もprovenanceへ保持し、否定関係はK graph上でも
    肯定関係と別predicateへ分離する。残差影響構造は監査用に保持しつつ確定回答証拠へ昇格させない。
    """

    def __init__(self, core: K3相当能力核) -> None:
        self.core = core

    def 投入(
        self,
        ir: HDSIR,
        *,
        provenance: Iterable[str] = (),
        信頼係数: float = 1.0,
    ) -> HDS知識投入結果:
        source = tuple(str(x) for x in provenance)
        source_confidence = _source_confidence(信頼係数)
        source_marker = _source_marker(source_confidence)
        coords = ir.座標辞書()
        facts: list[Fact] = []
        coord_count = 0
        relation_count = 0
        blocked_count = 0
        source_blocked, impacted = _残差阻害(ir)

        for coord in ir.座標:
            kind = _text(coord.種別)
            if kind in _SURFACE_ONLY_KINDS or kind.startswith(HDS_COMPILER_META_PREFIXES):
                continue
            content = _text(coord.内容)
            if not content:
                continue
            residual_markers = _残差marker(source_blocked, impacted.get(coord.座標ID, ()))
            if residual_markers:
                blocked_count += 1
            facts.append(Fact(
                "hds_coordinate",
                (kind, content),
                confidence=_combined_confidence(coord.値状態, source_confidence),
                provenance=source + ("HDS-IR", coord.座標ID, _state_marker(coord.値状態), source_marker, *residual_markers, _text(coord.由来), _text(coord.暫定性)),
            ))
            coord_count += 1

        for relation in ir.関係:
            starts = tuple(_text(coords[x].内容) for x in relation.始点 if x in coords and _text(coords[x].内容))
            ends = tuple(_text(coords[x].内容) for x in relation.終点 if x in coords and _text(coords[x].内容))
            if not starts and not ends:
                continue
            affected_kinds: list[str] = []
            for coordinate_id in (*relation.始点, *relation.終点):
                affected_kinds.extend(impacted.get(coordinate_id, ()))
            residual_markers = _残差marker(source_blocked, affected_kinds)
            if residual_markers:
                blocked_count += 1
            effective_kind = _effective_relation_kind(relation)
            condition_markers = tuple(
                "relation_condition:" + _text(condition)
                for condition in relation.条件
                if _text(condition)
            )
            facts.append(Fact(
                _predicate(effective_kind),
                starts + ("→",) + ends,
                confidence=_combined_confidence(relation.値状態, source_confidence),
                provenance=source + (
                    "HDS-IR",
                    relation.関係ID,
                    _state_marker(relation.値状態),
                    source_marker,
                    *residual_markers,
                    "relation_type:" + _text(relation.種別),
                    "relation_effective_type:" + effective_kind,
                    *condition_markers,
                    _text(relation.由来),
                    _text(relation.暫定性),
                ),
            ))
            relation_count += 1

        for residual in ir.残差:
            facts.append(Fact(
                "hds_residual",
                (_text(residual.種別), _text(residual.原文), _text(residual.理由), *tuple(_text(x) for x in residual.影響座標)),
                confidence=0.35 * source_confidence,
                provenance=source + ("HDS-IR", residual.残差ID, "value_state:留保", source_marker, *tuple("impact:" + str(x) for x in residual.影響座標)),
            ))

        ledger = _証拠台帳(self.core)
        for fact in facts:
            ledger.setdefault(fact.fact_id, fact)

        added = self.core.K.add_many(facts)
        _graph索引無効化(self.core)
        return HDS知識投入結果(
            追加事実数=added,
            座標事実数=coord_count,
            関係事実数=relation_count,
            残差数=len(ir.残差),
            semantic_loss=source_blocked,
            証拠事実数=len(facts),
            証拠阻害事実数=blocked_count,
            source_confidence=source_confidence,
        )


__all__ = [
    "HDS知識投入結果",
    "HDSIR知識Adapter",
    "HDS証拠事実",
    "HDS証拠状態複製",
]

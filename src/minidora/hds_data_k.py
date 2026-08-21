from __future__ import annotations

from dataclasses import dataclass
import re
from typing import Iterable

from .hds_ir import HDSIR, 値状態
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
    """HDS関係種別を可逆にK predicateへ写す。

    `記述→問い` を `記述_問い` へ潰すと、問いIR側の生関係ラベルと再照合できなくなる。
    Fact predicateは識別子制約を持たないため、空白だけ正規化して関係記号を保持する。
    """
    normalized = re.sub(r"\s+", " ", str(kind)).strip()
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


def _state_marker(state: 値状態) -> str:
    return "value_state:" + state.value


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


class HDSIR知識Adapter:
    """コンパイル済みHDS-IRだけをKへ投入する一般Adapter。

    Kには残差を含む全構造を監査用として保持する。一方、残差が影響する座標・関係は
    `value_state:留保` / `residual_blocked:*` を付与し、J/HDSの確定回答証拠・graph経路へは昇格させない。
    """

    def __init__(self, core: K3相当能力核) -> None:
        self.core = core

    def 投入(self, ir: HDSIR, *, provenance: Iterable[str] = ()) -> HDS知識投入結果:
        source = tuple(str(x) for x in provenance)
        coords = ir.座標辞書()
        facts: list[Fact] = []
        coord_count = 0
        relation_count = 0
        blocked_count = 0
        source_blocked, impacted = _残差阻害(ir)

        for coord in ir.座標:
            kind = _text(coord.種別)
            if kind in _SURFACE_ONLY_KINDS:
                continue
            content = _text(coord.内容)
            if not content:
                continue
            residual_markers = _残差marker(source_blocked, impacted.get(coord.座標ID, ()))
            if residual_markers:
                blocked_count += 1
            facts.append(Fact(
                "hds_coordinate", (kind, content), confidence=_confidence(coord.値状態),
                provenance=source + ("HDS-IR", coord.座標ID, _state_marker(coord.値状態), *residual_markers, _text(coord.由来), _text(coord.暫定性)),
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
            facts.append(Fact(
                _predicate(relation.種別), starts + ("→",) + ends,
                confidence=_confidence(relation.値状態),
                provenance=source + ("HDS-IR", relation.関係ID, _state_marker(relation.値状態), *residual_markers, "relation_type:" + _text(relation.種別), _text(relation.由来), _text(relation.暫定性)),
            ))
            relation_count += 1

        for residual in ir.残差:
            facts.append(Fact(
                "hds_residual", (_text(residual.種別), _text(residual.原文), _text(residual.理由), *tuple(_text(x) for x in residual.影響座標)),
                confidence=0.35,
                provenance=source + ("HDS-IR", residual.残差ID, "value_state:留保", *tuple("impact:" + str(x) for x in residual.影響座標)),
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
        )


__all__ = ["HDS知識投入結果", "HDSIR知識Adapter", "HDS証拠事実"]

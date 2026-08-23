from __future__ import annotations

from dataclasses import dataclass
import re
from typing import Iterable

from .hds_compiler_records import HDS_COMPILER_META_PREFIXES
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
_CANDIDATE_QUERY_KINDS = {"choice", "fallback_choice", "fallback_choice_only"}
_RETRIEVAL_SELECTION_FACTOR = 0.25


def _predicate(kind: str) -> str:
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


def _source_confidence(value: float) -> float:
    return min(1.0, max(0.0, float(value)))


def _combined_confidence(state: 値状態, source_confidence: float) -> float:
    return _confidence(state) * _source_confidence(source_confidence)


def _state_marker(state: 値状態) -> str:
    return "value_state:" + state.value


def _source_marker(value: float) -> str:
    return f"source_confidence:{_source_confidence(value):.6f}"


def _retrieval_marker(value: float) -> str:
    return f"retrieval_independence:{min(1.0, max(0.0, float(value))):.6f}"


def _retrieval_independence(provenance: Iterable[str]) -> float:
    """検索選択と真偽証拠の独立性を保守的に評価する。

    候補そのものを含むqueryでしか発見されていない資料は、その候補語・問い語との表層一致が
    検索条件によって事前選択されている。この一致を独立な真偽証拠と同じ強度へ昇格させない。

    同一資料がstructured/focus/entity等の候補非依存queryからも取得されている場合は、検索選択
    への依存が解消されたとみなし従来強度を維持する。これは資料自体のsource confidenceとは
    別軸であり、GPQAや正解ラベルには依存しない。
    """
    source = tuple(str(x) for x in provenance)
    query_kinds = {
        item.split(":", 1)[1]
        for item in source
        if item.startswith("query_kind:") and ":" in item
    }
    has_choice = any(item.startswith("query_choice:") for item in source)
    candidate_only = bool(query_kinds & _CANDIDATE_QUERY_KINDS)
    neutral = bool(query_kinds - _CANDIDATE_QUERY_KINDS)
    if has_choice and candidate_only and not neutral:
        return _RETRIEVAL_SELECTION_FACTOR
    return 1.0


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
    retrieval_independence: float = 1.0


class HDSIR知識Adapter:
    """コンパイル済みHDS-IRをKへ投入する一般Adapter。

    HDSの値状態confidence、R側のsource confidence、検索選択からの独立性を分離して扱う。
    Kへ入るFact強度は三者の積とする。候補指定queryでしか見つからない資料は検索条件による
    自己支持を避けるため補助証拠へ減衰し、候補非依存queryでも同じ資料が見つかった場合は
    従来強度へ戻す。残差影響構造は監査用に保持しつつ確定回答証拠・graph経路へ昇格させない。
    Compilerの監査メタ座標も実世界Factへ昇格させない。
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
        retrieval_independence = _retrieval_independence(source)
        effective_confidence = source_confidence * retrieval_independence
        source_marker = _source_marker(source_confidence)
        retrieval_marker = _retrieval_marker(retrieval_independence)
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
                confidence=_combined_confidence(coord.値状態, effective_confidence),
                provenance=source + (
                    "HDS-IR", coord.座標ID, _state_marker(coord.値状態), source_marker,
                    retrieval_marker, *residual_markers, _text(coord.由来), _text(coord.暫定性),
                ),
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
                _predicate(relation.種別),
                starts + ("→",) + ends,
                confidence=_combined_confidence(relation.値状態, effective_confidence),
                provenance=source + (
                    "HDS-IR", relation.関係ID, _state_marker(relation.値状態), source_marker,
                    retrieval_marker, *residual_markers, "relation_type:" + _text(relation.種別),
                    _text(relation.由来), _text(relation.暫定性),
                ),
            ))
            relation_count += 1

        for residual in ir.残差:
            facts.append(Fact(
                "hds_residual",
                (_text(residual.種別), _text(residual.原文), _text(residual.理由), *tuple(_text(x) for x in residual.影響座標)),
                confidence=0.35 * effective_confidence,
                provenance=source + (
                    "HDS-IR", residual.残差ID, "value_state:留保", source_marker, retrieval_marker,
                    *tuple("impact:" + str(x) for x in residual.影響座標),
                ),
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
            retrieval_independence=retrieval_independence,
        )


__all__ = [
    "HDS知識投入結果",
    "HDSIR知識Adapter",
    "HDS証拠事実",
    "HDS証拠状態複製",
]

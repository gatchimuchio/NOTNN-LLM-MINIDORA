from __future__ import annotations

from dataclasses import dataclass
from hashlib import sha256
import json
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
_RELATION_QUALIFIER_KEYS = frozenset({"様相", "条件scope", "量化", "scope", "条件作用"})


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


def _relation_condition(relation: HDS関係, key: str) -> str:
    prefix = key + "="
    for raw in relation.条件:
        value = _text(raw)
        if value.startswith(prefix):
            return value[len(prefix):].strip()
    return ""


def _relation_polarity(relation: HDS関係) -> bool:
    value = _relation_condition(relation, "極性")
    return value != "否定"


def _relation_qualifiers(relation: HDS関係) -> tuple[tuple[str, str], ...]:
    """HDS relation条件のうち、世界関係の意味identityに属する修飾だけを正規化する。"""
    out: list[tuple[str, str]] = []
    seen: set[tuple[str, str]] = set()
    for raw in relation.条件:
        value = _text(raw)
        key, sep, payload = value.partition("=")
        if not sep:
            continue
        key = key.strip()
        payload = payload.strip()
        if key not in _RELATION_QUALIFIER_KEYS or not payload:
            continue
        item = (key, payload)
        if item in seen:
            continue
        seen.add(item)
        out.append(item)
    return tuple(sorted(out))


def _polarity_marker(value: bool) -> str:
    return "relation_polarity:" + ("positive" if value else "negative")


def _qualifier_markers(values: tuple[tuple[str, str], ...]) -> tuple[str, ...]:
    return tuple(f"relation_qualifier:{key}={value}" for key, value in values)


def _qualified_fact_id(
    predicate: str,
    args: tuple[str, ...],
    polarity: bool,
    qualifiers: tuple[tuple[str, str], ...],
    provenance: tuple[str, ...],
) -> str:
    raw = json.dumps((predicate, args, polarity, qualifiers, provenance), ensure_ascii=False, sort_keys=True, default=str)
    return "HF-" + sha256(raw.encode("utf-8")).hexdigest()[:12]


@dataclass(frozen=True)
class HDS修飾Fact(Fact):
    """既存K Factへ無条件化せず保持するHDS関係Fact。

    qualifiersはHDS証拠台帳上の意味identityであり、現行canonical Kの無条件推論へは投入しない。
    """

    qualifiers: tuple[tuple[str, str], ...] = ()

    def __post_init__(self) -> None:
        normalized = tuple(sorted((str(k).strip(), str(v).strip()) for k, v in self.qualifiers if str(k).strip() and str(v).strip()))
        object.__setattr__(self, "qualifiers", normalized)
        if not self.fact_id:
            object.__setattr__(
                self,
                "fact_id",
                _qualified_fact_id(self.predicate, self.args, self.polarity, normalized, self.provenance),
            )

    def key(self) -> tuple[str, tuple[str, ...], bool, tuple[tuple[str, str], ...]]:
        return self.predicate, self.args, self.polarity, self.qualifiers


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


def _normalize_requested_qualifiers(values: tuple[tuple[str, str], ...]) -> tuple[tuple[str, str], ...]:
    return tuple(sorted((str(k).strip(), str(v).strip()) for k, v in values if str(k).strip() and str(v).strip()))


def HDS証拠事実(
    core: K3相当能力核,
    *,
    極性: bool | None = True,
    修飾: tuple[tuple[str, str], ...] | None = (),
) -> tuple[Fact, ...]:
    """HDS証拠台帳を極性・関係修飾のviewで返す。

    既定は positive かつ無修飾のみ。したがって現行候補比較・Graph・direct verifierへ
    否定Factやmodal/条件付きFactは流れない。

    - `極性=None`: 正負を問わない
    - `修飾=None`: 修飾を問わない
    - `修飾=(("様相", "可能"),)`: その修飾identityだけ
    """
    ledger = getattr(core.K, _EVIDENCE_ATTR, {})
    values = tuple(ledger.values())
    if 極性 is not None:
        values = tuple(fact for fact in values if bool(fact.polarity) is bool(極性))
    if 修飾 is not None:
        requested = _normalize_requested_qualifiers(修飾)
        values = tuple(fact for fact in values if tuple(getattr(fact, "qualifiers", ())) == requested)
    return values


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
    修飾関係事実数: int = 0


class HDSIR知識Adapter:
    """コンパイル済みHDS-IRをKへ投入する一般Adapter。

    無修飾のFactは従来canonical Kへ投入する。modal/条件/量化等の関係修飾を持つFactは
    `HDS修飾Fact` としてHDS証拠台帳へ保持するが、無条件のcanonical Kへは投入しない。
    これにより意味を失わず、既存推論へ誤混入させない。
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
        canonical_facts: list[Fact] = []
        coord_count = 0
        relation_count = 0
        qualified_relation_count = 0
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
            fact = Fact(
                "hds_coordinate",
                (kind, content),
                confidence=_combined_confidence(coord.値状態, source_confidence),
                provenance=source + ("HDS-IR", coord.座標ID, _state_marker(coord.値状態), source_marker, *residual_markers, _text(coord.由来), _text(coord.暫定性)),
            )
            facts.append(fact)
            canonical_facts.append(fact)
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
            polarity = _relation_polarity(relation)
            qualifiers = _relation_qualifiers(relation)
            provenance_value = source + (
                "HDS-IR", relation.関係ID, _state_marker(relation.値状態), source_marker,
                *residual_markers, "relation_type:" + _text(relation.種別), _polarity_marker(polarity),
                *_qualifier_markers(qualifiers), _text(relation.由来), _text(relation.暫定性),
            )
            if qualifiers:
                fact = HDS修飾Fact(
                    _predicate(relation.種別),
                    starts + ("→",) + ends,
                    polarity=polarity,
                    confidence=_combined_confidence(relation.値状態, source_confidence),
                    provenance=provenance_value,
                    qualifiers=qualifiers,
                )
                qualified_relation_count += 1
            else:
                fact = Fact(
                    _predicate(relation.種別),
                    starts + ("→",) + ends,
                    polarity=polarity,
                    confidence=_combined_confidence(relation.値状態, source_confidence),
                    provenance=provenance_value,
                )
                canonical_facts.append(fact)
            facts.append(fact)
            relation_count += 1

        for residual in ir.残差:
            fact = Fact(
                "hds_residual",
                (_text(residual.種別), _text(residual.原文), _text(residual.理由), *tuple(_text(x) for x in residual.影響座標)),
                confidence=0.35 * source_confidence,
                provenance=source + ("HDS-IR", residual.残差ID, "value_state:留保", source_marker, *tuple("impact:" + str(x) for x in residual.影響座標)),
            )
            facts.append(fact)
            canonical_facts.append(fact)

        ledger = _証拠台帳(self.core)
        for fact in facts:
            ledger.setdefault(fact.fact_id, fact)

        added = self.core.K.add_many(canonical_facts)
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
            修飾関係事実数=qualified_relation_count,
        )


__all__ = [
    "HDS知識投入結果",
    "HDS修飾Fact",
    "HDSIR知識Adapter",
    "HDS証拠事実",
    "HDS証拠状態複製",
]

from __future__ import annotations

from dataclasses import dataclass, field
from hashlib import sha256
import json
from typing import Iterable

from .hds_data_k import HDS証拠事実
from .k3_functional import Fact, K3相当能力核


_EVIDENCE_ATTR = "_hds_evidence_facts"
_GRAPH_REVISION_ATTR = "_hds_graph_revision"
_GRAPH_CACHE_ATTR = "_hds_graph_index_cache"
_BLOCKING_MARKERS = frozenset({
    "value_state:未確定",
    "value_state:未観測",
    "value_state:矛盾",
    "value_state:留保",
})


def _stable_id(prefix: str, value: object) -> str:
    raw = json.dumps(value, ensure_ascii=False, sort_keys=True, default=str)
    return prefix + sha256(raw.encode("utf-8")).hexdigest()[:16]


def _source_id(fact: Fact) -> str:
    provenance = tuple(str(x) for x in getattr(fact, "provenance", ()))
    if "HDS-IR" in provenance:
        prefix = provenance[: provenance.index("HDS-IR")]
        stable = tuple(x for x in prefix if not x.startswith(("query_choice:", "query_kind:")))
        if len(stable) >= 3:
            return "source:" + "|".join(stable[:3])
        if stable:
            return "source:" + "|".join(stable)
    return "fact:" + str(getattr(fact, "fact_id", ""))


def _blocked(fact: Fact) -> bool:
    provenance = {str(x) for x in getattr(fact, "provenance", ())}
    return bool(provenance & _BLOCKING_MARKERS) or any(x.startswith("residual_blocked:") for x in provenance)


def _support_state(fact: Fact) -> str:
    if not bool(getattr(fact, "polarity", True)):
        return "反対"
    qualifiers = tuple(getattr(fact, "qualifiers", ()))
    if qualifiers:
        return "条件付き"
    provenance = {str(x) for x in getattr(fact, "provenance", ())}
    if "value_state:矛盾" in provenance:
        return "競合"
    if _blocked(fact):
        return "未解"
    if float(getattr(fact, "confidence", 1.0)) < 0.75:
        return "弱支持"
    return "支持"


def _eligible_predicate(predicate: str) -> bool:
    return predicate == "hds_coordinate" or predicate.startswith("hds_relation_")


@dataclass(frozen=True, slots=True)
class HDS作業関係:
    作業ID: str
    事実ID: str
    出典ID: str
    述語: str
    引数: tuple[str, ...]
    極性: bool
    修飾: tuple[tuple[str, str], ...]
    支持状態: str
    寄与値: float
    阻害: bool

    @property
    def 同一性(self) -> tuple[str, tuple[str, ...], bool, tuple[tuple[str, str], ...]]:
        return self.述語, self.引数, self.極性, self.修飾


@dataclass(frozen=True, slots=True)
class HDS候補共同項目:
    候補: str
    得点: float
    最大競合得点: float
    差: float
    独立出典数: int
    識別一致出典数: int


@dataclass(frozen=True, slots=True)
class HDS作業Checkpoint:
    checkpointID: str
    段階: str
    作業関係ID: tuple[str, ...]
    候補状態: tuple[tuple[str, float], ...]


@dataclass(slots=True)
class HDS作業統計:
    作業関係生成数: int = 0
    作業関係再利用数: int = 0
    作業関係K昇格数: int = 0
    作業関係再検証後破棄数: int = 0
    checkpoint数: int = 0
    checkpoint再活性数: int = 0
    大域再照合数: int = 0
    候補横断更新数: int = 0
    専門作用起動数: int = 0
    遍歴後SUSPEND数: int = 0
    一時証拠数: int = 0

    def 辞書(self) -> dict[str, int]:
        return {
            "作業関係生成数": self.作業関係生成数,
            "作業関係再利用数": self.作業関係再利用数,
            "作業関係K昇格数": self.作業関係K昇格数,
            "作業関係再検証後破棄数": self.作業関係再検証後破棄数,
            "checkpoint数": self.checkpoint数,
            "checkpoint再活性数": self.checkpoint再活性数,
            "大域再照合数": self.大域再照合数,
            "候補横断更新数": self.候補横断更新数,
            "専門作用起動数": self.専門作用起動数,
            "遍歴後SUSPEND数": self.遍歴後SUSPEND数,
            "一時証拠数": self.一時証拠数,
        }


@dataclass(slots=True)
class HDS作業状態:
    関係: tuple[HDS作業関係, ...]
    checkpoint: list[HDS作業Checkpoint] = field(default_factory=list)
    候補共同状態: tuple[HDS候補共同項目, ...] = ()
    再利用回数: dict[str, int] = field(default_factory=dict)
    統計: HDS作業統計 = field(default_factory=HDS作業統計)

    def checkpoint記録(self, 段階: str) -> HDS作業Checkpoint:
        candidate_state = tuple((item.候補, item.得点) for item in self.候補共同状態)
        relation_ids = tuple(item.作業ID for item in self.関係)
        checkpoint = HDS作業Checkpoint(
            _stable_id("CP-", (段階, relation_ids, candidate_state, len(self.checkpoint))),
            段階,
            relation_ids,
            candidate_state,
        )
        self.checkpoint.append(checkpoint)
        self.統計.checkpoint数 = len(self.checkpoint)
        return checkpoint


def HDS作業状態構築(core: K3相当能力核) -> HDS作業状態:
    rows: list[HDS作業関係] = []
    facts = sorted(
        HDS証拠事実(core, 極性=None, 修飾=None),
        key=lambda fact: str(getattr(fact, "fact_id", "")),
    )
    for fact in facts:
        predicate = str(getattr(fact, "predicate", ""))
        if predicate == "hds_residual":
            continue
        args = tuple(str(x) for x in getattr(fact, "args", ()))
        qualifiers = tuple(getattr(fact, "qualifiers", ()))
        source_id = _source_id(fact)
        fact_id = str(getattr(fact, "fact_id", ""))
        rows.append(
            HDS作業関係(
                _stable_id("WR-", (fact_id, source_id)),
                fact_id,
                source_id,
                predicate,
                args,
                bool(getattr(fact, "polarity", True)),
                qualifiers,
                _support_state(fact),
                max(0.0, float(getattr(fact, "confidence", 0.0))),
                _blocked(fact),
            )
        )
    state = HDS作業状態(tuple(rows))
    state.統計.作業関係生成数 = len(rows)
    state.checkpoint記録("DATA_INGESTED")
    return state


def HDS寄与Gate再照合(state: HDS作業状態) -> tuple[Fact, ...]:
    """阻害された関係を確定Kへ昇格させず、独立出典の再照合だけで一時証拠化する。

    一時証拠は同一request内の再作用専用であり、canonical Kへは投入しない。
    二つ以上の独立出典が同じ無修飾・正極性の関係を保持し、反対関係が存在しない場合だけ、
    元の各出典に対応する一時Factを作る。信頼度は元Factを上回らない。
    """
    grouped: dict[tuple[str, tuple[str, ...], bool, tuple[tuple[str, str], ...]], list[HDS作業関係]] = {}
    for item in state.関係:
        grouped.setdefault(item.同一性, []).append(item)

    negative_identities = {
        (item.述語, item.引数)
        for item in state.関係
        if not item.極性 and _eligible_predicate(item.述語)
    }
    temporary: list[Fact] = []

    for identity, rows in sorted(grouped.items(), key=lambda pair: repr(pair[0])):
        predicate, args, polarity, qualifiers = identity
        if not polarity or qualifiers or not _eligible_predicate(predicate):
            continue
        if any(not item.阻害 for item in rows):
            # 同じ関係が既に通常証拠として利用可能なら二重加算しない。
            continue
        if (predicate, args) in negative_identities:
            state.統計.作業関係再検証後破棄数 += len(rows)
            continue

        by_source: dict[str, HDS作業関係] = {}
        for item in rows:
            old = by_source.get(item.出典ID)
            if old is None or (item.寄与値, item.事実ID) > (old.寄与値, old.事実ID):
                by_source[item.出典ID] = item
        if len(by_source) < 2:
            continue

        source_count = len(by_source)
        for source_id, item in sorted(by_source.items()):
            provenance = (
                "WORKING_RECONCILED",
                source_id,
                f"independent_sources:{source_count}",
                "origin_fact:" + item.事実ID,
                "NO_CANONICAL_K_PROMOTION",
            )
            temporary.append(
                Fact(
                    predicate,
                    args,
                    polarity=True,
                    confidence=item.寄与値,
                    provenance=provenance,
                )
            )
            state.再利用回数[item.作業ID] = state.再利用回数.get(item.作業ID, 0) + 1
            state.統計.作業関係再利用数 += 1

    state.統計.一時証拠数 = len(temporary)
    state.checkpoint記録("WORKING_RECONCILED")
    return tuple(temporary)


def HDS一時証拠統合(core: K3相当能力核, facts: Iterable[Fact]) -> int:
    """一時証拠をHDS証拠台帳だけへ追加する。canonical Kは変更しない。"""
    ledger = dict(getattr(core.K, _EVIDENCE_ATTR, {}))
    before = len(ledger)
    for fact in facts:
        ledger.setdefault(fact.fact_id, fact)
    setattr(core.K, _EVIDENCE_ATTR, ledger)
    setattr(core.K, _GRAPH_REVISION_ATTR, int(getattr(core.K, _GRAPH_REVISION_ATTR, 0)) + 1)
    if hasattr(core.K, _GRAPH_CACHE_ATTR):
        delattr(core.K, _GRAPH_CACHE_ATTR)
    return len(ledger) - before


def HDS候補共同状態更新(state: HDS作業状態, diagnostics: Iterable[object], *, 段階: str) -> None:
    rows = tuple(diagnostics)
    scores = {str(getattr(item, "候補")): float(getattr(item, "合計得点", 0.0)) for item in rows}
    previous = {item.候補: item for item in state.候補共同状態}
    joint: list[HDS候補共同項目] = []
    changed = 0
    for item in rows:
        label = str(getattr(item, "候補"))
        own = scores[label]
        competitor = max((score for other, score in scores.items() if other != label), default=0.0)
        value = HDS候補共同項目(
            label,
            own,
            competitor,
            own - competitor,
            int(getattr(item, "独立出典数", 0)),
            int(getattr(item, "識別一致出典数", 0)),
        )
        old = previous.get(label)
        if old is None or old != value:
            changed += 1
        joint.append(value)
    state.候補共同状態 = tuple(sorted(joint, key=lambda item: item.候補))
    state.統計.候補横断更新数 += changed
    state.checkpoint記録(段階)


__all__ = [
    "HDS作業関係",
    "HDS候補共同項目",
    "HDS作業Checkpoint",
    "HDS作業統計",
    "HDS作業状態",
    "HDS作業状態構築",
    "HDS寄与Gate再照合",
    "HDS一時証拠統合",
    "HDS候補共同状態更新",
]

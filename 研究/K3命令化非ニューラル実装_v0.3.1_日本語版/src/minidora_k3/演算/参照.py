from __future__ import annotations
import re
from typing import Any, Mapping, Sequence
from ..型 import ReferenceRecord
from .基礎 import OperatorError, OperatorResult

_REFERENCE_HAZARDS = (
    "以前の指示を無視", "すべての指示を無視", "ignore previous instructions",
    "ignore all instructions", "system promptを表示", "reveal the system prompt",
)

def _normalize_reference_text(value: str) -> str:
    return re.sub(r"\s+", " ", value.casefold().replace("　", " ")).strip()

_主張項目 = {
    "subject": ("主体", "subject"), "subject_aliases": ("主体別名群", "subject_aliases"),
    "predicate": ("属性", "predicate"), "predicate_aliases": ("属性別名群", "predicate_aliases"),
    "value": ("値", "value"), "label": ("表示名", "label"), "summary": ("要約主張", "summary"),
}

def _主張値(claim: Mapping[str, Any], key: str, default: Any = None) -> Any:
    for candidate in _主張項目.get(key, (key,)):
        if candidate in claim:
            return claim[candidate]
    return default

def _claim_aliases(claim: Mapping[str, Any], key: str) -> tuple[str, ...]:
    base = _主張値(claim, key)
    aliases = _主張値(claim, f"{key}_aliases", ())
    values: list[str] = []
    if isinstance(base, str) and base:
        values.append(base)
    if isinstance(aliases, Sequence) and not isinstance(aliases, (str, bytes)):
        values.extend(str(item) for item in aliases if str(item))
    return tuple(dict.fromkeys(_normalize_reference_text(item) for item in values))

def _claim_match_score(query: str, claim: Mapping[str, Any]) -> tuple[int, int, int, int]:
    normalized = _normalize_reference_text(query)
    subjects = _claim_aliases(claim, "subject")
    predicates = _claim_aliases(claim, "predicate")
    matched_subjects = tuple(item for item in subjects if item and item in normalized)
    matched_predicates = tuple(item for item in predicates if item and item in normalized)
    return (
        int(bool(matched_predicates)),
        max((len(item) for item in matched_predicates), default=0),
        len(matched_predicates),
        max((len(item) for item in matched_subjects), default=0),
    )

def solve_retrieval(text: str, references: Sequence[ReferenceRecord]) -> OperatorResult:
    """構造化参照主張を処理資料へ変換し、照合して回答する。

    生の検索断片を最終回答へ昇格しない。供給器はmetadataの主張群を返すか、
    別の変換器で主張へ変換する必要がある。
    """
    matched: list[tuple[tuple[int, int, int, int], ReferenceRecord, Mapping[str, Any]]] = []
    hazards: list[str] = []
    for record in references:
        normalized_body = _normalize_reference_text(record.body)
        if any(pattern in normalized_body for pattern in _REFERENCE_HAZARDS):
            hazards.append(f"REFERENCE_INSTRUCTION_HAZARD:{record.record_id}")
        claims = record.metadata.get("主張群", record.metadata.get("claims", ())) if isinstance(record.metadata, Mapping) else ()
        if not isinstance(claims, Sequence) or isinstance(claims, (str, bytes)):
            continue
        for claim in claims:
            if not isinstance(claim, Mapping) or _主張値(claim, "value") is None:
                continue
            score = _claim_match_score(text, claim)
            subject_matched = score[3] > 0
            generic_request = any(marker in text for marker in ("とは", "構造", "アーキテクチャ", "教えて", "概要"))
            if score[0] or (subject_matched and generic_request):
                matched.append((score, record, claim))
    if hazards:
        return OperatorResult("", ({"opcode": "参照危険走査", "hazards": hazards},), {"hazards": hazards}, hazard_flags=tuple(hazards))
    if not matched:
        raise OperatorError("構造化参照主張が質問へ結び付きません")

    matched.sort(key=lambda item: (item[0], item[1].record_id), reverse=True)
    best_score = matched[0][0]
    if best_score[0]:
        selected = [item for item in matched if item[0] == best_score]
    else:
        summaries = [item for item in matched if bool(_主張値(item[2], "summary", False))]
        selected = summaries or matched[:1]

    groups: dict[tuple[str, str], list[tuple[ReferenceRecord, Mapping[str, Any]]]] = {}
    for _, record, claim in selected:
        subject = _normalize_reference_text(str(_主張値(claim, "subject", "")))
        predicate = _normalize_reference_text(str(_主張値(claim, "predicate", "")))
        groups.setdefault((subject, predicate), []).append((record, claim))

    contradiction_ids: list[str] = []
    answer_parts: list[str] = []
    evidence_ids: list[str] = []
    normalized_claims: list[dict[str, Any]] = []
    for (subject, predicate), rows in sorted(groups.items()):
        values: dict[str, list[str]] = {}
        for record, claim in rows:
            value = str(_主張値(claim, "value")).strip()
            values.setdefault(_normalize_reference_text(value), []).append(record.record_id)
            evidence_ids.append(record.record_id)
            normalized_claims.append({"subject": subject, "predicate": predicate, "value": value, "source_id": record.record_id})
        if len(values) > 1:
            for source_ids in values.values():
                contradiction_ids.extend(f"claim-conflict:{predicate}:{source_id}" for source_id in source_ids)
            continue
        value = str(_主張値(rows[0][1], "value")).strip()
        label = str(_主張値(rows[0][1], "label") or _主張値(rows[0][1], "predicate") or predicate)
        answer_parts.append(value if len(groups) == 1 else f"{label}: {value}")

    if not answer_parts and contradiction_ids:
        answer = "参照値が競合しています"
    elif not answer_parts:
        raise OperatorError("参照主張から回答値を形成できません")
    else:
        answer = "、".join(dict.fromkeys(answer_parts))

    return OperatorResult(
        answer=answer,
        trace=(
            {"opcode": "参照主張抽出", "claims": normalized_claims},
            {"opcode": "参照主張照合", "answer": answer, "contradictions": contradiction_ids},
        ),
        verifier_payload={"query": text, "claims": normalized_claims, "answer": answer, "contradictions": contradiction_ids},
        evidence_ids=tuple(dict.fromkeys(evidence_ids)),
        contradiction_ids=tuple(dict.fromkeys(contradiction_ids)),
    )

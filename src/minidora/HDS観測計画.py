from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable

from .HDS中間表現 import HDSIR, HDS関係, 値状態
from .意味字句 import 意味語

_BLOCKING = {値状態.未確定, 値状態.未観測, 値状態.矛盾, 値状態.留保}
_RELATION_META_KEYS = frozenset({
    "検索述語", "不足位置", "英日意味射影", "受動態", "選択意図", "選択問題閉包",
})
_GENERIC_RELATIONS = frozenset({"問い適合", "命題適合", "説明適合"})


@dataclass(frozen=True, slots=True)
class HDS参照観測要求:
    """Compiler KernelからRへ渡す完成済み観測要求。

    意味関係と外部検索文脈を別フィールドで保持する。Rは原文・意味IRを再解釈せず、
    ``外部検索表層`` をproviderへ降下するだけでよい。
    """

    ID: str
    関係ID: str | None
    関係種別: str | None
    未知位置: str | None
    既知端点: tuple[str, ...]
    条件scope: tuple[tuple[str, str], ...]
    候補ラベル: str | None
    候補表層: str | None
    外部言語: str
    外部検索表層: str
    必須被覆: bool
    外部文脈アンカー: tuple[str, ...] = ()
    段階: str = "primary"
    優先度: int = 50
    provenance: tuple[str, ...] = ()


def _unique(parts: Iterable[str]) -> tuple[str, ...]:
    out: list[str] = []
    seen: set[str] = set()
    for raw in parts:
        value = " ".join(str(raw).split()).strip()
        if not value:
            continue
        key = value.casefold()
        if key in seen:
            continue
        seen.add(key)
        out.append(value)
    return tuple(out)


def _意味集合(values: Iterable[str]) -> frozenset[str]:
    out: set[str] = set()
    for value in values:
        out.update(str(x).casefold() for x in 意味語(value) if str(x))
    return frozenset(out)


def _条件値(関係: HDS関係, key: str) -> str:
    prefix = key + "="
    for raw in 関係.条件:
        value = str(raw)
        if value.startswith(prefix):
            return value[len(prefix):].strip()
    return ""


def _局所scope(関係: HDS関係) -> tuple[tuple[str, str], ...]:
    out: list[tuple[str, str]] = []
    seen: set[tuple[str, str]] = set()
    for raw in 関係.条件:
        key, sep, payload = str(raw).partition("=")
        key, payload = key.strip(), payload.strip()
        if not sep or not key or not payload or key in _RELATION_META_KEYS:
            continue
        item = (key, payload)
        if item in seen:
            continue
        seen.add(item)
        out.append(item)
    return tuple(out)


def _選択肢(ir: HDSIR) -> tuple[tuple[str, str], ...]:
    out: list[tuple[str, str]] = []
    for coord in ir.座標:
        if not str(coord.座標ID).startswith("選択肢:"):
            continue
        label = str(coord.座標ID).split(":", 1)[1]
        value = " ".join(str(coord.内容).split()).strip()
        if label and value:
            out.append((label, value))
    return tuple(sorted(out))


def _検索表層(ir: HDSIR) -> tuple[str, ...]:
    return _unique(
        str(coord.内容)
        for coord in ir.座標
        if str(coord.種別).startswith("検索.")
        and coord.値状態 not in {値状態.矛盾, 値状態.留保}
    )


def _fallback対象(ir: HDSIR) -> tuple[str, ...]:
    return _unique(
        str(coord.内容)
        for coord in ir.座標
        if str(coord.種別).startswith(("対象.", "実体."))
        and coord.値状態 not in _BLOCKING
        and str(coord.内容).strip()
    )


def _汎用外部文脈(ir: HDSIR) -> tuple[str, ...]:
    """関係未閉包時にもKernelが保持する外部観測用の意味文脈。

    Rで原文を読み直さず、Compilerが既に構文化した対象・関係表層・状態・属性・値・条件だけを使う。
    制御・監査・選択肢・未知位置などの実行メタは混ぜない。
    """
    prefixes = ("対象.", "実体.", "関係.", "状態.", "属性.", "値.", "条件.", "時刻.", "時間.", "範囲.")
    return _unique(
        str(coord.内容)
        for coord in ir.座標
        if not str(coord.座標ID).startswith("選択肢:")
        and str(coord.種別).startswith(prefixes)
        and coord.値状態 not in _BLOCKING
        and str(coord.内容).strip()
    )


def _監査表層(ir: HDSIR) -> tuple[str, ...]:
    return _unique(
        str(coord.内容)
        for coord in ir.座標
        if str(coord.種別) == "監査.R_query"
        and coord.値状態 != 値状態.矛盾
    )


def _既知端点(ir: HDSIR, 関係: HDS関係, position: str) -> tuple[str, ...]:
    coords = ir.座標辞書()
    ids = 関係.終点 if position == "始点" else 関係.始点
    return _unique(
        str(coords[cid].内容)
        for cid in ids
        if cid in coords and coords[cid].値状態 not in _BLOCKING
    )


def _query_surface(
    *,
    predicate: str,
    position: str,
    known: tuple[str, ...],
    scope: tuple[tuple[str, str], ...],
    candidate: str | None,
) -> str:
    scoped = tuple(value for _key, value in scope)
    if candidate is None:
        if position == "始点":
            return " ".join(_unique((predicate, *known, *scoped)))
        return " ".join(_unique((*known, predicate, *scoped)))
    if position == "始点":
        parts = (candidate, predicate, *known, *scoped)
    else:
        parts = (*known, predicate, candidate, *scoped)
    return " ".join(_unique(parts))


def _関連検索文脈(
    search_surfaces: tuple[str, ...],
    *,
    predicate: str,
    known: tuple[str, ...],
    scope: tuple[tuple[str, str], ...],
    最大: int = 2,
) -> tuple[str, ...]:
    """Compilerが既に抽出した外部検索表層から、関係観測の文脈anchorを選ぶ。
    意味分類をRでやり直さないため、ここでCompiler Kernel内で選ぶ。

    """
    if not search_surfaces:
        return ()
    needles = _unique((predicate, *known, *(value for _key, value in scope)))
    scored: list[tuple[int, int, str]] = []
    for index, surface in enumerate(search_surfaces):
        low = surface.casefold()
        score = sum(1 for needle in needles if needle.casefold() in low)
        scored.append((score, -index, surface))
    scored.sort(reverse=True)
    related = [surface for score, _order, surface in scored if score > 0]
    if not related:
        related = list(search_surfaces)
    return tuple(related[:max(1, int(最大))])


def _外部表層(local_surface: str, context: tuple[str, ...]) -> str:
    # 文脈anchorと局所意味を両方保持する。重複した完全表層だけを除き、語句の削除はしない。
    return " ".join(_unique((*context, local_surface)))


def HDS参照観測要求群(ir: HDSIR) -> tuple[HDS参照観測要求, ...]:
    """Kernel意味正本を再解析せず、外部観測へ降下可能な要求群を構成する。"""

    choices = _選択肢(ir)
    search_surfaces = _検索表層(ir)
    audit_surfaces = _監査表層(ir)
    fallback_targets = _fallback対象(ir)
    language = str(ir.入力言語 or "ja")
    requests: list[HDS参照観測要求] = []
    concrete = 0
    planned_relations = 0
    relation_signatures: set[tuple[object, ...]] = set()
    canonical_relations: list[tuple[str, str, frozenset[str]]] = []

    for candidate_relation in ir.関係:
        candidate_position = _条件値(candidate_relation, "不足位置")
        candidate_predicate = _条件値(candidate_relation, "検索述語")
        if candidate_position not in {"始点", "終点"} or not candidate_predicate:
            continue
        if not _条件値(candidate_relation, "英日意味射影"):
            continue
        candidate_known = _既知端点(ir, candidate_relation, candidate_position)
        candidate_scope = _局所scope(candidate_relation)
        terms = _意味集合((*candidate_known, *(value for _key, value in candidate_scope)))
        canonical_relations.append((candidate_position, str(candidate_relation.種別), terms))

    for 関係 in ir.関係:
        position = _条件値(関係, "不足位置")
        predicate = _条件値(関係, "検索述語")
        if position not in {"始点", "終点"} or not predicate:
            continue
        planned_relations += 1
        known = _既知端点(ir, 関係, position)
        scope = _局所scope(関係)
        generic = str(関係.種別) in _GENERIC_RELATIONS or bool(_条件値(関係, "選択問題閉包"))
        relation_kind = str(関係.種別)
        if not _条件値(関係, "英日意味射影"):
            local_terms = _意味集合((*known, *(value for _key, value in scope)))
            dominated = any(
                c_position == position
                and c_kind == relation_kind
                and local_terms
                and c_terms
                and (local_terms <= c_terms or c_terms <= local_terms)
                for c_position, c_kind, c_terms in canonical_relations
            )
            if dominated:
                continue
        predicate_key = (
            str(predicate).casefold()
            if relation_kind in {"開放述語", "問い適合"}
            else relation_kind
        )
        signature = (
            position,
            predicate_key,
            tuple(str(x).casefold() for x in known),
            tuple((str(k), str(v).casefold()) for k, v in scope),
            generic,
        )
        if signature in relation_signatures:
            continue
        relation_signatures.add(signature)
        stage = "fallback" if generic else "primary"
        base_priority = 90 if generic else 10
        if not generic:
            concrete += 1

        context = _関連検索文脈(
            search_surfaces,
            predicate=predicate,
            known=known,
            scope=scope,
        )
        local_anchor = (
            " ".join(_unique((*known, *(value for _key, value in scope))))
            if generic
            else _query_surface(
                predicate=predicate,
                position=position,
                known=known,
                scope=scope,
                candidate=None,
            )
        )
        anchor = _外部表層(local_anchor, context) if local_anchor else " ".join(context)
        if anchor:
            requests.append(HDS参照観測要求(
                ID=f"関係:{関係.関係ID}:anchor",
                関係ID=str(関係.関係ID),
                関係種別=str(関係.種別),
                未知位置=position,
                既知端点=known,
                条件scope=scope,
                候補ラベル=None,
                候補表層=None,
                外部言語=language,
                外部検索表層=anchor,
                必須被覆=False,
                外部文脈アンカー=context,
                段階=stage,
                優先度=base_priority,
                provenance=(f"関係:{関係.関係ID}", "Compiler外部文脈"),
            ))

        bound_choices = choices or (("_", ""),)
        for label, candidate in bound_choices:
            local_surface = (
                " ".join(_unique((candidate, *known, *(value for _key, value in scope))))
                if generic and candidate
                else _query_surface(
                    predicate=predicate,
                    position=position,
                    known=known,
                    scope=scope,
                    candidate=candidate or None,
                )
            )
            surface = _外部表層(local_surface, context) if local_surface else " ".join(context)
            if not surface:
                continue
            observation_id = f"関係:{関係.関係ID}:候補:{label}" if choices else f"関係:{関係.関係ID}:観測"
            requests.append(HDS参照観測要求(
                ID=observation_id,
                関係ID=str(関係.関係ID),
                関係種別=str(関係.種別),
                未知位置=position,
                既知端点=known,
                条件scope=scope,
                候補ラベル=None if label == "_" else label,
                候補表層=candidate or None,
                外部言語=language,
                外部検索表層=surface,
                必須被覆=True,
                外部文脈アンカー=context,
                段階=stage,
                優先度=base_priority + 1,
                provenance=(f"関係:{関係.関係ID}", f"候補:{label}", "Compiler外部文脈"),
            ))
            if candidate:
                fallback_parts = (
                    " ".join(_unique((*known, candidate))),
                    candidate,
                )
                for offset, fallback_surface in enumerate(_unique(fallback_parts), start=1):
                    if fallback_surface.casefold() == surface.casefold():
                        continue
                    requests.append(HDS参照観測要求(
                        ID=observation_id,
                        関係ID=str(関係.関係ID),
                        関係種別=str(関係.種別),
                        未知位置=position,
                        既知端点=known,
                        条件scope=scope,
                        候補ラベル=label,
                        候補表層=candidate,
                        外部言語=language,
                        外部検索表層=fallback_surface,
                        必須被覆=True,
                        外部文脈アンカー=(),
                        段階="fallback",
                        優先度=base_priority + 20 + offset,
                        provenance=(f"関係:{関係.関係ID}", f"候補:{label}", "縮退"),
                    ))

    # 外部検索表層そのものも独立観測として残す。関係queryへのanchor利用とは別責任。
    for index, surface in enumerate(search_surfaces):
        requests.append(HDS参照観測要求(
            ID=f"検索表層:{index}",
            関係ID=None,
            関係種別=None,
            未知位置=None,
            既知端点=(),
            条件scope=(),
            候補ラベル=None,
            候補表層=None,
            外部言語=language,
            外部検索表層=surface,
            必須被覆=False,
            外部文脈アンカー=(surface,),
            段階="primary",
            優先度=20 if concrete else 40,
            provenance=("検索.外部表層",),
        ))

    for index, surface in enumerate(audit_surfaces):
        requests.append(HDS参照観測要求(
            ID=f"監査表層:{index}",
            関係ID=None,
            関係種別=None,
            未知位置=None,
            既知端点=(),
            条件scope=(),
            候補ラベル=None,
            候補表層=None,
            外部言語=language,
            外部検索表層=surface,
            必須被覆=False,
            外部文脈アンカー=(),
            段階="fallback",
            優先度=80,
            provenance=("監査.R_query",),
        ))

    if choices and planned_relations == 0:
        generic_context = _汎用外部文脈(ir)
        generic_primary = search_surfaces[0] if search_surfaces else " ".join(generic_context)
        if generic_primary:
            requests.append(HDS参照観測要求(
                ID="汎用文脈:0",
                関係ID=None,
                関係種別="未解決関係",
                未知位置=None,
                既知端点=fallback_targets,
                条件scope=(),
                候補ラベル=None,
                候補表層=None,
                外部言語=language,
                外部検索表層=generic_primary,
                必須被覆=False,
                外部文脈アンカー=generic_context or (generic_primary,),
                段階="primary",
                優先度=35,
                provenance=("Compiler汎用外部文脈",),
            ))
        anchor = search_surfaces[0] if search_surfaces else " ".join(fallback_targets)
        for label, candidate in choices:
            observation_id = f"generic:候補:{label}"
            surfaces = _unique((" ".join(_unique((anchor, candidate))), candidate))
            for offset, surface in enumerate(surfaces):
                if not surface:
                    continue
                requests.append(HDS参照観測要求(
                    ID=observation_id,
                    関係ID=None,
                    関係種別="未解決関係",
                    未知位置=None,
                    既知端点=fallback_targets,
                    条件scope=(),
                    候補ラベル=label,
                    候補表層=candidate,
                    外部言語=language,
                    外部検索表層=surface,
                    必須被覆=True,
                    外部文脈アンカー=(anchor,) if anchor and offset == 0 else (),
                    段階="fallback",
                    優先度=95 + offset,
                    provenance=("未解決関係", f"候補:{label}"),
                ))

    out: list[HDS参照観測要求] = []
    seen: set[tuple[str, str, str]] = set()
    for request in sorted(requests, key=lambda x: (x.優先度, x.ID, x.外部検索表層.casefold())):
        key = (request.ID, request.段階, request.外部検索表層.casefold())
        if key in seen:
            continue
        seen.add(key)
        out.append(request)
    return tuple(out)


__all__ = ["HDS参照観測要求", "HDS参照観測要求群"]

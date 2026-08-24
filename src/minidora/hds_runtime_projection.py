from __future__ import annotations

from dataclasses import replace
import re

from .hds_compiler_records import HDS_COMPILER_META_PREFIXES
from .hds_ir import HDSIR, HDS座標, HDS関係, 値状態
from .semantic_tokens import 意味語


_SURFACE_ONLY_KINDS = {
    "source_text",
    "language.input",
    "language.normalized",
    "対象.原文保持",
    "文脈.言語",
}
_K_NON_SEMANTIC_PREFIXES = HDS_COMPILER_META_PREFIXES + (
    "検索.",
    "制御.",
    "目的.",
)
_R_CONTEXT_PREFIXES = (
    "検索.",
    "条件.",
    "文脈.",
    "時刻.",
    "時間.",
    "範囲.",
)
_R_FALLBACK_SEMANTIC_PREFIXES = (
    "対象.",
    "実体.",
    "状態.",
    "属性.",
    "値.",
)
_R_CONTROL_CONDITION_KINDS = frozenset({"条件.検索極性"})
_BLOCKING = {値状態.未確定, 値状態.未観測, 値状態.矛盾, 値状態.留保}
_K_UNSUPPORTED_SCOPE_SURFACE = re.compile(
    r"\b(?:not|never|cannot|can't|can\s+not|does\s+not|do\s+not|did\s+not|"
    r"may|might|could|would|can|must|should|unless)\b",
    re.I,
)
_K_UNSUPPORTED_SCOPE_KEYS = frozenset({"様相", "量化", "条件scope", "scope", "条件作用"})
_K_SCOPE_COORD_KINDS = frozenset({"不確実性.明示", "前提.明示", "射程.明示", "動態.分岐"})


def _条件値(relation: HDS関係, key: str) -> str:
    prefix = key + "="
    for raw in relation.条件:
        value = str(raw)
        if value.startswith(prefix):
            return value[len(prefix):].strip()
    return ""


def _座標重複除去(*groups: tuple[HDS座標, ...]) -> tuple[HDS座標, ...]:
    out: list[HDS座標] = []
    seen: set[str] = set()
    for group in groups:
        for coord in group:
            cid = str(coord.座標ID)
            if cid in seen:
                continue
            seen.add(cid)
            out.append(coord)
    return tuple(out)


def _文字列重複除去(values: tuple[str, ...]) -> tuple[str, ...]:
    out: list[str] = []
    seen: set[str] = set()
    for raw in values:
        value = " ".join(str(raw).split()).strip()
        if not value:
            continue
        key = value.casefold()
        if key in seen:
            continue
        seen.add(key)
        out.append(value)
    return tuple(out)


def _R利用座標(coord: HDS座標) -> bool:
    kind = str(coord.種別)
    return kind not in _R_CONTROL_CONDITION_KINDS


def _R検索表層(coords: tuple[HDS座標, ...], relations: tuple[HDS関係, ...] = ()) -> str:
    search = tuple(str(coord.内容) for coord in coords if str(coord.種別).startswith("検索."))
    predicates = tuple(_条件値(relation, "検索述語") for relation in relations)
    known_endpoints = tuple(
        str(coord.内容)
        for coord in coords
        if str(coord.種別).startswith(("対象.", "実体.", "状態.", "属性.", "値."))
        and coord.値状態 not in _BLOCKING
    )
    context = tuple(
        str(coord.内容)
        for coord in coords
        if str(coord.種別).startswith(("条件.", "時刻.", "時間.", "範囲."))
        and _R利用座標(coord)
        and coord.値状態 not in {値状態.矛盾, 値状態.留保}
    )
    return " ".join(_文字列重複除去((*search, *predicates, *known_endpoints, *context)))


def _K意味座標(coord: HDS座標) -> bool:
    kind = str(coord.種別)
    if kind in _SURFACE_ONLY_KINDS:
        return False
    return not kind.startswith(_K_NON_SEMANTIC_PREFIXES)


def _質問関係(ir: HDSIR) -> tuple[HDS関係, ...]:
    canonical = tuple(
        relation
        for relation in ir.関係
        if _条件値(relation, "英日意味射影")
        and _条件値(relation, "不足位置") in {"始点", "終点"}
    )
    if canonical:
        return canonical
    return tuple(
        relation
        for relation in ir.関係
        if _条件値(relation, "不足位置") in {"始点", "終点"}
    )


def _関係座標ID(relations: tuple[HDS関係, ...]) -> set[str]:
    ids: set[str] = set()
    for relation in relations:
        ids.update(relation.始点)
        ids.update(relation.終点)
    return ids


def _関係を座標へ閉じる(relations: tuple[HDS関係, ...], coordinate_ids: set[str]) -> tuple[HDS関係, ...]:
    return tuple(
        relation
        for relation in relations
        if (*relation.始点, *relation.終点)
        and all(cid in coordinate_ids for cid in (*relation.始点, *relation.終点))
    )


def _scope座標が関係へ掛かる(ir: HDSIR, relation: HDS関係, coords: dict[str, HDS座標]) -> bool:
    endpoint_terms: list[frozenset[str]] = []
    for cid in (*relation.始点, *relation.終点):
        coord = coords.get(cid)
        if coord is None:
            continue
        terms = 意味語(coord.内容)
        if terms:
            endpoint_terms.append(terms)
    if len(endpoint_terms) < 2:
        return False

    for scope in ir.座標:
        if str(scope.種別) not in _K_SCOPE_COORD_KINDS:
            continue
        scope_terms = 意味語(scope.内容)
        if not scope_terms:
            continue
        if all(terms & scope_terms for terms in endpoint_terms):
            return True
    return False


def _K未対応scope(ir: HDSIR, relation: HDS関係, coords: dict[str, HDS座標]) -> bool:
    """Kがまだ論理関係として表現できないscopeを無条件Factへ潰さない。"""
    for raw in relation.条件:
        value = str(raw)
        key, sep, payload = value.partition("=")
        if not sep:
            continue
        key = key.strip()
        payload = payload.strip()
        if key == "極性" and payload and payload != "肯定":
            return True
        if key in _K_UNSUPPORTED_SCOPE_KEYS and payload:
            return True

    for cid in (*relation.始点, *relation.終点):
        coord = coords.get(cid)
        if coord is None:
            continue
        if _K_UNSUPPORTED_SCOPE_SURFACE.search(str(coord.内容)):
            return True
    return _scope座標が関係へ掛かる(ir, relation, coords)


def _K関係射影(ir: HDSIR, coords: tuple[HDS座標, ...]) -> tuple[HDS関係, ...]:
    coord_map = {coord.座標ID: coord for coord in coords}
    closed = _関係を座標へ閉じる(ir.関係, set(coord_map))
    return tuple(relation for relation in closed if not _K未対応scope(ir, relation, coord_map))


def HDSR質問射影(ir: HDSIR) -> HDSIR:
    """質問HDS-IRからRが検索query生成に必要な最小構造だけを返す。"""
    choices = tuple(coord for coord in ir.座標 if coord.座標ID.startswith("choice:"))
    question_relations = _質問関係(ir)
    coords_by_id = ir.座標辞書()
    context = tuple(
        coord
        for coord in ir.座標
        if str(coord.種別).startswith(_R_CONTEXT_PREFIXES)
        and _R利用座標(coord)
        and coord.値状態 not in {値状態.矛盾, 値状態.留保}
        and str(coord.内容).strip()
    )

    if question_relations:
        endpoint_ids = _関係座標ID(question_relations)
        endpoints = tuple(coords_by_id[cid] for cid in endpoint_ids if cid in coords_by_id)
        projected_coords = _座標重複除去(choices, endpoints, context)
        surface = _R検索表層(projected_coords, question_relations)
        return replace(ir, 原文=surface, 正規化文=surface, 座標=projected_coords, 関係=question_relations, 意味作用履歴=())

    search_focus = tuple(coord for coord in context if str(coord.種別).startswith("検索."))
    if search_focus:
        projected_coords = _座標重複除去(choices, search_focus)
        surface = _R検索表層(projected_coords)
        return replace(ir, 原文=surface, 正規化文=surface, 座標=projected_coords, 関係=(), 意味作用履歴=())

    fallback = tuple(
        coord
        for coord in ir.座標
        if str(coord.種別).startswith((*_R_FALLBACK_SEMANTIC_PREFIXES, *_R_CONTEXT_PREFIXES))
        and _R利用座標(coord)
        and coord.値状態 not in _BLOCKING
        and str(coord.内容).strip()
    )
    relations = _関係を座標へ閉じる(ir.関係, {coord.座標ID for coord in fallback})
    projected_coords = _座標重複除去(choices, fallback)
    surface = _R検索表層(projected_coords, relations)
    return replace(ir, 原文=surface, 正規化文=surface, 座標=projected_coords, 関係=relations, 意味作用履歴=())


def HDSK質問射影(ir: HDSIR) -> HDSIR:
    """質問HDS-IRからC/Kの候補比較に必要な最小意味核だけを返す。"""
    choices = tuple(coord for coord in ir.座標 if coord.座標ID.startswith("choice:"))
    question_relations = _質問関係(ir)
    coords_by_id = ir.座標辞書()

    if question_relations:
        endpoint_ids = _関係座標ID(question_relations)
        endpoints = tuple(coords_by_id[cid] for cid in endpoint_ids if cid in coords_by_id)
        projected_relations = tuple(
            replace(
                relation,
                値状態=値状態.確定,
                由来="HDS Runtime K質問射影",
                暫定性="RELATION_TYPE_KNOWN_ENDPOINT_OPEN",
            )
            for relation in question_relations
        )
        return replace(ir, 座標=_座標重複除去(choices, endpoints), 関係=projected_relations, 意味作用履歴=())

    topic = tuple(
        coord
        for coord in ir.座標
        if str(coord.種別) == "対象.主題語"
        and coord.値状態 not in _BLOCKING
        and str(coord.内容).strip()
    )
    if topic:
        return replace(ir, 座標=_座標重複除去(choices, topic), 関係=(), 意味作用履歴=())

    semantic_coords = tuple(coord for coord in ir.座標 if _K意味座標(coord))
    semantic_relations = _K関係射影(ir, semantic_coords)
    return replace(ir, 座標=_座標重複除去(choices, semantic_coords), 関係=semantic_relations, 意味作用履歴=())


def HDSK候補射影(ir: HDSIR) -> HDSIR:
    """候補IRから候補識別とKが表現可能な明示命題だけを残す。"""
    semantic_coords = tuple(coord for coord in ir.座標 if _K意味座標(coord))
    semantic_relations = _K関係射影(ir, semantic_coords)
    return replace(ir, 座標=semantic_coords, 関係=semantic_relations, 意味作用履歴=())


def HDSKData射影(ir: HDSIR) -> HDSIR:
    """R取得DataからKへ投入してよい世界事実意味だけを残す。

    K未対応の否定・様相・条件scopeは関係Factへ縮退させず、端点語の証拠だけを残す。
    """
    semantic_coords = tuple(coord for coord in ir.座標 if _K意味座標(coord))
    semantic_relations = _K関係射影(ir, semantic_coords)
    return replace(ir, 座標=semantic_coords, 関係=semantic_relations, 意味作用履歴=())


__all__ = ["HDSR質問射影", "HDSK質問射影", "HDSK候補射影", "HDSKData射影"]

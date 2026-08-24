from __future__ import annotations

from dataclasses import replace

from .hds_compiler_records import HDS_COMPILER_META_PREFIXES
from .hds_ir import HDSIR, HDS座標, HDS関係, 値状態


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
_BLOCKING = {値状態.未確定, 値状態.未観測, 値状態.矛盾, 値状態.留保}


def _条件値(relation: HDS関係, key: str) -> str:
    prefix = key + "="
    for raw in relation.条件:
        value = str(raw)
        if value.startswith(prefix):
            return value[len(prefix):].strip()
    return ""


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
    out: list[HDS関係] = []
    for relation in relations:
        endpoints = tuple((*relation.始点, *relation.終点))
        if endpoints and all(cid in coordinate_ids for cid in endpoints):
            out.append(relation)
    return tuple(out)


def HDSR質問射影(ir: HDSIR) -> HDSIR:
    """質問HDS-IRからRが検索query生成に必要な最小構造だけを返す。

    関係質問では「候補集合 + 検索述語付き関係 + 既知/未知端点 + 検索条件」を保持する。
    一般質問ではCompilerが生成した `検索.*` を最優先し、無い場合だけ対象・状態等へ縮退する。
    選択制御・監査・保持・帰還等は検索対象ではないため除外する。
    """
    choices = tuple(coord for coord in ir.座標 if coord.座標ID.startswith("choice:"))
    question_relations = _質問関係(ir)
    coords_by_id = ir.座標辞書()
    context = tuple(
        coord
        for coord in ir.座標
        if str(coord.種別).startswith(_R_CONTEXT_PREFIXES)
        and coord.値状態 not in {値状態.矛盾, 値状態.留保}
        and str(coord.内容).strip()
    )

    if question_relations:
        endpoint_ids = _関係座標ID(question_relations)
        endpoints = tuple(coords_by_id[cid] for cid in endpoint_ids if cid in coords_by_id)
        return replace(
            ir,
            座標=tuple(dict.fromkeys((*choices, *endpoints, *context))),
            関係=question_relations,
            意味作用履歴=(),
        )

    search_focus = tuple(coord for coord in context if str(coord.種別).startswith("検索."))
    if search_focus:
        return replace(ir, 座標=tuple((*choices, *search_focus)), 関係=(), 意味作用履歴=())

    fallback = tuple(
        coord
        for coord in ir.座標
        if str(coord.種別).startswith((*_R_FALLBACK_SEMANTIC_PREFIXES, *_R_CONTEXT_PREFIXES))
        and coord.値状態 not in _BLOCKING
        and str(coord.内容).strip()
    )
    fallback_ids = {coord.座標ID for coord in fallback}
    relations = _関係を座標へ閉じる(ir.関係, fallback_ids)
    return replace(ir, 座標=tuple((*choices, *fallback)), 関係=relations, 意味作用履歴=())


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
        return replace(ir, 座標=tuple((*choices, *endpoints)), 関係=projected_relations, 意味作用履歴=())

    search_focus = tuple(
        coord
        for coord in ir.座標
        if str(coord.種別).startswith("検索.") and coord.値状態 not in _BLOCKING and str(coord.内容).strip()
    )
    if search_focus:
        projected = tuple(
            replace(
                coord,
                種別="対象.照合焦点",
                由来="HDS Runtime K質問射影",
                暫定性="SEARCH_SURFACE_AS_MATCH_FOCUS",
            )
            for coord in search_focus
        )
        return replace(ir, 座標=tuple((*choices, *projected)), 関係=(), 意味作用履歴=())

    semantic_coords = tuple(coord for coord in ir.座標 if _K意味座標(coord))
    semantic_ids = {coord.座標ID for coord in semantic_coords}
    semantic_relations = _関係を座標へ閉じる(ir.関係, semantic_ids)
    return replace(ir, 座標=tuple((*choices, *semantic_coords)), 関係=semantic_relations, 意味作用履歴=())


def HDSK候補射影(ir: HDSIR) -> HDSIR:
    """候補IRから候補識別と明示命題に必要な意味だけを残す。"""
    semantic_coords = tuple(coord for coord in ir.座標 if _K意味座標(coord))
    semantic_ids = {coord.座標ID for coord in semantic_coords}
    semantic_relations = _関係を座標へ閉じる(ir.関係, semantic_ids)
    return replace(ir, 座標=semantic_coords, 関係=semantic_relations, 意味作用履歴=())


def HDSKData射影(ir: HDSIR) -> HDSIR:
    """R取得DataからKへ投入してよい世界事実意味だけを残す。"""
    semantic_coords = tuple(coord for coord in ir.座標 if _K意味座標(coord))
    semantic_ids = {coord.座標ID for coord in semantic_coords}
    semantic_relations = _関係を座標へ閉じる(ir.関係, semantic_ids)
    return replace(ir, 座標=semantic_coords, 関係=semantic_relations, 意味作用履歴=())


__all__ = ["HDSR質問射影", "HDSK質問射影", "HDSK候補射影", "HDSKData射影"]

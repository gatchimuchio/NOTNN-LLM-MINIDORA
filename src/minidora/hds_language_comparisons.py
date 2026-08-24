from __future__ import annotations

from dataclasses import replace

from .hds_ir import HDSIR, HDS座標, HDS関係, 値状態
from .言語基底_英語_比較 import 英語比較意味抽出


_VERSION = "v0.7-clean"
_BLOCKING = {値状態.未確定, 値状態.未観測, 値状態.矛盾, 値状態.留保}


def _norm(value: object) -> str:
    return " ".join(str(value).casefold().split()).strip(" ,;:。！？?.")


def _signatures(ir: HDSIR) -> set[tuple[str, str, str]]:
    coords = ir.座標辞書()
    out: set[tuple[str, str, str]] = set()
    for relation in ir.関係:
        starts = [coords[cid] for cid in relation.始点 if cid in coords and coords[cid].値状態 not in _BLOCKING]
        ends = [coords[cid] for cid in relation.終点 if cid in coords and coords[cid].値状態 not in _BLOCKING]
        for start in starts:
            for end in ends:
                out.add((str(relation.種別), _norm(start.内容), _norm(end.内容)))
    return out


def HDS英語比較射影(ir: HDSIR) -> HDSIR:
    """英語で明示された比較・等価・不同を有向HDS関係へ射影する。

    世界知識・比較値の推測・形容詞軸の補完は行わない。`greater than` 等、比較軸が言語上
    明示されている場合だけ扱う。疑問文では未知端点を未観測として保持する。
    """
    language = str(getattr(ir, "入力言語", "") or "").casefold()
    if not language.startswith("en"):
        return ir

    meanings = 英語比較意味抽出(str(ir.正規化文 or ir.原文))
    if not meanings:
        return ir

    coords = list(ir.座標)
    relations = list(ir.関係)
    existing_ids = {coord.座標ID for coord in coords}
    existing_relation_ids = {relation.関係ID for relation in relations}
    signatures = _signatures(ir)
    added = 0

    def add_coord(base: str, kind: str, content: str, state: 値状態) -> str:
        cid = base
        serial = 1
        while cid in existing_ids:
            cid = f"{base}:{serial}"
            serial += 1
        existing_ids.add(cid)
        coords.append(HDS座標(cid, kind, content, state, 由来="共有言語基底P", 暫定性="ENGLISH_COMPARISON_PROJECTION"))
        return cid

    for meaning in meanings:
        start_text = str(meaning.始点).strip()
        end_text = str(meaning.終点).strip()
        if not start_text or not end_text:
            continue

        if not meaning.未知位置:
            signature = (meaning.種別, _norm(start_text), _norm(end_text))
            if signature in signatures:
                continue
            sid = add_coord(f"lang-cmp:start:{added}", "対象.始点", start_text, 値状態.確定)
            oid = add_coord(f"lang-cmp:end:{added}", "対象.終点", end_text, 値状態.確定)
            state = 値状態.確定
            conditions = (f"検索述語={meaning.検索述語}", f"英語比較射影={_VERSION}")
        elif meaning.未知位置 == "始点":
            sid = add_coord(f"lang-cmp:unknown-start:{added}", "目的.未知始点", meaning.要求型 or "未特定", 値状態.未観測)
            oid = add_coord(f"lang-cmp:known-end:{added}", "対象.終点", end_text, 値状態.確定)
            add_coord(f"lang-cmp:missing:{added}", "目的.不足位置", "始点", 値状態.確定)
            if meaning.要求型:
                add_coord(f"lang-cmp:type:{added}", "目的.要求型", meaning.要求型, 値状態.確定)
            state = 値状態.未観測
            conditions = (f"検索述語={meaning.検索述語}", "不足位置=始点", f"英語比較射影={_VERSION}")
        else:
            sid = add_coord(f"lang-cmp:known-start:{added}", "対象.始点", start_text, 値状態.確定)
            oid = add_coord(f"lang-cmp:unknown-end:{added}", "目的.未知終点", meaning.要求型 or "未特定", 値状態.未観測)
            add_coord(f"lang-cmp:missing:{added}", "目的.不足位置", "終点", 値状態.確定)
            if meaning.要求型:
                add_coord(f"lang-cmp:type:{added}", "目的.要求型", meaning.要求型, 値状態.確定)
            state = 値状態.未観測
            conditions = (f"検索述語={meaning.検索述語}", "不足位置=終点", f"英語比較射影={_VERSION}")

        rid = f"lang-cmp:relation:{added}"
        serial = 1
        while rid in existing_relation_ids:
            rid = f"lang-cmp:relation:{added}:{serial}"
            serial += 1
        existing_relation_ids.add(rid)
        relations.append(HDS関係(rid, (sid,), (oid,), meaning.種別, 条件=conditions, 値状態=state, 由来="共有言語基底P", 暫定性="ENGLISH_COMPARISON_PROJECTION"))
        if state == 値状態.確定:
            signatures.add((meaning.種別, _norm(start_text), _norm(end_text)))
        added += 1

    if not added:
        return ir
    return replace(ir, 座標=tuple(coords), 関係=tuple(relations))


__all__ = ["HDS英語比較射影"]

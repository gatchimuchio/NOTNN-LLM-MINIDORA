from __future__ import annotations

from dataclasses import replace

from .hds_ir import HDSIR, HDS座標, HDS関係, 値状態
from .言語基底_英語_分類 import 英語分類意味抽出


_VERSION = "v0.14-current"


def HDS英語分類射影(ir: HDSIR) -> HDSIR:
    """英語で明示された `A is a B` / `A is a type of B` だけを分類関係へ射影する。"""
    language = str(getattr(ir, "入力言語", "") or "").casefold()
    if not language.startswith("en"):
        return ir
    meanings = 英語分類意味抽出(str(ir.正規化文 or ir.原文))
    if not meanings:
        return ir

    coords = list(ir.座標)
    relations = list(ir.関係)
    existing_ids = {coord.座標ID for coord in coords}
    existing_relation_ids = {r.関係ID for r in relations}
    added = 0

    def add_coord(base: str, kind: str, content: str, state: 値状態) -> str:
        cid = base
        serial = 1
        while cid in existing_ids:
            cid = f"{base}:{serial}"
            serial += 1
        existing_ids.add(cid)
        coords.append(HDS座標(cid, kind, content, state, 由来="共有言語基底P", 暫定性="EXPLICIT_CLASSIFICATION"))
        return cid

    for meaning in meanings:
        if meaning.未知対象:
            sid = add_coord(f"lang-class:unknown:{added}", "目的.未知始点", meaning.要求型 or "選択肢", 値状態.未観測)
            oid = add_coord(f"lang-class:target:{added}", "対象.分類先", meaning.分類先, 値状態.確定)
            add_coord(f"lang-class:missing:{added}", "目的.不足位置", "始点", 値状態.確定)
            if meaning.要求型:
                add_coord(f"lang-class:type:{added}", "目的.要求型", meaning.要求型, 値状態.確定)
            state = 値状態.未観測
            conditions = (f"検索述語={meaning.検索述語}", "不足位置=始点", f"英語分類射影={_VERSION}")
        else:
            sid = add_coord(f"lang-class:start:{added}", "対象.実体", meaning.対象, 値状態.確定)
            oid = add_coord(f"lang-class:target:{added}", "対象.分類先", meaning.分類先, 値状態.確定)
            state = 値状態.確定
            conditions = (f"検索述語={meaning.検索述語}", f"英語分類射影={_VERSION}")

        rid = f"lang-class:relation:{added}"
        serial = 1
        while rid in existing_relation_ids:
            rid = f"lang-class:relation:{added}:{serial}"
            serial += 1
        existing_relation_ids.add(rid)
        relations.append(HDS関係(rid, (sid,), (oid,), "分類", 条件=conditions, 値状態=state, 由来="共有言語基底P", 暫定性="EXPLICIT_CLASSIFICATION"))
        added += 1

    return replace(ir, 座標=tuple(coords), 関係=tuple(relations)) if added else ir


__all__ = ["HDS英語分類射影"]

from __future__ import annotations

from dataclasses import replace

from .hds_ir import HDSIR, HDS座標, HDS関係, 値状態
from .言語基底_英語_関係節 import 英語関係節意味抽出


_VERSION = "v0.8-clean"
_RELATIVE = {"which", "who"}


def _norm(value: object) -> str:
    return " ".join(str(value).casefold().split()).strip(" ,;:。！？?.")


def _relative_false_positive(relation: HDS関係, coords: dict[str, HDS座標]) -> bool:
    if str(relation.由来) not in {"公開HDS Compiler", "共有言語基底P"}:
        return False
    endpoints = [coords[cid] for cid in (*relation.始点, *relation.終点) if cid in coords]
    return any(_norm(coord.内容) in _RELATIVE for coord in endpoints)


def HDS英語関係節射影(ir: HDSIR) -> HDSIR:
    """非制限関係節の明示先行詞だけを解決し、関係代名詞を意味端点から除く。

    `A, which inhibits B, ...` のwhichは局所文法上Aへ戻せるため解決する。
    it/this/that/they等の自由照応は推測しない。
    """
    language = str(getattr(ir, "入力言語", "") or "").casefold()
    if not language.startswith("en"):
        return ir

    meanings = 英語関係節意味抽出(str(ir.正規化文 or ir.原文))
    if not meanings:
        return ir

    coords = list(ir.座標)
    coord_map = {coord.座標ID: coord for coord in coords}
    original_relations = list(ir.関係)
    relations = [relation for relation in original_relations if not _relative_false_positive(relation, coord_map)]
    removed = len(original_relations) - len(relations)
    existing_ids = {coord.座標ID for coord in coords}
    existing_relation_ids = {relation.関係ID for relation in relations}
    signatures: set[tuple[str, str, str]] = set()

    for relation in relations:
        for sid in relation.始点:
            for oid in relation.終点:
                if sid in coord_map and oid in coord_map:
                    signatures.add((str(relation.種別), _norm(coord_map[sid].内容), _norm(coord_map[oid].内容)))

    added = 0

    def add_coord(base: str, kind: str, content: str) -> str:
        cid = base
        serial = 1
        while cid in existing_ids:
            cid = f"{base}:{serial}"
            serial += 1
        existing_ids.add(cid)
        coords.append(HDS座標(cid, kind, content, 値状態.確定, 由来="共有言語基底P", 暫定性="EXPLICIT_RELATIVE_CLAUSE_COREFERENCE"))
        return cid

    for meaning in meanings:
        start, end = (meaning.相手端点, meaning.先行詞) if meaning.受動 else (meaning.先行詞, meaning.相手端点)
        signature = (meaning.種別, _norm(start), _norm(end))
        if signature in signatures:
            continue
        sid = add_coord(f"lang-coref:start:{added}", "対象.始点", start)
        oid = add_coord(f"lang-coref:end:{added}", "対象.終点", end)
        rid = f"lang-coref:relation:{added}"
        serial = 1
        while rid in existing_relation_ids:
            rid = f"lang-coref:relation:{added}:{serial}"
            serial += 1
        existing_relation_ids.add(rid)
        relations.append(
            HDS関係(
                rid,
                (sid,),
                (oid,),
                meaning.種別,
                条件=(
                    f"検索述語={meaning.検索述語}",
                    f"照応先行詞={meaning.先行詞}",
                    f"関係代名詞={meaning.関係代名詞}",
                    f"英語関係節射影={_VERSION}",
                ),
                値状態=値状態.確定,
                由来="共有言語基底P",
                暫定性="EXPLICIT_RELATIVE_CLAUSE_COREFERENCE",
            )
        )
        signatures.add(signature)
        added += 1

    if not added and not removed:
        return ir
    return replace(ir, 座標=tuple(coords), 関係=tuple(relations))


__all__ = ["HDS英語関係節射影"]

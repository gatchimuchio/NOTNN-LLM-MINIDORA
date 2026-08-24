from __future__ import annotations

from dataclasses import replace
import re

from .hds_ir import HDSIR, HDS座標, HDS関係, 値状態
from .言語基底_英語 import 英語基本形


_VERSION = "v0.12-clean"
_ORIGINS = {"公開HDS Compiler", "共有言語基底P"}
_LONG_AUX = re.compile(r"^(?P<base>.+?)\s+(?P<aux>has\s+been|have\s+been|had\s+been)$", re.I)
_SHORT_AUX = re.compile(r"^(?P<base>.+?)\s+(?P<aux>is|are|was|were|has|have|had|do|does|did)$", re.I)
_BE = {"is", "are", "was", "were"}
_HAVE = {"has", "have", "had"}
_DO = {"do", "does", "did"}


def _norm(value: object) -> str:
    return " ".join(str(value).split()).strip(" ,;:()[]")


def _条件値(relation: HDS関係, key: str) -> str:
    prefix = key + "="
    for raw in relation.条件:
        value = str(raw)
        if value.startswith(prefix):
            return value[len(prefix):].strip()
    return ""


def _補助語(subject: str) -> tuple[str, str] | None:
    for pattern in (_LONG_AUX, _SHORT_AUX):
        match = pattern.fullmatch(_norm(subject))
        if match:
            base = _norm(match.group("base"))
            aux = _norm(match.group("aux")).casefold()
            if base:
                return base, aux
    return None


def _predicate_head(relation: HDS関係) -> str:
    predicate = _条件値(relation, "検索述語")
    return predicate.casefold().split()[0] if predicate else ""


def _変換種別(aux: str, predicate_head: str) -> tuple[str, tuple[str, ...]]:
    """return (action, extra_conditions). actionはkeep/replace/drop。"""
    if not predicate_head:
        return "keep", ()

    if aux in {"has been", "have been", "had been"}:
        if predicate_head.endswith("ing"):
            tense = "過去" if aux.startswith("had") else "現在"
            return "replace", ("相=完了進行", f"時制={tense}")
        # 完了受動はactive表層として確定しない。専用passive規則がある場合はそちらを残す。
        return "drop", ()

    if aux in _BE:
        if predicate_head.endswith("ing"):
            tense = "過去" if aux in {"was", "were"} else "現在"
            return "replace", ("相=進行", f"時制={tense}")
        # be + 過去分詞/形容詞をactive関係へ誤射影しない。
        return "drop", ()

    if aux in _HAVE:
        lemma = 英語基本形(predicate_head)
        if lemma != predicate_head or predicate_head.endswith(("ed", "en")):
            tense = "過去" if aux == "had" else "現在"
            return "replace", ("相=完了", f"時制={tense}")
        return "drop", ()

    if aux in _DO:
        tense = "過去" if aux == "did" else "現在"
        return "replace", ("強調=do", f"時制={tense}")

    return "keep", ()


def HDS英語補助語端点正規化(ir: HDSIR) -> HDSIR:
    """関係始点へ吸収された時制・相の補助語を、実体端点と分離する。

    `A is generating B` を `A is --生成→ B` とせず、Aを始点として相=進行を条件へ残す。
    modal/否定はこの層の責務外とし、意味を勝手にactualへ変換しない。
    """
    language = str(getattr(ir, "入力言語", "") or "").casefold()
    if not language.startswith("en"):
        return ir

    coords = list(ir.座標)
    coord_map = {coord.座標ID: coord for coord in coords}
    existing_ids = {coord.座標ID for coord in coords}
    possible_orphans: set[str] = set()
    staged: list[HDS関係] = []
    changed = False
    serial = 0

    def add_start(content: str, origin: str) -> str:
        nonlocal serial
        for coord in coords:
            if str(coord.種別) == "対象.始点" and _norm(coord.内容).casefold() == content.casefold() and coord.値状態 == 値状態.確定:
                return coord.座標ID
        cid = f"lang-aux:start:{serial}"
        serial += 1
        while cid in existing_ids:
            cid = f"lang-aux:start:{serial}"
            serial += 1
        existing_ids.add(cid)
        coords.append(HDS座標(cid, "対象.始点", content, 値状態.確定, 由来=origin, 暫定性="AUXILIARY_ENDPOINT_NORMALIZATION"))
        coord_map[cid] = coords[-1]
        return cid

    for relation in ir.関係:
        if relation.値状態 != 値状態.確定 or str(relation.由来) not in _ORIGINS or len(relation.始点) != 1:
            staged.append(relation)
            continue
        sid = relation.始点[0]
        start = coord_map.get(sid)
        if start is None or start.値状態 != 値状態.確定:
            staged.append(relation)
            continue
        parsed = _補助語(str(start.内容))
        if parsed is None:
            staged.append(relation)
            continue

        base, aux = parsed
        action, extra = _変換種別(aux, _predicate_head(relation))
        if action == "keep":
            staged.append(relation)
            continue

        changed = True
        possible_orphans.add(sid)
        if action == "drop":
            continue

        new_sid = add_start(base, str(start.由来) or str(relation.由来))
        conditions = tuple(dict.fromkeys((*relation.条件, *extra, f"補助語端点正規化={_VERSION}", f"補助語表層={aux}")))
        staged.append(replace(relation, 始点=(new_sid,), 条件=conditions))

    if not changed:
        return ir

    # 同じ意味辺を二重保持しない。
    deduped: list[HDS関係] = []
    signatures: set[tuple[str, tuple[str, ...], tuple[str, ...], 値状態]] = set()
    for relation in staged:
        starts = tuple(_norm(coord_map[cid].内容).casefold() for cid in relation.始点 if cid in coord_map)
        ends = tuple(_norm(coord_map[cid].内容).casefold() for cid in relation.終点 if cid in coord_map)
        signature = (str(relation.種別), starts, ends, relation.値状態)
        if signature in signatures:
            continue
        signatures.add(signature)
        deduped.append(relation)

    referenced = {cid for relation in deduped for cid in (*relation.始点, *relation.終点)}
    cleaned_coords = tuple(
        coord for coord in coords
        if not (
            coord.座標ID in possible_orphans
            and coord.座標ID not in referenced
            and str(coord.種別) == "対象.始点"
            and str(coord.由来) in _ORIGINS
        )
    )
    return replace(ir, 座標=cleaned_coords, 関係=tuple(deduped))


__all__ = ["HDS英語補助語端点正規化"]

from __future__ import annotations

from dataclasses import replace
import re

from .hds_ir import HDSIR, HDS座標, HDS関係, 値状態
from .semantic_tokens import 意味語
from .言語基底 import 言語基底P, 標準言語基底P
from .言語基底_英日意味強化 import 英語明示述語関係抽出


_BLOCKING = {値状態.未確定, 値状態.未観測, 値状態.矛盾, 値状態.留保}
_QUESTION_START = re.compile(r"^\s*(?:which|what|who|where|when|why|how)\b", re.I)
_DERIVED_ACTIVE_FALSE = re.compile(r"\b(?:is|are|was|were)\s*$", re.I)


def _norm(value: object) -> str:
    return " ".join(str(value).split()).strip(" ,;:。！？?.").casefold()


def _条件値(relation: HDS関係, key: str) -> str:
    prefix = key + "="
    for raw in relation.条件:
        value = str(raw)
        if value.startswith(prefix):
            return value[len(prefix):].strip()
    return ""


def _関係署名(kind: str, subject: object, object_: object, predicate: str = "", conditions: tuple[str, ...] = ()) -> tuple[object, ...]:
    condition_map: dict[str, str] = {}
    for raw in conditions:
        key, sep, payload = str(raw).partition("=")
        if sep:
            condition_map[key.strip()] = payload.strip()
    polarity = condition_map.get("極性", "肯定") or "肯定"
    scope = tuple(
        (key, condition_map[key])
        for key in ("様相", "量化", "条件scope", "scope", "条件作用")
        if condition_map.get(key)
    )
    predicate_key = _norm(predicate) if str(kind) == "開放述語" else ""
    return (str(kind), _norm(subject), _norm(object_), predicate_key, polarity, scope)


def _existing_signatures(ir: HDSIR) -> set[tuple[object, ...]]:
    coords = ir.座標辞書()
    out: set[tuple[object, ...]] = set()
    for relation in ir.関係:
        if relation.値状態 in _BLOCKING:
            continue
        starts = [coords[cid] for cid in relation.始点 if cid in coords and coords[cid].値状態 not in _BLOCKING]
        ends = [coords[cid] for cid in relation.終点 if cid in coords and coords[cid].値状態 not in _BLOCKING]
        for start in starts:
            for end in ends:
                predicate = _条件値(relation, "検索述語")
                out.add(_関係署名(str(relation.種別), start.内容, end.内容, predicate, tuple(str(x) for x in relation.条件)))
    return out


def HDS英語基底関係射影(ir: HDSIR, 言語基底: 言語基底P | None = None) -> HDSIR:
    """英語に表層明示された関係を、有限関係族＋開放述語としてHDSへ補完する。"""
    language = str(getattr(ir, "入力言語", "") or "").casefold()
    if not language.startswith("en"):
        return ir

    text = str(ir.正規化文 or ir.原文)
    if "?" in text or _QUESTION_START.search(text):
        return ir

    language_p = 言語基底 or 標準言語基底P
    syntaxes = language_p.英語関係構文()
    coords = list(ir.座標)
    relations = list(ir.関係)
    existing_ids = {coord.座標ID for coord in coords}
    existing_relation_ids = {relation.関係ID for relation in relations}
    signatures = _existing_signatures(ir)
    added = 0

    def add_coord(kind: str, content: str, suffix: str) -> str:
        base = f"language:{suffix}:{added}"
        cid = base
        serial = 1
        while cid in existing_ids:
            cid = f"{base}:{serial}"
            serial += 1
        existing_ids.add(cid)
        coords.append(HDS座標(cid, kind, content, 値状態.確定, 由来="共有言語基底P"))
        return cid

    def add_relation(kind: str, subject: str, object_: str, predicate: str, *, conditions: tuple[str, ...] = ()) -> None:
        nonlocal added
        subject = " ".join(subject.split()).strip(" ,;:()[]")
        object_ = " ".join(object_.split()).strip(" ,;:()[]")
        predicate = " ".join(predicate.split()).strip()
        if not subject or not object_ or not predicate:
            return
        if not 意味語(subject) or not 意味語(object_):
            return
        if _norm(subject) == _norm(object_):
            return
        signature = _関係署名(kind, subject, object_, predicate, conditions)
        if signature in signatures:
            return
        sid = add_coord("対象.始点", subject, "subject")
        oid = add_coord("対象.終点", object_, "object")
        rid_base = f"language-rel:{added}"
        rid = rid_base
        serial = 1
        while rid in existing_relation_ids:
            rid = f"{rid_base}:{serial}"
            serial += 1
        existing_relation_ids.add(rid)
        relation_conditions = [f"検索述語={predicate}", "由来=共有言語基底P"]
        relation_conditions.extend(conditions)
        relations.append(
            HDS関係(
                rid,
                (sid,),
                (oid,),
                kind,
                条件=tuple(dict.fromkeys(relation_conditions)),
                値状態=値状態.確定,
                由来="共有言語基底P",
            )
        )
        signatures.add(signature)
        added += 1

    for syntax in syntaxes:
        for match in syntax.正規表現.finditer(text):
            subject = " ".join(match.group("s").split()).strip(" ,;:()[]")
            object_ = " ".join(match.group("o").split()).strip(" ,;:()[]")
            predicate = " ".join(match.group("v").split()).strip()
            if not subject or not object_ or not predicate:
                continue
            if not syntax.反転 and object_.casefold().startswith("by "):
                continue
            if predicate.casefold() == "derived from" and _DERIVED_ACTIVE_FALSE.search(subject):
                continue
            if syntax.反転:
                subject, object_ = object_, subject
            add_relation(syntax.種別, subject, object_, predicate)

    for item in 英語明示述語関係抽出(text):
        # 既存17関係族は上の共有言語基底P構文が正本。第二passは有限語彙外だけを補完する。
        if item.種別 != "開放述語":
            continue
        conditions = []
        if item.極性 == "否定":
            conditions.append("極性=否定")
        conditions.extend(f"{key}={value}" for key, value in item.修飾)
        add_relation(item.種別, item.始点, item.終点, item.検索述語, conditions=tuple(conditions))

    if not added:
        return ir
    return replace(ir, 座標=tuple(coords), 関係=tuple(relations))


__all__ = ["HDS英語基底関係射影"]

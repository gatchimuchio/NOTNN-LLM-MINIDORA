from __future__ import annotations

from dataclasses import replace
import re

from .hds_ir import HDSIR, HDS座標, HDS関係, 値状態
from .semantic_tokens import 意味語
from .言語基底 import 言語基底P, 標準言語基底P


_BLOCKING = {値状態.未確定, 値状態.未観測, 値状態.矛盾, 値状態.留保}
_QUESTION_START = re.compile(r"^\s*(?:which|what|who|where|when|why|how)\b", re.I)
_NEGATIVE_TAIL = re.compile(
    r"\b(?:(?:do|does|did|can|could|may|might|must|will|would|should)\s+not|"
    r"don't|doesn't|didn't|can't|cannot|couldn't|won't|wouldn't|shouldn't|mustn't)\s*$",
    re.I,
)


def _norm(value: object) -> str:
    return " ".join(str(value).split()).strip(" ,;:。！？?.").casefold()


def _条件値(relation: HDS関係, key: str) -> str:
    prefix = key + "="
    for raw in relation.条件:
        value = str(raw)
        if value.startswith(prefix):
            return value[len(prefix):].strip()
    return ""


def _極性(relation: HDS関係) -> str:
    return _条件値(relation, "極性") or "肯定"


def _signatures(coords: tuple[HDS座標, ...] | list[HDS座標], relations: tuple[HDS関係, ...] | list[HDS関係]) -> set[tuple[str, str, str, str]]:
    coord_map = {coord.座標ID: coord for coord in coords}
    out: set[tuple[str, str, str, str]] = set()
    for relation in relations:
        if relation.値状態 in _BLOCKING:
            continue
        starts = [coord_map[cid] for cid in relation.始点 if cid in coord_map and coord_map[cid].値状態 not in _BLOCKING]
        ends = [coord_map[cid] for cid in relation.終点 if cid in coord_map and coord_map[cid].値状態 not in _BLOCKING]
        for start in starts:
            for end in ends:
                out.add((str(relation.種別), _極性(relation), _norm(start.内容), _norm(end.内容)))
    return out


def _legacy_negative_false_positive(relation: HDS関係, coords: dict[str, HDS座標]) -> bool:
    if str(relation.由来) != "公開HDS Compiler" or _条件値(relation, "極性"):
        return False
    starts = [coords[cid] for cid in relation.始点 if cid in coords]
    return any(_NEGATIVE_TAIL.search(str(start.内容)) for start in starts)


def _検索述語(surface: str, language_p: 言語基底P) -> str:
    phrase = " ".join(str(surface).split()).strip().casefold()
    if not phrase:
        return ""
    parts = phrase.split()
    head = language_p.英語基本形(parts[0])
    if len(parts) > 1 and parts[-1] in {"to", "in", "on", "with", "against", "from"}:
        return f"{head} {parts[-1]}"
    return head


def HDS英語基底関係射影(ir: HDSIR, 言語基底: 言語基底P | None = None) -> HDSIR:
    """共有英語基底Pの明示構文だけを、極性付きHDS関係へ補完する。

    名詞共起・近接・分野知識から関係を推定しない。現行基礎Compilerが取りこぼしやすい
    過去形・進行形・受動態・否定態など、言語形だけが異なる明示関係を対象とする。
    否定補助語を主語末尾へ取り込んだ旧Compilerの肯定偽陽性もここで除去する。
    疑問文は未知端点処理を基礎Compiler/英日意味射影へ委ねる。
    """
    language = str(getattr(ir, "入力言語", "") or "").casefold()
    if not language.startswith("en"):
        return ir

    text = str(ir.正規化文 or ir.原文)
    if "?" in text or _QUESTION_START.search(text):
        return ir

    language_p = 言語基底 or 標準言語基底P
    syntaxes = language_p.英語関係構文()

    coords = list(ir.座標)
    coord_map = {coord.座標ID: coord for coord in coords}
    original_relations = list(ir.関係)
    relations = [relation for relation in original_relations if not _legacy_negative_false_positive(relation, coord_map)]
    removed = len(original_relations) - len(relations)
    existing_ids = {coord.座標ID for coord in coords}
    existing_relation_ids = {relation.関係ID for relation in relations}
    signatures = _signatures(coords, relations)
    added = 0

    def add_coord(kind: str, content: str, suffix: str) -> str:
        base = f"language:{suffix}:{added}"
        cid = base
        serial = 1
        while cid in existing_ids:
            cid = f"{base}:{serial}"
            serial += 1
        existing_ids.add(cid)
        coords.append(
            HDS座標(
                cid,
                kind,
                content,
                値状態.確定,
                由来="共有言語基底P",
            )
        )
        return cid

    for syntax in syntaxes:
        for match in syntax.正規表現.finditer(text):
            subject = " ".join(match.group("s").split()).strip(" ,;:()[]")
            object_ = " ".join(match.group("o").split()).strip(" ,;:()[]")
            predicate = " ".join(match.group("v").split()).strip()
            if not subject or not object_ or not predicate:
                continue

            # 否定文を肯定active側が `A does not` -> `inhibit` と誤分解しない。
            if syntax.極性 == "肯定" and _NEGATIVE_TAIL.search(subject):
                continue
            if not syntax.反転 and object_.casefold().startswith("by "):
                continue
            if syntax.反転:
                subject, object_ = object_, subject

            if not 意味語(subject) or not 意味語(object_):
                continue
            if _norm(subject) == _norm(object_):
                continue

            signature = (syntax.種別, syntax.極性, _norm(subject), _norm(object_))
            if signature in signatures:
                continue

            sid = add_coord("対象.始点", subject, "subject")
            oid = add_coord("対象.終点", object_, "object")
            rid_base = f"language-rel:{added}"
            rid = rid_base
            serial = 1
            while rid in existing_relation_ids:
                rid = f"{rid_base}:{serial}"
                serial += 1
            existing_relation_ids.add(rid)
            search_predicate = _検索述語(predicate, language_p)
            relations.append(
                HDS関係(
                    rid,
                    (sid,),
                    (oid,),
                    syntax.種別,
                    条件=(
                        f"検索述語={search_predicate or predicate}",
                        f"極性={syntax.極性}",
                        "由来=共有言語基底P",
                    ),
                    値状態=値状態.確定,
                    由来="共有言語基底P",
                )
            )
            signatures.add(signature)
            added += 1

    if not added and not removed:
        return ir
    return replace(ir, 座標=tuple(coords), 関係=tuple(relations))


__all__ = ["HDS英語基底関係射影"]

from __future__ import annotations

from dataclasses import replace
import re
import unicodedata

from .hds_ir import HDSIR, HDS関係


_MODAL = {
    "can": "可能",
    "could": "可能",
    "may": "可能",
    "might": "可能",
    "would": "可能",
    "must": "必要",
    "should": "必要",
}


def _norm(value: object) -> str:
    return " ".join(unicodedata.normalize("NFKC", str(value)).split()).strip(" ,;:。！？?.")


def _条件値(relation: HDS関係, key: str) -> str:
    prefix = key + "="
    for raw in relation.条件:
        value = str(raw)
        if value.startswith(prefix):
            return value[len(prefix):].strip()
    return ""


def _条件追加(relation: HDS関係, *items: str) -> HDS関係:
    conditions = list(relation.条件)
    for item in items:
        if item and item not in conditions:
            conditions.append(item)
    return replace(relation, 条件=tuple(conditions))


def _phrase_pattern(value: str) -> str:
    words = [re.escape(word) for word in _norm(value).split() if word]
    return r"\s+".join(words)


def _predicate_pattern(value: str) -> str:
    words = _norm(value).casefold().split()
    if not words:
        return ""
    head = re.escape(words[0])
    # Compilerが正規化済みの検索述語を持つため、語形差は最小限だけ許容する。
    head = rf"{head}(?:s|ed|ing)?"
    if len(words) == 1:
        return head
    return head + r"\s+" + r"\s+".join(re.escape(word) for word in words[1:])


def _relation_scope(text: str, relation: HDS関係, coords: dict[str, object]) -> tuple[str, ...]:
    predicate = _条件値(relation, "検索述語")
    if not predicate:
        return ()
    starts = [_norm(getattr(coords[cid], "内容", "")) for cid in relation.始点 if cid in coords]
    ends = [_norm(getattr(coords[cid], "内容", "")) for cid in relation.終点 if cid in coords]
    if len(starts) != 1 or len(ends) != 1 or not starts[0] or not ends[0]:
        return ()

    start = _phrase_pattern(starts[0])
    end = _phrase_pattern(ends[0])
    pred = _predicate_pattern(predicate)
    if not start or not end or not pred:
        return ()

    out: list[str] = []

    # semantic direction: start -> end
    active_neg = re.compile(rf"\b{start}\s+(?:does|do|did)\s+not\s+{pred}\s+{end}\b", re.I)
    active_modal = re.compile(rf"\b{start}\s+(?P<m>can|could|may|might|would|must|should)\s+(?:not\s+)?{pred}\s+{end}\b", re.I)
    active_modal_neg = re.compile(rf"\b{start}\s+(?P<m>can|could|may|might|would|must|should)\s+not\s+{pred}\s+{end}\b", re.I)

    # passive surface reverses semantic endpoints: end is grammatical subject, start follows by.
    passive_neg = re.compile(rf"\b{end}\s+(?:is|are|was|were)\s+not\s+{pred}(?:ed|d)?\s+by\s+{start}\b", re.I)
    passive_modal = re.compile(rf"\b{end}\s+(?P<m>can|could|may|might|would|must|should)\s+(?:not\s+)?be\s+{pred}(?:ed|d)?\s+by\s+{start}\b", re.I)
    passive_modal_neg = re.compile(rf"\b{end}\s+(?P<m>can|could|may|might|would|must|should)\s+not\s+be\s+{pred}(?:ed|d)?\s+by\s+{start}\b", re.I)

    if active_neg.search(text) or passive_neg.search(text) or active_modal_neg.search(text) or passive_modal_neg.search(text):
        out.append("極性=否定")

    modal_match = active_modal.search(text) or passive_modal.search(text)
    if modal_match:
        modal_surface = modal_match.group("m").casefold()
        modal = _MODAL.get(modal_surface)
        if modal:
            out.extend((f"様相={modal}", f"様相表層={modal_surface}"))

    # 条件句は、同じ文中で関係節の前に明示された場合だけscopeへ結ぶ。
    # 自由な談話条件や後続文への伝播はしない。
    relation_surface = re.compile(
        rf"\b(?:{start}\b.*?{pred}\b.*?{end}|{end}\b.*?{pred}\b.*?by\s+{start})",
        re.I,
    )
    rel_match = relation_surface.search(text)
    if rel_match:
        prefix = text[: rel_match.start()]
        cond_match = re.search(
            r"(?:^|[.;]\s*)(?P<c>(?:if|when|under|given|assuming)\b[^.;,]{1,180})\s*,\s*$",
            prefix,
            re.I,
        )
        if cond_match:
            out.append("条件scope=" + _norm(cond_match.group("c")))

    return tuple(dict.fromkeys(out))


def HDS英語関係scope射影(ir: HDSIR) -> HDSIR:
    """英語表層の明示scopeを、Compilerが既に確定した関係へ局所結合する。

    Runtimeへ自然言語再解析を持ち込まないためのCompiler責務である。
    新しい世界関係は生成せず、既存relationの条件だけを補う。
    疑問文は質問意味Compilerへ委ね、この層では宣言文だけを対象とする。
    """
    if not str(getattr(ir, "入力言語", "")).casefold().startswith("en"):
        return ir
    text = _norm(ir.正規化文 or ir.原文)
    if not text or "?" in str(ir.正規化文 or ir.原文):
        return ir

    coords = ir.座標辞書()
    changed = False
    relations: list[HDS関係] = []
    for relation in ir.関係:
        additions = _relation_scope(text, relation, coords)
        if additions:
            updated = _条件追加(relation, *additions, "scope結合=Compiler")
            changed = changed or updated != relation
            relations.append(updated)
        else:
            relations.append(relation)
    if not changed:
        return ir
    return replace(ir, 関係=tuple(relations))


__all__ = ["HDS英語関係scope射影"]

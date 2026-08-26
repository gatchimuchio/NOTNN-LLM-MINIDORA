from __future__ import annotations

from dataclasses import dataclass, replace
import re
import unicodedata

from .言語基底_英日意味 import (
    英日意味制御,
    英日関係質問,
    英日意味フレーム,
    英日意味フレーム抽出 as _旧抽出,
)
from .言語基底_英語 import 英語基本形, 英語関係概念


@dataclass(frozen=True, slots=True)
class 英語明示述語関係:
    種別: str
    始点: str
    終点: str
    検索述語: str
    極性: str = "肯定"
    修飾: tuple[tuple[str, str], ...] = ()


_末尾疑問符 = re.compile(r"[?？]+$")
_文分割 = re.compile(r"(?<=[?!.。？！])\s+|\n+")
_語 = re.compile(r"[A-Za-z][A-Za-z0-9_-]*")
_補助語 = frozenset({
    "is", "are", "was", "were", "be", "been", "being", "do", "does", "did",
    "can", "could", "may", "might", "must", "should", "would", "will", "has", "have", "had",
})
_機能語 = frozenset({
    "which", "what", "who", "where", "when", "why", "how", "of", "the", "following",
    "most", "least", "likely", "unlikely", "best", "correctly", "accurately", "directly",
    "and", "or", "nor",
})
_前置詞 = frozenset({"to", "in", "on", "with", "against", "from", "of", "for", "by", "as", "into", "onto", "through"})
_判定反転 = re.compile(r"\b(?:least\s+likely|unlikely|except|incorrect|false|inaccurate|invalid|inconsistent|unsupported|not\s+true|not\s+correct)\b", re.I)
_否定 = re.compile(r"\b(?:never|not|no|without|cannot|can't|does\s+not|do\s+not|did\s+not|is\s+not|are\s+not|was\s+not|were\s+not)\b", re.I)
_先頭条件 = re.compile(r"^(?P<c>(?:(?:if|when|under|given|assuming|unless)\b|in\s+the\s+(?:presence|absence)\s+of\b)[^?]{1,220}?)[,;]\s*(?P<q>.+)$", re.I)
_末尾条件 = re.compile(r"\b(?P<c>(?:when|if|unless|under|given|assuming)\b.+)$", re.I)
_命題選択 = re.compile(
    r"^(?:which|what)(?:\s+of\s+the\s+following)?(?:\s+(?:statement|statements|claim|claims|description|descriptions|explanation|explanations))?\s+"
    r"(?:(?:is|are)\s+)?(?:(?:most|least)\s+likely\s+)?"
    r"(?P<judge>correct|incorrect|true|false|accurate|inaccurate|valid|invalid|consistent|inconsistent|supported|unsupported)"
    r"(?:\s+(?:regarding|about|for|with\s+respect\s+to)\s+(?P<topic>.+))?$", re.I,
)
_説明選択 = re.compile(
    r"^(?:which|what)(?:\s+of\s+the\s+following)?(?:\s+(?:statement|statements|option|options|choice|choices|explanation|explanations))?\s+"
    r"(?:(?:best|most\s+directly|most\s+accurately)\s+)?(?P<v>describes?|explains?|accounts?\s+for|characterizes?|represents?)\s+(?P<o>.+)$", re.I,
)
_数量 = re.compile(r"^how\s+(?:many|much)\s+(?P<o>.+)$", re.I)
_一般同定 = re.compile(r"^(?:what|which)\s+(?:(?:would|could|may|might|should|can|will|must)\s+)?(?:be\s+)?(?P<o>.+)$", re.I)
_様相コピュラ同定 = re.compile(
    r"^(?:what|which)\s+(?:would|could|may|might|should|can|will|must)\s+be\b", re.I,
)
_協調主語 = re.compile(r"\b(?:and|or|nor)\b", re.I)
_協調接続終端 = re.compile(r"\b(?:and|or|nor)\s*$", re.I)
_末尾補助語 = re.compile(
    r"\s+(?:do|does|did|is|are|was|were|be|been|being|can|could|may|might|must|should|would|will|has|have|had)\s*$",
    re.I,
)
_疑問語 = re.compile(r"\b(?:which|what|who|where|when|why|how)\b", re.I)
_受動 = re.compile(
    r"^(?P<s>.+?)\s+(?:is|are|was|were|be|been|being|has\s+been|have\s+been|had\s+been)\s+"
    r"(?P<v>[A-Za-z][A-Za-z-]*(?:\s+(?:to|in|on|with|against|from|of|for))?)\s+by\s+(?P<o>.+)$", re.I,
)


def _正規化(text: object) -> str:
    return " ".join(unicodedata.normalize("NFKC", str(text)).split()).strip()


def _端点(text: object) -> str:
    return _末尾疑問符.sub("", _正規化(text)).strip(" ,;:()[]")


def _開放主語(text: object) -> str:
    """open述語探索が主語側へ吸収した補助語だけを除く。世界知識は足さない。"""
    return _末尾補助語.sub("", _端点(text)).strip()


def _焦点(text: str) -> str:
    raw = _正規化(text)
    parts = [p.strip() for p in _文分割.split(raw) if p.strip()]
    for part in reversed(parts):
        if "?" in part or "？" in part:
            return part
    return parts[-1] if parts else raw


def _動詞基本形(surface: str) -> str:
    phrase = _正規化(surface).casefold()
    parts = phrase.split()
    if not parts:
        return ""
    word = parts[0]
    known = 英語基本形(word)
    if known != word:
        head = known
    elif len(word) > 4 and word.endswith("ies"):
        head = word[:-3] + "y"
    elif len(word) > 4 and word.endswith(("izes", "ises")):
        head = word[:-1]
    elif len(word) > 4 and word.endswith(("ches", "shes", "xes", "sses", "oes")):
        head = word[:-2]
    elif len(word) > 3 and word.endswith("s") and not word.endswith(("ss", "is", "us")):
        head = word[:-1]
    elif len(word) > 5 and word.endswith(("ized", "ised")):
        head = word[:-1]
    elif len(word) > 4 and word.endswith("ied"):
        head = word[:-3] + "y"
    elif len(word) > 4 and word.endswith("ed"):
        head = word[:-2]
        if head in {"stabiliz", "activat", "regulat", "generat", "characteriz", "represent", "associat"}:
            head += "e"
    elif len(word) > 5 and word.endswith("ing"):
        head = word[:-3]
        if head.endswith(("iz", "at")):
            head += "e"
    else:
        head = word
    return " ".join((head, *parts[1:]))


def _関係種別(predicate: str) -> tuple[str, str]:
    normalized = _動詞基本形(predicate)
    head = normalized.split()[0] if normalized else ""
    kind = 英語関係概念(head)
    return (kind or "開放述語", normalized)


def _修飾(text: str, conditions: tuple[str, ...] = ()) -> tuple[tuple[str, str], ...]:
    out: list[tuple[str, str]] = []
    if _否定.search(text):
        out.append(("極性", "否定"))
    low = text.casefold()
    if re.search(r"\b(?:can|could|may|might|would|should)\b", low):
        out.append(("様相", "可能"))
    if re.search(r"\b(?:must|necessary)\b", low):
        out.append(("様相", "必要"))
    if re.search(r"\b(?:all|each|every)\b", low):
        out.append(("量化", "全称"))
    for condition in conditions:
        if condition:
            out.append(("条件scope", condition))
    return tuple(dict.fromkeys(out))


def _条件分離(text: str) -> tuple[str, tuple[str, ...]]:
    raw = _端点(text)
    first = _先頭条件.fullmatch(raw)
    if first:
        return _正規化(first.group("q")), (_正規化(first.group("c")),)
    tail = _末尾条件.search(raw)
    if tail and tail.start() > 0:
        return raw[:tail.start()].strip(" ,;:"), (_正規化(tail.group("c")),)
    return raw, ()


def _反転(text: str) -> bool:
    return bool(_判定反転.search(text))


def _predicate_from_tokens(tokens: list[str], start: int) -> tuple[str, list[str]] | None:
    for index in range(start, len(tokens)):
        token = tokens[index].casefold().strip("?,.;:")
        if token in _補助語 or token in _機能語 or token == "never":
            continue
        if 英語関係概念(token) is not None or re.fullmatch(r"[a-z][a-z-]{2,}", token):
            predicate = [tokens[index]]
            if index + 1 < len(tokens) and tokens[index + 1].casefold().strip("?,.;:") in _前置詞:
                predicate.append(tokens[index + 1])
                return " ".join(predicate), tokens[index + 2:]
            return " ".join(predicate), tokens[index + 1:]
    return None


def _generic_relation_question(raw: str, conditions: tuple[str, ...]) -> 英日関係質問 | None:
    body = _端点(raw)
    tokens = body.split()
    if not tokens or tokens[0].casefold() not in {"which", "what", "who"}:
        return None
    if len(tokens) == 1:
        return None

    aux_index = next((i for i, t in enumerate(tokens) if t.casefold() in {"does", "do", "did"}), None)
    if aux_index is not None and aux_index >= 1:
        requested = " ".join(tokens[1:aux_index]).replace("of the following", "").strip() or "選択肢"
        predicate_info = _predicate_from_tokens(tokens, aux_index + 1)
        if predicate_info:
            predicate_surface, tail = predicate_info
            relation_index = body.casefold().rfind(predicate_surface.casefold())
            subject = body[len(" ".join(tokens[:aux_index + 1])):relation_index].strip() if relation_index >= 0 else " ".join(tokens[aux_index + 1:-1])
            kind, predicate = _関係種別(predicate_surface)
            return 英日関係質問(kind, "終点", requested, _端点(subject), predicate, _反転(body), False, _修飾(body, conditions))

    prefix = 1
    if len(tokens) >= 4 and [t.casefold() for t in tokens[1:4]] == ["of", "the", "following"]:
        requested = "選択肢"
        prefix = 4
    else:
        requested_tokens: list[str] = []
        while prefix < len(tokens):
            low = tokens[prefix].casefold().strip("?,.;:")
            if low in _補助語 or low in {"never", "not", "most", "least", "likely", "unlikely"}:
                break
            if prefix + 1 < len(tokens):
                next_low = tokens[prefix + 1].casefold().strip("?,.;:")
                if 英語関係概念(next_low) is not None or next_low.endswith(("s", "ed", "ing")):
                    requested_tokens.append(tokens[prefix])
                    prefix += 1
                    break
            requested_tokens.append(tokens[prefix])
            prefix += 1
        requested = " ".join(requested_tokens).strip() or "選択肢"

    predicate_info = _predicate_from_tokens(tokens, prefix)
    if not predicate_info:
        return 英日関係質問("問い適合", "始点", requested, body, "match", _反転(body), False, _修飾(body, conditions))
    predicate_surface, tail = predicate_info
    kind, predicate = _関係種別(predicate_surface)
    known = _端点(" ".join(tail)) or body
    return 英日関係質問(kind, "始点", requested, known, predicate, _反転(body), False, _修飾(body, conditions))


def _fallback_question(focus: str) -> 英日関係質問 | None:
    body, conditions = _条件分離(focus)
    proposition = _命題選択.fullmatch(body)
    if proposition:
        topic = _端点(proposition.group("topic") or "候補命題")
        return 英日関係質問("命題適合", "始点", "選択肢", topic, "proposition_match", _反転(body), False, _修飾(body, conditions))
    explanation = _説明選択.fullmatch(body)
    if explanation:
        predicate = _動詞基本形(explanation.group("v"))
        return 英日関係質問("説明適合", "始点", "選択肢", _端点(explanation.group("o")), predicate, _反転(body), False, _修飾(body, conditions))
    quantity = _数量.fullmatch(body)
    if quantity:
        return 英日関係質問("数量同定", "終点", "数量", _端点(quantity.group("o")), "count", _反転(body), False, _修飾(body, conditions))
    # "What would be ..." 等は内容語をopen述語と誤認する前に同定要求として閉じる。
    if _様相コピュラ同定.match(body):
        identity = _一般同定.fullmatch(body)
        if identity:
            target = _端点(identity.group("o"))
            return 英日関係質問("同定", "終点", "未特定", target, "identify", _反転(body), False, _修飾(body, conditions))
    generic = _generic_relation_question(body, conditions)
    if generic:
        return generic
    identity = _一般同定.fullmatch(body)
    if identity:
        target = _端点(identity.group("o"))
        return 英日関係質問("同定", "終点", "未特定", target, "identify", _反転(body), False, _修飾(body, conditions))

    # 既知構文へ閉じられなくても、質問として明示された意味内容はtopic bagへ捨てない。
    # 世界事実を補わず、質問表層そのものを既知端点にした「問い適合」として保持する。
    content_tokens = [
        token for token in _語.findall(body)
        if token.casefold() not in _機能語 and token.casefold() not in _補助語
    ]
    if ("?" in focus or "？" in focus or _疑問語.search(body)) and content_tokens:
        return 英日関係質問(
            "問い適合", "始点", "選択肢", body, "match", _反転(body), False, _修飾(body, conditions),
        )
    return None


def 英日意味フレーム抽出(text: str) -> 英日意味フレーム:
    focus = _焦点(text)
    proposition = _命題選択.fullmatch(_端点(_条件分離(focus)[0]))
    fallback = _fallback_question(focus)
    if proposition is not None and fallback is not None:
        base = _旧抽出(text)
        canonical = tuple((*base.正本意味, f"関係:{fallback.種別}", f"述語:{fallback.検索述語}", f"不足位置:{fallback.未知位置}"))
        return 英日意味フレーム(tuple(dict.fromkeys(canonical)), base.外部検索語, base.制御, fallback)

    base = _旧抽出(text)
    if base.関係質問 is not None:
        _, conditions = _条件分離(focus)
        modifiers = tuple(dict.fromkeys((*base.関係質問.修飾, *_修飾(focus, conditions))))
        return replace(base, 関係質問=replace(base.関係質問, 修飾=modifiers))
    if fallback is None:
        return base
    canonical = tuple((*base.正本意味, f"関係:{fallback.種別}", f"述語:{fallback.検索述語}", f"不足位置:{fallback.未知位置}"))
    return 英日意味フレーム(tuple(dict.fromkeys(canonical)), base.外部検索語, base.制御, fallback)


def _declaration_conditions(text: str) -> tuple[str, tuple[tuple[str, str], ...]]:
    head, conditions = _条件分離(text)
    return head, _修飾(text, conditions)


def _declaration_one(sentence: str) -> 英語明示述語関係 | None:
    raw = _端点(sentence)
    if not raw or re.match(r"^(?:which|what|who|where|when|why|how)\b", raw, re.I):
        return None
    polarity = "否定" if _否定.search(raw) else "肯定"
    normalized = re.sub(r"\b(?:do|does|did|is|are|was|were|can|could|may|might|must|will|would|should|has|have|had)\s+not\b", lambda m: m.group(0).rsplit(None, 1)[0], raw, flags=re.I)
    passive = _受動.fullmatch(normalized)
    if passive:
        kind, predicate = _関係種別(passive.group("v"))
        obj, mods = _declaration_conditions(passive.group("s"))
        return 英語明示述語関係(kind, _端点(passive.group("o")), obj, predicate, polarity, mods)
    tokens = normalized.split()
    if len(tokens) < 3:
        return None
    predicate_info = _predicate_from_tokens(tokens, 1)
    if predicate_info:
        predicate_surface, tail = predicate_info
        predicate_index = next((i for i, t in enumerate(tokens[1:], 1) if predicate_surface.casefold().startswith(t.casefold().strip("?,.;:"))), None)
        if predicate_index is not None and tail:
            subject_surface = _端点(" ".join(tokens[:predicate_index]))
            subject = _開放主語(subject_surface)
            object_text, mods = _declaration_conditions(" ".join(tail))
            if subject and object_text:
                kind, predicate = _関係種別(predicate_surface)
                if kind == "開放述語" and (
                    _協調接続終端.search(subject_surface)
                    or (_協調主語.search(subject) and _末尾補助語.search(subject_surface))
                ):
                    return None
                return 英語明示述語関係(kind, subject, object_text, predicate, polarity, mods)
    copula = re.match(r"^(?P<s>.+?)\s+(?:is|are|was|were)\s+(?P<o>.+)$", raw, re.I)
    if copula:
        obj, mods = _declaration_conditions(copula.group("o"))
        return 英語明示述語関係("開放述語", _端点(copula.group("s")), obj, "be", polarity, mods)
    return None


def 英語明示述語関係抽出(text: str) -> tuple[英語明示述語関係, ...]:
    raw = _正規化(text)
    out: list[英語明示述語関係] = []
    seen: set[tuple[object, ...]] = set()
    for sentence in _文分割.split(raw):
        relation = _declaration_one(sentence)
        if relation is None:
            continue
        key = (relation.種別, relation.始点.casefold(), relation.終点.casefold(), relation.検索述語, relation.極性, relation.修飾)
        if key not in seen:
            seen.add(key)
            out.append(relation)
    return tuple(out)


__all__ = [
    "英日意味制御", "英日関係質問", "英日意味フレーム", "英語明示述語関係",
    "英日意味フレーム抽出", "英語明示述語関係抽出",
]

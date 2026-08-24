from __future__ import annotations

from dataclasses import dataclass
import re
import unicodedata

from .言語基底_英語 import 英語基本形, 英語関係概念


@dataclass(frozen=True, slots=True)
class 英日意味制御:
    種別: str
    表層: str
    正本: str


@dataclass(frozen=True, slots=True)
class 英日関係質問:
    種別: str
    未知位置: str
    要求型: str
    既知端点: str
    検索述語: str
    反転: bool = False
    受動: bool = False


@dataclass(frozen=True, slots=True)
class 英日意味フレーム:
    正本意味: tuple[str, ...]
    外部検索語: tuple[str, ...]
    制御: tuple[英日意味制御, ...]
    関係質問: 英日関係質問 | None = None


_語 = re.compile(r"[A-Za-z][A-Za-z0-9_-]*")
_末尾疑問符 = re.compile(r"[?？]+$")
_文分割 = re.compile(r"(?<=[?!.。？！])\s+|\n+")
_関係句 = r"(?P<v>[A-Za-z]+(?:\s+(?:to|in|on|with|against|from|of))?)"
_型 = r"(?P<kind>[A-Za-z][A-Za-z0-9 _-]{0,72}?)"
_助動 = r"(?:(?:would|could|may|might|can|must)\s+)?"
_受動助動 = r"(?:is|are|was|were|has\s+been|have\s+been|had\s+been|(?:would|could|may|might|can|must)\s+be)"

_受動未知対象 = re.compile(
    rf"^(?:which|what)\s+(?:of\s+the\s+following\s+)?{_型}\s+"
    rf"{_受動助動}\s+{_関係句}\s+by\s+(?P<s>.+)$",
    re.I,
)
_選択肢能動 = re.compile(
    rf"^(?:which|what)\s+of\s+the\s+following\s+"
    rf"(?:(?:is|are)\s+)?(?:(?P<degree>most|least)\s+likely\s+to\s+|(?P<likelihood>likely|unlikely)\s+to\s+)?"
    rf"{_助動}{_関係句}\s+(?P<o>.+)$",
    re.I,
)
_能動未知対象 = re.compile(
    rf"^(?:which|what)\s+(?:of\s+the\s+following\s+)?{_型}\s+"
    rf"(?:(?:is|are)\s+)?(?:(?P<degree>most|least)\s+likely\s+to\s+|(?P<likelihood>likely|unlikely)\s+to\s+)?"
    rf"{_助動}{_関係句}\s+(?P<o>.+)$",
    re.I,
)
_能動未知終点 = re.compile(
    rf"^(?:which|what)\s+(?:of\s+the\s+following\s+)?{_型}\s+"
    rf"(?:does|do|did)\s+(?P<s>.+?)\s+{_関係句}$",
    re.I,
)
_無型未知終点 = re.compile(
    rf"^(?:what|which)\s+(?:does|do|did)\s+(?P<s>.+?)\s+{_関係句}$",
    re.I,
)
_選択肢受動 = re.compile(
    rf"^(?:which|what)\s+of\s+the\s+following\s+"
    rf"{_受動助動}\s+{_関係句}\s+by\s+(?P<s>.+)$",
    re.I,
)

_制御規則 = (
    ("選択", re.compile(r"\b(?:least\s+likely|unlikely|except|most\s+unlikely)\b", re.I), "反転"),
    ("否定", re.compile(r"\b(?:not|no|never|without|cannot|can't|does\s+not|is\s+not)\b", re.I), "否定"),
    ("量化", re.compile(r"\b(?:all|each|every)\b", re.I), "全称"),
    ("量化", re.compile(r"\b(?:some|any)\b", re.I), "不定"),
    ("量化", re.compile(r"\b(?:none|neither)\b", re.I), "全否定"),
    ("比較", re.compile(r"\b(?:greater|higher|more)\s+than\b", re.I), "大"),
    ("比較", re.compile(r"\b(?:less|lower)\s+than\b", re.I), "小"),
    ("比較", re.compile(r"\bat\s+least\b", re.I), "以上"),
    ("比較", re.compile(r"\bat\s+most\b", re.I), "以下"),
    ("条件", re.compile(r"\b(?:if|when|under|given|assuming)\b", re.I), "条件"),
    ("条件", re.compile(r"\bunless\b|\bin\s+the\s+absence\s+of\b", re.I), "否定条件"),
    ("条件", re.compile(r"\bexcept\b", re.I), "例外"),
    ("様相", re.compile(r"\b(?:can|could|may|might|would)\b", re.I), "可能"),
    ("様相", re.compile(r"\b(?:must|required|necessary)\b", re.I), "必要"),
    ("蓋然性", re.compile(r"\bmost\s+likely\b", re.I), "最大"),
    ("蓋然性", re.compile(r"\bleast\s+likely\b|\bunlikely\b", re.I), "最小"),
)

_検索除外 = frozenset(
    {
        "a", "an", "the", "of", "to", "in", "on", "at", "for", "from", "with", "and", "or",
        "is", "are", "was", "were", "be", "been", "being", "which", "what", "who", "when", "where",
        "why", "how", "this", "that", "these", "those", "it", "its", "do", "does", "did", "has", "have",
        "had", "would", "could", "may", "might", "can", "must", "most", "least", "likely", "unlikely",
        "following", "statement", "statements", "answer", "answers", "option", "options", "choice", "choices",
        "correct", "incorrect", "true", "false", "best", "select", "choose",
    }
)


def _正規化(text: str) -> str:
    return " ".join(unicodedata.normalize("NFKC", str(text)).split()).strip()


def _質問焦点(text: str) -> str:
    raw = _正規化(text)
    if not raw:
        return ""
    parts = [part.strip() for part in _文分割.split(raw) if part.strip()]
    for part in reversed(parts):
        if "?" in part or "？" in part:
            return part
    return parts[-1] if parts else raw


def _端点(text: str) -> str:
    value = _末尾疑問符.sub("", _正規化(text)).strip(" ,;:()[]")
    return value


def _要求型(text: str) -> str:
    value = _正規化(text)
    value = re.sub(r"^(?:of\s+the\s+following\s+)", "", value, flags=re.I)
    value = re.sub(r"\b(?:most|least)\s+likely\s*$", "", value, flags=re.I)
    return value.strip()


def _関係句意味(surface: str) -> tuple[str, str] | None:
    phrase = _正規化(surface).casefold()
    head = phrase.split()[0] if phrase else ""
    kind = 英語関係概念(head)
    if kind is None:
        return None
    lemma = 英語基本形(head)
    suffix = ""
    if " " in phrase:
        suffix = " " + phrase.split(" ", 1)[1]
    return kind, lemma + suffix


def _反転(match: re.Match[str] | None, raw: str) -> bool:
    if match is not None:
        degree = (match.groupdict().get("degree") or "").casefold()
        likelihood = (match.groupdict().get("likelihood") or "").casefold()
        if degree == "least" or likelihood == "unlikely":
            return True
    lowered = raw.casefold()
    return "least likely" in lowered or "most unlikely" in lowered or " except" in (" " + lowered)


def _質問関係(text: str) -> 英日関係質問 | None:
    raw = _端点(text)

    match = _選択肢受動.fullmatch(raw)
    if match:
        relation = _関係句意味(match.group("v"))
        if relation is not None:
            kind, predicate = relation
            return 英日関係質問(kind, "終点", "選択肢", _端点(match.group("s")), predicate, _反転(match, raw), True)

    match = _選択肢能動.fullmatch(raw)
    if match:
        relation = _関係句意味(match.group("v"))
        if relation is not None:
            kind, predicate = relation
            return 英日関係質問(kind, "始点", "選択肢", _端点(match.group("o")), predicate, _反転(match, raw), False)

    match = _受動未知対象.fullmatch(raw)
    if match:
        relation = _関係句意味(match.group("v"))
        if relation is not None:
            kind, predicate = relation
            return 英日関係質問(kind, "終点", _要求型(match.group("kind")), _端点(match.group("s")), predicate, _反転(match, raw), True)

    match = _能動未知終点.fullmatch(raw)
    if match:
        relation = _関係句意味(match.group("v"))
        if relation is not None:
            kind, predicate = relation
            return 英日関係質問(kind, "終点", _要求型(match.group("kind")), _端点(match.group("s")), predicate, _反転(match, raw), False)

    match = _無型未知終点.fullmatch(raw)
    if match:
        relation = _関係句意味(match.group("v"))
        if relation is not None:
            kind, predicate = relation
            return 英日関係質問(kind, "終点", "", _端点(match.group("s")), predicate, _反転(match, raw), False)

    match = _能動未知対象.fullmatch(raw)
    if match:
        relation = _関係句意味(match.group("v"))
        if relation is not None:
            kind, predicate = relation
            return 英日関係質問(kind, "始点", _要求型(match.group("kind")), _端点(match.group("o")), predicate, _反転(match, raw), False)
    return None


def _制御(text: str) -> tuple[英日意味制御, ...]:
    out: list[英日意味制御] = []
    seen: set[tuple[str, str]] = set()
    for kind, pattern, canonical in _制御規則:
        for match in pattern.finditer(text):
            key = (kind, canonical)
            if key in seen:
                continue
            seen.add(key)
            out.append(英日意味制御(kind, _正規化(match.group(0)), canonical))
    return tuple(out)


def _検索語(text: str) -> tuple[str, ...]:
    out: list[str] = []
    seen: set[str] = set()
    for token in _語.findall(text):
        value = token.casefold()
        if value in _検索除外:
            continue
        lemma = 英語基本形(value)
        if lemma in _検索除外 or not lemma:
            continue
        if lemma not in seen:
            seen.add(lemma)
            out.append(lemma)
        relation = 英語関係概念(lemma)
        if relation is not None:
            marker = f"rel:{relation}"
            if marker not in seen:
                seen.add(marker)
                out.append(marker)
    return tuple(out)


def 英日意味フレーム抽出(text: str) -> 英日意味フレーム:
    focus = _質問焦点(text)
    controls = _制御(focus)
    question = _質問関係(focus)
    canonical: list[str] = [f"{item.種別}:{item.正本}" for item in controls]
    if question is not None:
        canonical.extend((f"関係:{question.種別}", f"不足位置:{question.未知位置}", f"要求型:{question.要求型}" if question.要求型 else "要求型:未特定"))
    return 英日意味フレーム(tuple(canonical), _検索語(focus), controls, question)


__all__ = ["英日意味制御", "英日関係質問", "英日意味フレーム", "英日意味フレーム抽出"]

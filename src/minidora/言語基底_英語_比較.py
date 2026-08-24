from __future__ import annotations

from dataclasses import dataclass
import re
import unicodedata


@dataclass(frozen=True, slots=True)
class 英語比較意味:
    種別: str
    始点: str
    終点: str
    検索述語: str
    未知位置: str = ""
    要求型: str = ""


_文分割 = re.compile(r"(?<=[?!.])\s+|\n+")
_末尾記号 = re.compile(r"[?!.]+$")
_端点 = r"[^?!.;,\n]{1,180}?"
_型 = r"[A-Za-z][A-Za-z0-9 _-]{0,72}?"

_比較句: tuple[tuple[str, str], ...] = (
    ("比較.以上", r"at\s+least"),
    ("比較.以下", r"at\s+most"),
    ("比較.大", r"greater\s+than|higher\s+than|larger\s+than"),
    ("比較.小", r"less\s+than|lower\s+than|smaller\s+than"),
    ("等価", r"equal\s+to|equivalent\s+to"),
    ("不同", r"different\s+from|unequal\s+to"),
)


def _normalize(text: object) -> str:
    return " ".join(unicodedata.normalize("NFKC", str(text)).split()).strip(" ,;:()[]")


def _compile_patterns() -> tuple[tuple[str, re.Pattern[str], re.Pattern[str], re.Pattern[str]], ...]:
    rows: list[tuple[str, re.Pattern[str], re.Pattern[str], re.Pattern[str]]] = []
    for kind, phrase in _比較句:
        declarative = re.compile(
            rf"^(?P<s>{_端点})\s+(?:is|are|was|were)\s+(?P<v>{phrase})\s+(?P<o>{_端点})$",
            re.I,
        )
        unknown_start = re.compile(
            rf"^(?:which|what)\s+(?:(?:of\s+the\s+following)\s+)?(?P<kind>{_型})?\s*"
            rf"(?:is|are|was|were)\s+(?P<v>{phrase})\s+(?P<o>{_端点})$",
            re.I,
        )
        unknown_end = re.compile(
            rf"^(?:which|what)\s+(?:(?:of\s+the\s+following)\s+)?(?P<kind>{_型})?\s*"
            rf"(?:is|are|was|were)\s+(?P<s>{_端点})\s+(?P<v>{phrase})$",
            re.I,
        )
        rows.append((kind, declarative, unknown_start, unknown_end))
    return tuple(rows)


_比較規則 = _compile_patterns()
_等価動詞 = re.compile(rf"^(?P<s>{_端点})\s+(?P<v>equals|equaled|equalled)\s+(?P<o>{_端点})$", re.I)


def _focus_sentences(text: str) -> tuple[str, ...]:
    raw = " ".join(unicodedata.normalize("NFKC", str(text)).split()).strip()
    if not raw:
        return ()
    parts = [part.strip() for part in _文分割.split(raw) if part.strip()]
    return tuple(_末尾記号.sub("", part).strip() for part in parts if part.strip())


def _requested_type(value: object) -> str:
    text = _normalize(value)
    return text or "選択肢"


def 英語比較意味抽出(text: str) -> tuple[英語比較意味, ...]:
    """世界知識を使わず、明示された英語比較だけを意味関係へ戻す。"""
    out: list[英語比較意味] = []
    for sentence in _focus_sentences(text):
        if not sentence:
            continue
        is_question = "?" in str(text) and sentence == _focus_sentences(text)[-1]

        if not is_question:
            eq = _等価動詞.fullmatch(sentence)
            if eq:
                item = 英語比較意味("等価", _normalize(eq.group("s")), _normalize(eq.group("o")), "equal to")
                if item not in out:
                    out.append(item)

        for kind, declarative, unknown_start, unknown_end in _比較規則:
            if is_question:
                match = unknown_start.fullmatch(sentence)
                if match:
                    item = 英語比較意味(
                        kind,
                        _requested_type(match.groupdict().get("kind") or ""),
                        _normalize(match.group("o")),
                        _normalize(match.group("v")).casefold(),
                        "始点",
                        _requested_type(match.groupdict().get("kind") or ""),
                    )
                    if item not in out:
                        out.append(item)
                    continue
                match = unknown_end.fullmatch(sentence)
                if match:
                    item = 英語比較意味(
                        kind,
                        _normalize(match.group("s")),
                        _requested_type(match.groupdict().get("kind") or ""),
                        _normalize(match.group("v")).casefold(),
                        "終点",
                        _requested_type(match.groupdict().get("kind") or ""),
                    )
                    if item not in out:
                        out.append(item)
                    continue
            else:
                match = declarative.fullmatch(sentence)
                if match:
                    item = 英語比較意味(
                        kind,
                        _normalize(match.group("s")),
                        _normalize(match.group("o")),
                        _normalize(match.group("v")).casefold(),
                    )
                    if item not in out:
                        out.append(item)
    return tuple(out)


__all__ = ["英語比較意味", "英語比較意味抽出"]

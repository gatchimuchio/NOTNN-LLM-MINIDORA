from __future__ import annotations

from dataclasses import dataclass
import re
import unicodedata


_SPLIT = re.compile(r"(?<=[?!.。？！])\s+|\n+")
_EXCEPTION_PATTERNS = (
    re.compile(r"\bexcept\b", re.I),
    re.compile(r"\bincorrect\b", re.I),
    re.compile(r"\bfalse\b", re.I),
    re.compile(r"\bnot\s+(?:correct|true|valid|permitted|allowed|possible|associated)\b", re.I),
    re.compile(r"\bwhich\b.{0,100}\b(?:does|do|is|are|will|would|can)\s+not\b", re.I),
    re.compile(r"\bwhich\b.{0,100}\bcannot\b", re.I),
    re.compile(r"(?:誤っている|正しくない|該当しない|当てはまらない|許可されない|認められない|除く|以外)", re.I),
)


@dataclass(frozen=True, slots=True)
class HDS選択意図:
    種別: str
    焦点: str
    根拠: tuple[str, ...] = ()


def _焦点(text: str) -> str:
    raw = unicodedata.normalize("NFKC", str(text)).strip()
    if not raw:
        return ""
    segments = [segment.strip() for segment in _SPLIT.split(raw) if segment.strip()]
    if not segments:
        return raw
    # 採否方向は背景説明から伝染させず、最後の実質問文だけで決める。
    for segment in reversed(segments):
        if "?" in segment or "？" in segment:
            return segment[-800:]
    return segments[-1][-800:]


def HDS選択意図判定(text: str) -> HDS選択意図:
    """選択問題の採否方向を、最終問いの表層論理だけから判定する。

    ベンチ名・分野・正解候補は参照しない。現在は明示的な単一例外/否定選択だけを
    `EXCEPTION` とし、それ以外は `POSITIVE` とする。曖昧な最小/最大比較はここで推測しない。
    """
    focus = _焦点(text)
    matched = tuple(pattern.pattern for pattern in _EXCEPTION_PATTERNS if pattern.search(focus))
    if matched:
        return HDS選択意図("EXCEPTION", focus, matched)
    return HDS選択意図("POSITIVE", focus, ())


__all__ = ["HDS選択意図", "HDS選択意図判定"]

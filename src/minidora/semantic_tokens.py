from __future__ import annotations

import re
import unicodedata

from .言語基底 import 標準言語基底P


_WORD = re.compile(r"[A-Za-z0-9_+\-\.]+|[Α-Ωα-ωϐ-Ͽ]+|[ぁ-んァ-ヶー]+|[一-龥々]+")
_MATH_NUMBER = r"[-+]?(?:\d+(?:\.\d+)?|\.\d+)(?:[eE][-+]?\d+)?"
_MATH_ANCHOR = re.compile(
    rf"(?<![A-Za-z0-9_]){_MATH_NUMBER}(?:\s*(?:/|\^|\*|×)\s*{_MATH_NUMBER})?(?![A-Za-z0-9_])"
)
_LATEX_FRAC = re.compile(
    rf"\\frac\s*\{{\s*({_MATH_NUMBER})\s*\}}\s*\{{\s*({_MATH_NUMBER})\s*\}}"
)
_SQRT_ANCHOR = re.compile(
    rf"(?:\\sqrt|sqrt)\s*[\{{\(]\s*({_MATH_NUMBER})\s*[\}}\)]",
    flags=re.I,
)
_ENUM_ATOM = re.compile(r"(?<![A-Za-z0-9_])([A-Za-zΑ-Ωα-ωϐ-Ͽ])\s*[\)\].:]")
_MATH_VAR_LEFT = re.compile(r"(?<![A-Za-z0-9_])([A-Za-zΑ-Ωα-ωϐ-Ͽ])(?=\s*(?:=|[+\-*/^<>≤≥]))")
_MATH_VAR_RIGHT = re.compile(r"(?:=|[+\-*/^<>≤≥])\s*([A-Za-zΑ-Ωα-ωϐ-Ͽ])(?![A-Za-z0-9_])")

_STOP = {
    # 基本機能語
    "the", "a", "an", "of", "to", "in", "on", "at", "for", "from", "with", "and", "or",
    "is", "are", "was", "were", "be", "been", "being", "which", "what", "who", "when", "where",
    "why", "how", "this", "that", "these", "those", "it", "its", "as", "by", "than", "then",
    "do", "does", "did", "have", "has", "had", "will", "shall", "would", "could", "should",
    "may", "might", "can", "about", "into", "through", "during", "after", "before", "between", "among",
    # 選択QAの制御語。真偽・反転はCompiler/J側で別構造として保持し、意味証拠へ混ぜない。
    "following", "statement", "statements", "answer", "answers", "option", "options", "choice", "choices",
    "correct", "incorrect", "true", "false", "most", "least", "likely", "unlikely", "best", "except",
    "select", "choose", "chosen", "consider", "considered", "describe", "describes", "described",
    "regarding", "according", "given", "respect", "respectively", "not",
}


def _english_stem(value: str) -> str:
    """意味照合用の保守的な英語表層正規化。"""
    if not re.fullmatch(r"[a-z]+", value):
        return value
    if value in {"species", "series"}:
        return value
    if len(value) > 4 and value.endswith("ies"):
        return value[:-3] + "y"
    if len(value) > 5 and value.endswith("sses"):
        return value[:-2]
    if len(value) > 5 and value.endswith(("xes", "zes", "ches", "shes")):
        return value[:-2]
    if len(value) > 4 and value.endswith("ing"):
        stem = value[:-3]
        if len(stem) >= 2 and stem[-1] == stem[-2] and stem[-1] not in "aeiou":
            stem = stem[:-1]
        if stem.endswith("us"):
            return stem + "e"
        return stem
    if len(value) > 4 and value.endswith("ed"):
        stem = value[:-2]
        if len(stem) >= 2 and stem[-1] == stem[-2] and stem[-1] not in "aeiou":
            stem = stem[:-1]
        return stem
    if len(value) > 3 and value.endswith("s") and not value.endswith(("ss", "is", "us")):
        return value[:-1]
    return value


def _数値語(value: str) -> bool:
    return re.fullmatch(_MATH_NUMBER, value) is not None


def _記号語(value: str) -> str:
    return "sym:" + value.casefold()


def _数式anchor(raw: str) -> set[str]:
    out: set[str] = set()
    for numerator, denominator in _LATEX_FRAC.findall(raw):
        out.add(f"math:{numerator}/{denominator}".casefold())
    for value in _SQRT_ANCHOR.findall(raw):
        out.add(f"math:sqrt({value})".casefold())
    for anchor in _MATH_ANCHOR.findall(raw):
        compact = re.sub(r"\s+", "", anchor).replace("×", "*")
        if compact:
            out.add("math:" + compact.casefold())
    return out


def 意味語(text: object) -> frozenset[str]:
    """HDS意味照合で共有する正規化語集合を返す。

    技術文では一文字の変数・列挙記号・ギリシャ文字・科学記数法自体が意味を持つ。
    日本語は共有言語基底Pを参照し、一文字漢字を意味記号として保持する一方、助詞など
    文法機能だけの語は意味証拠へ混ぜない。選択QAの制御語はCompiler/J側の
    選択意図・否定・反転構造に責任を分離する。
    """
    raw = unicodedata.normalize("NFKC", str(text))
    out: set[str] = _数式anchor(raw)

    stripped = raw.strip()
    if re.fullmatch(r"[A-Za-zΑ-Ωα-ωϐ-Ͽ]", stripped):
        out.add("atom:" + stripped.casefold())

    for atom in _ENUM_ATOM.findall(raw):
        out.add("atom:" + atom.casefold())

    for variable in (*_MATH_VAR_LEFT.findall(raw), *_MATH_VAR_RIGHT.findall(raw)):
        out.add(_記号語(variable))

    for token in _WORD.findall(raw):
        original = token
        value = token.casefold().strip("._")
        if _数値語(value):
            out.add(value)
            continue

        if len(original) == 1 and (
            original.isupper()
            or re.fullmatch(r"[Α-Ωα-ωϐ-Ͽ]", original) is not None
        ):
            out.add(_記号語(original))
            continue

        # 日本語一文字漢字はそれ自体が意味記号になり得るため、英字と同じ長さ基準で捨てない。
        if len(original) == 1 and 標準言語基底P.文字知識(original).体系 == "漢字":
            out.add(original)
            continue

        # 助詞・否定・丁寧表現などの文法機能はCompiler側の構造へ責任分離する。
        if 標準言語基底P.文法機能(original) is not None:
            continue

        value = value.strip("-")
        if len(value) <= 1 or value in _STOP:
            continue
        normalized = _english_stem(value)
        if len(normalized) <= 1 or normalized in _STOP:
            continue
        out.add(normalized)
    return frozenset(out)


__all__ = ["意味語"]

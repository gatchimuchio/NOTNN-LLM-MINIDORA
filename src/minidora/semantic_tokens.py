from __future__ import annotations

import re


_WORD = re.compile(r"[A-Za-z0-9_+\-\.]+|[ぁ-んァ-ヶー]+|[一-龥々]+")
_STOP = {
    "the", "a", "an", "of", "to", "in", "on", "at", "for", "from", "with", "and", "or",
    "is", "are", "was", "were", "be", "been", "being", "which", "what", "who", "when", "where",
    "why", "how", "this", "that", "these", "those", "it", "its", "as", "by", "than", "then",
}


def _english_stem(value: str) -> str:
    """意味照合用の保守的な英語表層正規化。

    言語学的な完全lemmatizerではない。外部依存を増やさず、問い・候補・K graphで
    同じ規則を共有して、単純な屈折差だけで意味接続が切れないことを目的とする。
    """
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


def 意味語(text: object) -> frozenset[str]:
    """HDS意味照合で共有する正規化語集合を返す。"""
    out: set[str] = set()
    for token in _WORD.findall(str(text)):
        value = token.casefold().strip("._-")
        if len(value) <= 1 or value in _STOP:
            continue
        normalized = _english_stem(value)
        if len(normalized) <= 1 or normalized in _STOP:
            continue
        out.add(normalized)
    return frozenset(out)


__all__ = ["意味語"]

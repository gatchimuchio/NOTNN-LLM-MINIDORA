from __future__ import annotations

from collections import Counter
from math import sqrt
import re

from .型 import ニュース項目


要約モジュール版 = "deterministic-summary-v0.1"


def _文分割(text: str) -> list[str]:
    normalized = re.sub(r"\r\n?", "\n", text or "").strip()
    if not normalized:
        return []
    parts = re.split(r"(?<=[。！？!?])\s*|\n+", normalized)
    return [re.sub(r"\s+", " ", item).strip() for item in parts if item.strip()]


def _二文字列(text: str) -> list[str]:
    normalized = re.sub(r"[\s、。！？!?・「」『』（）()\[\]【】,:;：；]", "", text)
    if len(normalized) < 2:
        return [normalized] if normalized else []
    return [normalized[index:index + 2] for index in range(len(normalized) - 1)]


def _切詰め(text: str, limit: int) -> str:
    if len(text) <= limit:
        return text
    return text[: max(1, limit - 1)].rstrip() + "…"


class 決定論的要約器:
    """入力に存在する文字列だけを抽出・圧縮する要約器。自由生成を行わない。"""

    def 文章要約(self, text: str, *, 文数: int = 3, 最大文字数: int = 500) -> str:
        sentences = _文分割(text)
        if not sentences:
            return ""
        if len(sentences) <= 文数:
            return _切詰め(" ".join(sentences), 最大文字数)

        frequency = Counter(token for sentence in sentences for token in _二文字列(sentence))
        scored: list[tuple[float, int]] = []
        for index, sentence in enumerate(sentences):
            tokens = _二文字列(sentence)
            repeated = sum(max(0, frequency[token] - 1) for token in tokens)
            content = sum(1 for char in sentence if not char.isspace())
            score = repeated / sqrt(max(1, content))
            score += 1.0 / (index + 1)  # 同点時に文脈先頭を優先する決定論的tie-break
            scored.append((score, index))
        selected = sorted(index for _, index in sorted(scored, key=lambda item: (-item[0], item[1]))[: max(1, 文数)])
        summary = " ".join(sentences[index] for index in selected)
        return _切詰め(summary, 最大文字数)

    def ニュース要約(self, items: tuple[ニュース項目, ...], *, 最大件数: int = 3, 一件最大文字数: int = 150) -> str:
        if not items:
            return ""
        lines: list[str] = []
        for item in items[: max(1, 最大件数)]:
            material = _文分割(item.要約素材)
            body = material[0] if material else ""
            if body and body != item.題名:
                line = f"- {item.題名} — {_切詰め(body, 一件最大文字数)}"
            else:
                line = f"- {item.題名}"
            lines.append(line)
        return "\n".join(lines)

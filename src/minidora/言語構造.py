from __future__ import annotations

from dataclasses import dataclass
import re
import unicodedata

from .semantic_tokens import 意味語
from .言語基底_英語 import 英語明示関係構文


_語 = re.compile(r"[A-Za-z0-9_+./^%µμΩ°\-]+|[Α-Ωα-ωϐ-Ͽ]+|[ぁ-んァ-ヶー]+|[一-龥々]+|[^\s]")
_英語否定 = re.compile(
    r"\b(?:do|does|did|is|are|was|were|be|been|being|can|could|may|might|must|will|would|should|has|have|had)\s+not\b|\bnever\b",
    re.I,
)
_日本語否定 = re.compile(r"(?:ではない|じゃない|しない|ない|ず|ぬ)")
_条件 = (
    re.compile(r"\b(?:if|when|given|assuming|unless)\s+([^,;.!?]{1,160})", re.I),
    re.compile(r"\bunder\s+([^,;.!?]{1,160})", re.I),
    re.compile(r"(?:もし|場合|とき|条件下|前提(?:として)?)([^。！？、]{1,120})"),
)
_記号関係 = re.compile(
    r"(?P<s>[A-Za-zΑ-Ωα-ωϐ-Ͽ0-9_µμΩ.+\-]+)\s*"
    r"(?P<op>->|=>|→|⇒|>=|<=|≥|≤|!=|≠|>|<|=)\s*"
    r"(?P<o>[A-Za-zΑ-Ωα-ωϐ-Ͽ0-9_µμΩ.+\-]+)"
)

_日本語関係語 = (
    ("因果", ("引き起こす", "生じさせる", "もたらす", "原因となる")),
    ("増加", ("増加させる", "高める", "促進する")),
    ("減少", ("減少させる", "低下させる", "抑える")),
    ("阻害", ("阻害する", "抑制する", "遮断する")),
    ("活性化", ("活性化する", "刺激する")),
    ("生成", ("生成する", "産生する", "作る")),
    ("要求", ("必要とする", "依存する")),
    ("包含", ("含む", "包含する")),
    ("使用", ("使う", "使用する", "利用する")),
    ("防止", ("防ぐ", "予防する")),
)


def _関係正規表現(verbs: tuple[str, ...]) -> re.Pattern[str]:
    choices = "|".join(re.escape(v) for v in sorted(verbs, key=len, reverse=True))
    return re.compile(
        rf"(?P<s>[^。！？、]{{1,100}}?)(?:が|は)(?P<o>[^。！？、]{{1,100}}?)(?:を)?(?P<v>{choices})"
    )


def _日本語否定形(verb: str) -> tuple[str, ...]:
    """既存述語の辞書形から一般的な否定活用だけを派生する。"""
    if verb.endswith("する"):
        stem = verb[:-2]
        return (stem + "しない", stem + "しません", stem + "せず", stem + "せぬ")
    if verb.endswith("させる") or verb.endswith("める") or verb.endswith("える"):
        stem = verb[:-1]
        return (stem + "ない", stem + "ません", stem + "ず", stem + "ぬ")
    last = verb[-1:]
    a_row = {"う":"わ","く":"か","ぐ":"が","す":"さ","つ":"た","ぬ":"な","ぶ":"ば","む":"ま","る":"ら"}
    i_row = {"う":"い","く":"き","ぐ":"ぎ","す":"し","つ":"ち","ぬ":"に","ぶ":"び","む":"み","る":"り"}
    if last in a_row:
        base = verb[:-1]
        return (
            base + a_row[last] + "ない",
            base + i_row[last] + "ません",
            base + a_row[last] + "ず",
            base + a_row[last] + "ぬ",
        )
    return ()


_日本語関係構文 = tuple((kind, _関係正規表現(verbs)) for kind, verbs in _日本語関係語)
_日本語否定関係構文 = tuple(
    (kind, _関係正規表現(tuple(form for verb in verbs for form in _日本語否定形(verb))))
    for kind, verbs in _日本語関係語
)

_記号種別 = {
    "->": "方向", "=>": "方向", "→": "方向", "⇒": "方向",
    ">": "比較.大", "<": "比較.小", ">=": "比較.以上", "≥": "比較.以上",
    "<=": "比較.以下", "≤": "比較.以下", "=": "等価", "!=": "不同", "≠": "不同",
}
_明示対比境界 = re.compile(r"\s*,\s*(?:but|whereas)\s+|\s*;\s*(?:but|whereas)\s+|、?しかし(?:、)?", re.I)


@dataclass(frozen=True, slots=True)
class 言語関係構造:
    種別: str
    始点: frozenset[str]
    終点: frozenset[str]
    肯定: bool = True
    条件: tuple[frozenset[str], ...] = ()
    述語: frozenset[str] = frozenset()

    @property
    def 署名(self) -> tuple[object, ...]:
        return (
            self.種別,
            tuple(sorted(self.始点)), tuple(sorted(self.終点)), self.肯定,
            tuple(tuple(sorted(item)) for item in self.条件),
            tuple(sorted(self.述語)) if self.種別 == "開放述語" else (),
        )


def _意味集合(text: str) -> frozenset[str]:
    return 意味語(" ".join(str(text).split()).strip(" ,;:。！？?"))


def 意味列(text: str) -> tuple[str, ...]:
    out: list[str] = []
    for surface in _語.findall(unicodedata.normalize("NFKC", str(text))):
        values = sorted(意味語(surface))
        if values:
            out.extend(values)
    return tuple(out)


def _条件群(text: str) -> tuple[frozenset[str], ...]:
    out: list[frozenset[str]] = []
    seen: set[tuple[str, ...]] = set()
    for pattern in _条件:
        for match in pattern.finditer(text):
            value = _意味集合(match.group(1))
            if not value:
                continue
            key = tuple(sorted(value))
            if key in seen:
                continue
            seen.add(key); out.append(value)
    return tuple(out)


def _否定除去(text: str) -> tuple[str, bool]:
    normalized = unicodedata.normalize("NFKC", str(text))
    negative = bool(_英語否定.search(normalized) or _日本語否定.search(normalized))
    cleaned = re.sub(r"\b(?:do|does|did)\s+not\s+", "", normalized, flags=re.I)
    cleaned = re.sub(
        r"\b(is|are|was|were|be|been|being|can|could|may|might|must|will|would|should|has|have|had)\s+not\s+",
        r"\1 ", cleaned, flags=re.I,
    )
    return cleaned, negative


def _文単位(text: str) -> tuple[str, ...]:
    """否定・条件のscopeを文と明示対比境界へ局所化する。小数点は分割しない。"""
    value = unicodedata.normalize("NFKC", str(text))
    parts: list[str] = []
    start = 0
    for index, char in enumerate(value):
        sentence_end = char in "。！？!?\n"
        if char == ".":
            left_digit = index > 0 and value[index - 1].isdigit()
            right_digit = index + 1 < len(value) and value[index + 1].isdigit()
            sentence_end = not (left_digit and right_digit)
        if sentence_end:
            piece = value[start:index].strip()
            if piece:
                parts.extend(x.strip() for x in _明示対比境界.split(piece) if x.strip())
            start = index + 1
    tail = value[start:].strip()
    if tail:
        parts.extend(x.strip() for x in _明示対比境界.split(tail) if x.strip())
    return tuple(parts) if parts else (value,)


def _単位関係抽出(raw: str, 言語体系: str) -> tuple[言語関係構造, ...]:
    cleaned, negative = _否定除去(raw)
    conditions = _条件群(raw)
    out: list[言語関係構造] = []
    seen: set[tuple[object, ...]] = set()

    def add(kind: str, subject: str, object_: str, predicate: str, *, reverse: bool = False, positive: bool | None = None) -> None:
        s = _意味集合(subject); o = _意味集合(object_); p = _意味集合(predicate)
        if reverse: s, o = o, s
        if not s or not o: return
        item = 言語関係構造(kind, s, o, not negative if positive is None else positive, conditions, p)
        if item.署名 in seen: return
        seen.add(item.署名); out.append(item)

    for match in _記号関係.finditer(cleaned):
        add(_記号種別[match.group("op")], match.group("s"), match.group("o"), match.group("op"))

    if str(言語体系).casefold().startswith("自然言語:en") or re.search(r"[A-Za-z]", cleaned):
        for syntax in 英語明示関係構文:
            for match in syntax.正規表現.finditer(cleaned):
                add(syntax.種別, match.group("s"), match.group("o"), match.group("v"), reverse=syntax.反転)

    if str(言語体系).casefold().startswith("自然言語:ja") or re.search(r"[ぁ-んァ-ヶ一-龥]", cleaned):
        for kind, pattern in _日本語関係構文:
            for match in pattern.finditer(cleaned):
                add(kind, match.group("s"), match.group("o"), match.group("v"), positive=True)
        for kind, pattern in _日本語否定関係構文:
            for match in pattern.finditer(raw):
                add(kind, match.group("s"), match.group("o"), match.group("v"), positive=False)

    return tuple(out)


def 言語関係抽出(text: str, 言語体系: str = "自然言語:ja") -> tuple[言語関係構造, ...]:
    out: list[言語関係構造] = []
    seen: set[tuple[object, ...]] = set()
    for unit in _文単位(text):
        for item in _単位関係抽出(unit, 言語体系):
            if item.署名 in seen: continue
            seen.add(item.署名); out.append(item)
    return tuple(out)


__all__ = ["言語関係構造", "意味列", "言語関係抽出"]

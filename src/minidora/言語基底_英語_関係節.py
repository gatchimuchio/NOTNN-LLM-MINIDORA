from __future__ import annotations

from dataclasses import dataclass
import re
import unicodedata


@dataclass(frozen=True, slots=True)
class 英語関係節意味:
    先行詞: str
    種別: str
    相手端点: str
    検索述語: str
    極性: str = "肯定"
    様相: str = ""
    受動: bool = False
    関係代名詞: str = "which"


# 自由代名詞 it/this/that は扱わない。
# `NP, which/who ... ,` のように文法上先行詞が局所的に一意な非制限関係節だけを対象とする。
_先行詞 = r"(?P<a>(?:(?:the|a|an)\s+)?[A-Za-z0-9][A-Za-z0-9_+./^%µμΩ°\-]*(?:\s+[A-Za-z0-9][A-Za-z0-9_+./^%µμΩ°\-]*){0,7})"
_相手 = r"(?P<o>[A-Za-z0-9][^,.;!?\n]{0,100}?)"
_代名詞 = r"(?P<r>which|who)"
_様相 = r"(?P<m>can|could|may|might|must|would)"

_関係族: tuple[tuple[str, str, str], ...] = (
    ("因果", r"cause|causes|lead\s+to|leads\s+to|result\s+in|results\s+in", "cause"),
    ("増加", r"increase|increases|raise|raises|enhance|enhances", "increase"),
    ("減少", r"decrease|decreases|reduce|reduces|lower|lowers", "decrease"),
    ("阻害", r"inhibit|inhibits|suppress|suppresses|block|blocks", "inhibit"),
    ("活性化", r"activate|activates|stimulate|stimulates", "activate"),
    ("生成", r"produce|produces|generate|generates", "produce"),
    ("要求", r"require|requires|need|needs|depend\s+on|depends\s+on", "require"),
    ("包含", r"contain|contains|include|includes|comprise|comprises", "contain"),
    ("使用", r"use|uses|utilize|utilizes|employ|employs", "use"),
    ("防止", r"prevent|prevents|protect\s+against|protects\s+against|protect\s+from|protects\s+from", "prevent"),
    ("相関", r"associate\s+with|associates\s+with|correlate\s+with|correlates\s+with|relate\s+to|relates\s+to", "correlate with"),
)

_受動族: tuple[tuple[str, str, str], ...] = (
    ("因果", r"caused", "cause"),
    ("増加", r"increased|raised|enhanced", "increase"),
    ("減少", r"decreased|reduced|lowered", "decrease"),
    ("阻害", r"inhibited|suppressed|blocked", "inhibit"),
    ("活性化", r"activated|stimulated", "activate"),
    ("生成", r"produced|generated", "produce"),
    ("要求", r"required|needed", "require"),
    ("使用", r"used|utilized|employed", "use"),
    ("防止", r"prevented|protected", "prevent"),
)


def _compile() -> tuple[tuple[str, str, re.Pattern[str], bool, str], ...]:
    rows: list[tuple[str, str, re.Pattern[str], bool, str]] = []
    boundary = r"(?:^|(?<=[.;])\s*)"
    tail = r"(?=\s*,|\s*[.;!?]|$)"

    for kind, forms, predicate in _関係族:
        patterns = (
            ("肯定", re.compile(rf"{boundary}{_先行詞}\s*,\s*{_代名詞}\s+(?P<v>{forms})\s+{_相手}{tail}", re.I), ""),
            ("否定", re.compile(rf"{boundary}{_先行詞}\s*,\s*{_代名詞}\s+(?:does|do|did)\s+not\s+(?P<v>{forms})\s+{_相手}{tail}", re.I), ""),
            ("肯定", re.compile(rf"{boundary}{_先行詞}\s*,\s*{_代名詞}\s+{_様相}\s+(?P<v>{forms})\s+{_相手}{tail}", re.I), "modal"),
            ("否定", re.compile(rf"{boundary}{_先行詞}\s*,\s*{_代名詞}\s+{_様相}\s+not\s+(?P<v>{forms})\s+{_相手}{tail}", re.I), "modal"),
        )
        for polarity, pattern, modal in patterns:
            rows.append((kind, predicate, pattern, False, polarity + ":" + modal))

    for kind, forms, predicate in _受動族:
        patterns = (
            ("肯定", re.compile(rf"{boundary}{_先行詞}\s*,\s*{_代名詞}\s+(?:is|are|was|were)\s+(?P<v>{forms})\s+by\s+{_相手}{tail}", re.I), ""),
            ("否定", re.compile(rf"{boundary}{_先行詞}\s*,\s*{_代名詞}\s+(?:is|are|was|were)\s+not\s+(?P<v>{forms})\s+by\s+{_相手}{tail}", re.I), ""),
            ("肯定", re.compile(rf"{boundary}{_先行詞}\s*,\s*{_代名詞}\s+{_様相}\s+be\s+(?P<v>{forms})\s+by\s+{_相手}{tail}", re.I), "modal"),
            ("否定", re.compile(rf"{boundary}{_先行詞}\s*,\s*{_代名詞}\s+{_様相}\s+not\s+be\s+(?P<v>{forms})\s+by\s+{_相手}{tail}", re.I), "modal"),
        )
        for polarity, pattern, modal in patterns:
            rows.append((kind, predicate, pattern, True, polarity + ":" + modal))
    return tuple(rows)


_規則 = _compile()


def _norm(value: object) -> str:
    return " ".join(unicodedata.normalize("NFKC", str(value)).split()).strip(" ,;:()[]")


def 英語関係節意味抽出(text: str) -> tuple[英語関係節意味, ...]:
    raw = unicodedata.normalize("NFKC", str(text))
    out: list[英語関係節意味] = []
    for kind, predicate, pattern, passive, flags in _規則:
        polarity, modal_flag = flags.split(":", 1)
        for match in pattern.finditer(raw):
            antecedent = _norm(match.group("a"))
            other = _norm(match.group("o"))
            relative = _norm(match.group("r")).casefold()
            modal = _norm(match.groupdict().get("m") or "").casefold() if modal_flag else ""
            if not antecedent or not other or antecedent.casefold() == other.casefold():
                continue
            item = 英語関係節意味(
                antecedent,
                kind,
                other,
                predicate,
                polarity,
                modal,
                passive,
                relative,
            )
            if item not in out:
                out.append(item)
    return tuple(out)


__all__ = ["英語関係節意味", "英語関係節意味抽出"]

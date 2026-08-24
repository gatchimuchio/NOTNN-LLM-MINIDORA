from __future__ import annotations

from dataclasses import dataclass
import re
import unicodedata


@dataclass(frozen=True, slots=True)
class 英語分類意味:
    対象: str
    分類先: str
    未知対象: bool = False
    要求型: str = ""
    検索述語: str = "is a"


_文分割 = re.compile(r"(?<=[?!.])\s+|\n+")
_末尾 = re.compile(r"[?!.]+$")
_主体 = r"(?P<s>[A-Za-z0-9][^?!.;,]{0,120}?)"
_型 = r"(?P<o>[A-Za-z][A-Za-z0-9_-]*(?:\s+[A-Za-z][A-Za-z0-9_-]*){0,5})"
_要求型 = r"(?P<kind>[A-Za-z][A-Za-z0-9_-]*(?:\s+[A-Za-z][A-Za-z0-9_-]*){0,3})"

_単純分類 = re.compile(rf"^{_主体}\s+(?:is|was)\s+(?:a|an)\s+{_型}$", re.I)
_型分類 = re.compile(rf"^{_主体}\s+(?:is|was)\s+(?:(?:a|an)\s+)?(?:type|kind|form|class|example)\s+of\s+{_型}$", re.I)
_未知単純 = re.compile(rf"^which\s+(?:(?:of\s+the\s+following)\s+)?(?:{_要求型}\s+)?(?:is|was)\s+(?:a|an)\s+{_型}$", re.I)
_未知型分類 = re.compile(rf"^which\s+(?:(?:of\s+the\s+following)\s+)?(?:{_要求型}\s+)?(?:is|was)\s+(?:(?:a|an)\s+)?(?:type|kind|form|class|example)\s+of\s+{_型}$", re.I)


def _norm(value: object) -> str:
    return " ".join(unicodedata.normalize("NFKC", str(value)).split()).strip(" ,;:()[]")


def _sentences(text: str) -> tuple[str, ...]:
    raw = " ".join(unicodedata.normalize("NFKC", str(text)).split()).strip()
    if not raw:
        return ()
    return tuple(_末尾.sub("", p).strip() for p in _文分割.split(raw) if p.strip())


def 英語分類意味抽出(text: str) -> tuple[英語分類意味, ...]:
    out: list[英語分類意味] = []
    sentences = _sentences(text)
    for index, sentence in enumerate(sentences):
        is_question = "?" in str(text) and index == len(sentences) - 1
        if is_question:
            for pattern, predicate in ((_未知型分類, "is a type of"), (_未知単純, "is a")):
                match = pattern.fullmatch(sentence)
                if not match:
                    continue
                target = _norm(match.group("o"))
                requested = _norm(match.groupdict().get("kind") or "") or "選択肢"
                item = 英語分類意味(requested, target, True, requested, predicate)
                if item not in out:
                    out.append(item)
                break
        else:
            for pattern, predicate in ((_型分類, "is a type of"), (_単純分類, "is a")):
                match = pattern.fullmatch(sentence)
                if not match:
                    continue
                subject = _norm(match.group("s"))
                target = _norm(match.group("o"))
                if subject and target and subject.casefold() != target.casefold():
                    item = 英語分類意味(subject, target, False, "", predicate)
                    if item not in out:
                        out.append(item)
                break
    return tuple(out)


__all__ = ["英語分類意味", "英語分類意味抽出"]

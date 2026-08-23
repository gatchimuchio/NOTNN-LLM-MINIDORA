from __future__ import annotations

from dataclasses import dataclass
import re
import unicodedata


@dataclass(frozen=True, slots=True)
class 英語関係構文:
    種別: str
    正規表現: re.Pattern[str]
    反転: bool = False


# 世界知識ではなく、英語という言語体系の基底知識だけを保持する。
# 科学・技術文を含む一般文で頻出する関係語の屈折・派生差を同一概念へ戻す。
_英語基本形表 = {
    # 因果
    "cause": "cause", "causes": "cause", "caused": "cause", "causing": "cause",
    "causal": "cause", "causally": "cause", "causation": "cause",
    "lead": "lead", "leads": "lead", "led": "lead", "leading": "lead",
    "result": "result", "results": "result", "resulted": "result", "resulting": "result",
    # 増加
    "increase": "increase", "increases": "increase", "increased": "increase", "increasing": "increase",
    "raise": "raise", "raises": "raise", "raised": "raise", "raising": "raise",
    "enhance": "enhance", "enhances": "enhance", "enhanced": "enhance", "enhancing": "enhance",
    "enhancement": "enhance", "enhancements": "enhance",
    # 減少
    "decrease": "decrease", "decreases": "decrease", "decreased": "decrease", "decreasing": "decrease",
    "reduce": "reduce", "reduces": "reduce", "reduced": "reduce", "reducing": "reduce",
    "reduction": "reduce", "reductions": "reduce", "reductive": "reduce",
    "lower": "lower", "lowers": "lower", "lowered": "lower", "lowering": "lower",
    # 阻害
    "inhibit": "inhibit", "inhibits": "inhibit", "inhibited": "inhibit", "inhibiting": "inhibit",
    "inhibition": "inhibit", "inhibitions": "inhibit", "inhibitory": "inhibit",
    "suppress": "suppress", "suppresses": "suppress", "suppressed": "suppress", "suppressing": "suppress",
    "suppression": "suppress", "suppressions": "suppress", "suppressive": "suppress",
    "block": "block", "blocks": "block", "blocked": "block", "blocking": "block", "blockage": "block",
    # 活性化
    "activate": "activate", "activates": "activate", "activated": "activate", "activating": "activate",
    "activation": "activate", "activations": "activate",
    "stimulate": "stimulate", "stimulates": "stimulate", "stimulated": "stimulate", "stimulating": "stimulate",
    "stimulation": "stimulate", "stimulations": "stimulate", "stimulatory": "stimulate",
    # 生成
    "produce": "produce", "produces": "produce", "produced": "produce", "producing": "produce",
    "production": "produce", "productions": "produce", "productive": "produce",
    "generate": "generate", "generates": "generate", "generated": "generate", "generating": "generate",
    "generation": "generate", "generations": "generate", "generative": "generate",
    # 要求・依存
    "require": "require", "requires": "require", "required": "require", "requiring": "require",
    "requirement": "require", "requirements": "require",
    "need": "need", "needs": "need", "needed": "need", "needing": "need",
    "depend": "depend", "depends": "depend", "depended": "depend", "depending": "depend",
    "dependent": "depend", "dependence": "depend", "dependency": "depend", "dependencies": "depend",
    # 包含
    "contain": "contain", "contains": "contain", "contained": "contain", "containing": "contain",
    "containment": "contain",
    "include": "include", "includes": "include", "included": "include", "including": "include",
    "inclusion": "include", "inclusions": "include", "inclusive": "include",
    "comprise": "comprise", "comprises": "comprise", "comprised": "comprise", "comprising": "comprise",
    # 使用
    "use": "use", "uses": "use", "used": "use", "using": "use", "usage": "use",
    "utilize": "utilize", "utilizes": "utilize", "utilized": "utilize", "utilizing": "utilize",
    "utilization": "utilize", "utilisation": "utilize",
    "employ": "employ", "employs": "employ", "employed": "employ", "employing": "employ",
    "employment": "employ",
    # 防止
    "prevent": "prevent", "prevents": "prevent", "prevented": "prevent", "preventing": "prevent",
    "prevention": "prevent", "preventive": "prevent", "preventative": "prevent",
    "protect": "protect", "protects": "protect", "protected": "protect", "protecting": "protect",
    "protection": "protect", "protective": "protect",
    # 相関
    "associate": "associate", "associates": "associate", "associated": "associate", "associating": "associate",
    "association": "associate", "associations": "associate",
    "correlate": "correlate", "correlates": "correlate", "correlated": "correlate", "correlating": "correlate",
    "correlation": "correlate", "correlations": "correlate", "correlative": "correlate",
    "relate": "relate", "relates": "relate", "related": "relate", "relating": "relate",
    "relation": "relate", "relations": "relate", "relational": "relate",
}


_英語関係族 = {
    "因果": frozenset({"cause", "lead", "result"}),
    "増加": frozenset({"increase", "raise", "enhance"}),
    "減少": frozenset({"decrease", "reduce", "lower"}),
    "阻害": frozenset({"inhibit", "suppress", "block"}),
    "活性化": frozenset({"activate", "stimulate"}),
    "生成": frozenset({"produce", "generate"}),
    "要求": frozenset({"require", "need", "depend"}),
    "包含": frozenset({"contain", "include", "comprise"}),
    "使用": frozenset({"use", "utilize", "employ"}),
    "防止": frozenset({"prevent", "protect"}),
    "相関": frozenset({"associate", "correlate", "relate"}),
}

_基本形から関係 = {
    lemma: kind
    for kind, lemmas in _英語関係族.items()
    for lemma in lemmas
}


def 英語基本形(word: str) -> str:
    value = unicodedata.normalize("NFKC", str(word)).casefold().strip("._-")
    return _英語基本形表.get(value, value)


def 英語関係概念(word: str) -> str | None:
    return _基本形から関係.get(英語基本形(word))


def 英語関係族() -> dict[str, frozenset[str]]:
    return dict(_英語関係族)


def 英語語形数() -> int:
    return len(_英語基本形表)


_SUBJECT = r"(?P<s>[^?!.;,\n]{1,120}?)"
_OBJECT = r"(?P<o>[^?!.;,\n]{1,120})"
_AUX = r"(?:is|are|was|were|be|been|being|has\s+been|have\s+been|had\s+been)"


def _active(forms: str) -> re.Pattern[str]:
    return re.compile(rf"{_SUBJECT}\s+(?P<v>{forms})\s+{_OBJECT}", re.I)


def _passive(forms: str) -> re.Pattern[str]:
    return re.compile(rf"{_SUBJECT}\s+(?P<v>{_AUX}\s+(?:{forms})\s+by)\s+{_OBJECT}", re.I)


# 高確度の明示構文だけを扱う。名詞共起や近接だけから関係を推定しない。
英語明示関係構文 = (
    英語関係構文("因果", _active(r"cause|causes|caused|causing|lead\s+to|leads\s+to|led\s+to|leading\s+to|result\s+in|results\s+in|resulted\s+in|resulting\s+in")),
    英語関係構文("因果", _passive(r"caused"), True),
    英語関係構文("増加", _active(r"increase|increases|increased|increasing|raise|raises|raised|raising|enhance|enhances|enhanced|enhancing")),
    英語関係構文("増加", _passive(r"increased|raised|enhanced"), True),
    英語関係構文("減少", _active(r"decrease|decreases|decreased|decreasing|reduce|reduces|reduced|reducing|lower|lowers|lowered|lowering")),
    英語関係構文("減少", _passive(r"decreased|reduced|lowered"), True),
    英語関係構文("阻害", _active(r"inhibit|inhibits|inhibited|inhibiting|suppress|suppresses|suppressed|suppressing|block|blocks|blocked|blocking")),
    英語関係構文("阻害", _passive(r"inhibited|suppressed|blocked"), True),
    英語関係構文("活性化", _active(r"activate|activates|activated|activating|stimulate|stimulates|stimulated|stimulating")),
    英語関係構文("活性化", _passive(r"activated|stimulated"), True),
    英語関係構文("生成", _active(r"produce|produces|produced|producing|generate|generates|generated|generating")),
    英語関係構文("生成", _passive(r"produced|generated"), True),
    英語関係構文("要求", _active(r"require|requires|required|requiring|need|needs|needed|needing|depend\s+on|depends\s+on|depended\s+on|depending\s+on")),
    英語関係構文("要求", _passive(r"required|needed"), True),
    英語関係構文("包含", _active(r"contain|contains|contained|containing|include|includes|included|including|comprise|comprises|comprised|comprising")),
    英語関係構文("使用", _active(r"use|uses|used|using|utilize|utilizes|utilized|utilizing|employ|employs|employed|employing")),
    英語関係構文("使用", _passive(r"used|utilized|employed"), True),
    英語関係構文("防止", _active(r"prevent|prevents|prevented|preventing|protect\s+against|protects\s+against|protected\s+against|protecting\s+against|protect\s+from|protects\s+from|protected\s+from|protecting\s+from")),
    英語関係構文("防止", _passive(r"prevented|protected"), True),
    英語関係構文("相関", _active(r"associate\s+with|associates\s+with|associated\s+with|associating\s+with|correlate\s+with|correlates\s+with|correlated\s+with|correlating\s+with|relate\s+to|relates\s+to|related\s+to|relating\s+to")),
)


__all__ = [
    "英語関係構文",
    "英語基本形",
    "英語関係概念",
    "英語関係族",
    "英語語形数",
    "英語明示関係構文",
]

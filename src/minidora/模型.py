from __future__ import annotations

from dataclasses import dataclass, field
from typing import Protocol, Sequence

from .semantic_tokens import 意味語


LLM成立規定リポジトリ = "https://github.com/gatchimuchio/LLM-Constitutive-Specification"
LLM成立規定参照コミット = "e94a13ba32208aabd9dc88b6de320872963725be"
LLM成立規定版 = "2026-08-26-成立規定-2"
LLM成立意味区別 = (
    "独立対象",
    "文脈依存関係",
    "関係再利用",
    "言語対応",
    "局所対応",
)


@dataclass(frozen=True, slots=True)
class 言語状態:
    """外部から観測できる言語体系上の一状態。"""

    内容: str
    言語体系: str = "自然言語:ja"
    識別子: str = ""

    def __post_init__(self) -> None:
        if not self.言語体系.strip():
            raise ValueError("言語体系は空にできない")
        if not isinstance(self.内容, str):
            raise TypeError("言語状態.内容は文字列である必要がある")


@dataclass(frozen=True, slots=True)
class 内部言語状態:
    """言語対応を通した、模型側で比較可能な内部状態。"""

    表層: str
    言語体系: str
    意味語集合: frozenset[str]
    識別子: str = ""


@dataclass(frozen=True, slots=True)
class 文脈付き言語状態:
    現在: 内部言語状態
    履歴: tuple[内部言語状態, ...] = ()
    条件: tuple[str, ...] = ()

    @property
    def 意味語集合(self) -> frozenset[str]:
        out = set(self.現在.意味語集合)
        for state in self.履歴:
            out.update(state.意味語集合)
        for condition in self.条件:
            out.update(意味語(condition))
        return frozenset(out)


@dataclass(frozen=True, slots=True)
class 成立候補:
    候補ID: str
    状態: 言語状態

    def __post_init__(self) -> None:
        if not self.候補ID.strip():
            raise ValueError("候補IDは空にできない")


@dataclass(frozen=True, slots=True)
class 関係寄与:
    関係名: str
    差: int
    根拠: tuple[str, ...] = ()


@dataclass(frozen=True, slots=True)
class 成立差:
    候補ID: str
    差: int
    寄与: tuple[関係寄与, ...] = ()


@dataclass(frozen=True, slots=True)
class 模型結果:
    文脈: 文脈付き言語状態
    候補差: tuple[成立差, ...]
    最有力候補ID: str | None
    同率候補ID: tuple[str, ...] = ()

    def 候補辞書(self) -> dict[str, int]:
        return {item.候補ID: item.差 for item in self.候補差}


class 言語対応:
    """外部言語状態を模型内部で比較可能な状態へ写す境界。

    tokenizer等の特定実装名を正本条件にしない。現行MINIDORAでは既存の
    ``意味語`` を決定論的な内部住所として利用する。
    """

    def 内部化(self, 状態: 言語状態) -> 内部言語状態:
        return 内部言語状態(
            表層=状態.内容,
            言語体系=状態.言語体系,
            意味語集合=意味語(状態.内容),
            識別子=状態.識別子,
        )

    def 文脈化(
        self,
        現在: 言語状態,
        履歴: Sequence[言語状態] = (),
        条件: Sequence[str] = (),
    ) -> 文脈付き言語状態:
        for state in 履歴:
            if state.言語体系 != 現在.言語体系:
                raise ValueError("同一の文脈評価内で言語体系を無言混在させない")
        return 文脈付き言語状態(
            現在=self.内部化(現在),
            履歴=tuple(self.内部化(item) for item in 履歴),
            条件=tuple(str(item) for item in 条件),
        )


class 模型関係(Protocol):
    名称: str

    def 評価(
        self,
        文脈: 文脈付き言語状態,
        候補: 内部言語状態,
    ) -> 関係寄与 | None: ...


@dataclass(frozen=True, slots=True)
class 関係規則:
    """再利用可能な決定論的関係規則。

    文脈と候補の双方に明示された意味差だけを使う。候補IDや正解ラベルを
    根拠にせず、同じ規則を複数状態へ再利用できることを前提とする。
    """

    名称: str
    文脈必須: frozenset[str] = field(default_factory=frozenset)
    候補必須: frozenset[str] = field(default_factory=frozenset)
    文脈禁止: frozenset[str] = field(default_factory=frozenset)
    候補禁止: frozenset[str] = field(default_factory=frozenset)
    差: int = 1
    根拠: tuple[str, ...] = ()

    def 評価(self, 文脈: 文脈付き言語状態, 候補: 内部言語状態) -> 関係寄与 | None:
        context = 文脈.意味語集合
        candidate = 候補.意味語集合
        if not self.文脈必須.issubset(context):
            return None
        if not self.候補必須.issubset(candidate):
            return None
        if self.文脈禁止.intersection(context):
            return None
        if self.候補禁止.intersection(candidate):
            return None
        if not (self.文脈必須 or self.候補必須 or self.文脈禁止 or self.候補禁止):
            return None
        return 関係寄与(self.名称, int(self.差), self.根拠)


@dataclass(frozen=True, slots=True)
class 意味連続関係:
    """共有意味語の連続を最小の汎用関係差として読む。

    これは世界知識を生成しない。明示された文脈と候補の共有差だけを返すため、
    根拠がない候補を勝手に優先しない。
    """

    名称: str = "意味連続"
    関係語重み: int = 2

    def 評価(self, 文脈: 文脈付き言語状態, 候補: 内部言語状態) -> 関係寄与 | None:
        shared = 文脈.意味語集合.intersection(候補.意味語集合)
        if not shared:
            return None
        relation_count = sum(1 for token in shared if token.startswith("rel:"))
        ordinary_count = len(shared) - relation_count
        difference = ordinary_count + relation_count * self.関係語重み
        if difference <= 0:
            return None
        return 関係寄与(
            self.名称,
            difference,
            tuple(f"共有:{token}" for token in sorted(shared)),
        )


class MINIDORA模型核:
    """大規模言語模型成立規定v2に従うMINIDORA v0.4の模型中核。

    確率分布・sampling・特定ニューラル構造を要求せず、文脈付き内部状態から
    候補ごとの成立差を決定論的に形成する。外部参照、HDS、主体Gate、表面化、
    候補生成、計算実行はこのクラスの成立条件へ混入させない。
    """

    def __init__(
        self,
        関係群: Sequence[模型関係] = (),
        *,
        言語対応_: 言語対応 | None = None,
    ) -> None:
        self.言語対応 = 言語対応_ or 言語対応()
        self._関係群: list[模型関係] = list(関係群)

    @property
    def 関係群(self) -> tuple[模型関係, ...]:
        return tuple(self._関係群)

    def 関係登録(self, 関係: 模型関係) -> None:
        if not getattr(関係, "名称", ""):
            raise ValueError("模型関係には名称が必要")
        self._関係群.append(関係)

    def 文脈化(
        self,
        現在: 言語状態,
        履歴: Sequence[言語状態] = (),
        条件: Sequence[str] = (),
    ) -> 文脈付き言語状態:
        return self.言語対応.文脈化(現在, 履歴, 条件)

    def 評価(
        self,
        文脈: 文脈付き言語状態,
        候補群: Sequence[成立候補],
    ) -> 模型結果:
        if not 候補群:
            raise ValueError("成立差の評価には1候補以上が必要")
        ids = [item.候補ID for item in 候補群]
        if len(ids) != len(set(ids)):
            raise ValueError("候補IDは評価内で一意である必要がある")

        differences: list[成立差] = []
        for candidate in 候補群:
            if candidate.状態.言語体系 != 文脈.現在.言語体系:
                raise ValueError("候補と言語文脈の言語体系が一致しない")
            internal = self.言語対応.内部化(candidate.状態)
            contributions: list[関係寄与] = []
            for relation in self._関係群:
                item = relation.評価(文脈, internal)
                if item is not None:
                    contributions.append(item)
            differences.append(
                成立差(
                    candidate.候補ID,
                    sum(item.差 for item in contributions),
                    tuple(contributions),
                )
            )

        maximum = max(item.差 for item in differences)
        top = tuple(item.候補ID for item in differences if item.差 == maximum)
        # 差が生じていない、または同率なら勝手に一候補へ確定しない。
        winner = top[0] if maximum != 0 and len(top) == 1 else None
        return 模型結果(文脈, tuple(differences), winner, top if len(top) > 1 else ())

    def 評価言語状態(
        self,
        現在: 言語状態,
        候補群: Sequence[成立候補],
        *,
        履歴: Sequence[言語状態] = (),
        条件: Sequence[str] = (),
    ) -> 模型結果:
        return self.評価(self.文脈化(現在, 履歴, 条件), 候補群)


def 標準模型核() -> MINIDORA模型核:
    """世界知識を捏造しない最小の標準模型核を返す。

    v0.4では大規模性をこの関数だけから宣言しない。大規模性は上位規定どおり、
    状態域・関係域・共有適用規模を別測定する。
    """

    return MINIDORA模型核((意味連続関係(),))


__all__ = [
    "LLM成立規定リポジトリ",
    "LLM成立規定参照コミット",
    "LLM成立規定版",
    "LLM成立意味区別",
    "言語状態",
    "内部言語状態",
    "文脈付き言語状態",
    "成立候補",
    "関係寄与",
    "成立差",
    "模型結果",
    "言語対応",
    "模型関係",
    "関係規則",
    "意味連続関係",
    "MINIDORA模型核",
    "標準模型核",
]

from __future__ import annotations

from collections import Counter, defaultdict
from dataclasses import dataclass
from fractions import Fraction
import hashlib
import json
import unicodedata
from typing import Iterable, Mapping, Sequence


言語確率法則版 = "v1.0"
BOS記号 = "<BOS>"
EOS記号 = "<EOS>"
UNK記号 = "<UNK>"


def _正規化(text: str) -> str:
    return unicodedata.normalize("NFKC", str(text)).replace("\r\n", "\n").replace("\r", "\n")


def _文脈キー(context: Sequence[str]) -> str:
    return "\u001f".join(context)


def _文脈復元(raw: str) -> tuple[str, ...]:
    return () if raw == "" else tuple(raw.split("\u001f"))


@dataclass(frozen=True, slots=True)
class 言語確率模型状態:
    """MINIDORA厳密LMの持続模型状態。

    `遷移計数` は全てのbackoff文脈を含む。実行時に正規化された確率へ変換する。
    """

    次数: int
    加算平滑化: int
    語彙: tuple[str, ...]
    遷移計数: tuple[tuple[tuple[str, ...], tuple[tuple[str, int], ...]], ...]
    形成文書数: int = 0

    def __post_init__(self) -> None:
        if self.次数 < 1:
            raise ValueError("次数は1以上である必要がある")
        if self.加算平滑化 < 1:
            raise ValueError("加算平滑化は1以上である必要がある")
        if EOS記号 not in self.語彙 or UNK記号 not in self.語彙:
            raise ValueError("語彙にはEOS/UNKが必要")
        if BOS記号 in self.語彙:
            raise ValueError("BOSは出力語彙へ含めない")
        if len(self.語彙) != len(set(self.語彙)):
            raise ValueError("語彙は一意である必要がある")

    def 辞書化(self) -> dict[str, object]:
        return {
            "schema": "minidora.strict-language-model.v1",
            "次数": self.次数,
            "加算平滑化": self.加算平滑化,
            "語彙": list(self.語彙),
            "形成文書数": self.形成文書数,
            "遷移計数": {
                _文脈キー(context): {token: count for token, count in rows}
                for context, rows in self.遷移計数
            },
        }

    @classmethod
    def 復元(cls, data: Mapping[str, object]) -> "言語確率模型状態":
        if data.get("schema") != "minidora.strict-language-model.v1":
            raise ValueError("未知の言語確率模型状態schema")
        raw_counts = data.get("遷移計数")
        if not isinstance(raw_counts, Mapping):
            raise TypeError("遷移計数が不正")
        counts: list[tuple[tuple[str, ...], tuple[tuple[str, int], ...]]] = []
        for raw_context, raw_rows in raw_counts.items():
            if not isinstance(raw_context, str) or not isinstance(raw_rows, Mapping):
                raise TypeError("遷移計数要素が不正")
            rows = tuple(sorted((str(token), int(count)) for token, count in raw_rows.items()))
            counts.append((_文脈復元(raw_context), rows))
        return cls(
            次数=int(data["次数"]),
            加算平滑化=int(data["加算平滑化"]),
            語彙=tuple(str(x) for x in data["語彙"]),
            遷移計数=tuple(sorted(counts, key=lambda row: row[0])),
            形成文書数=int(data.get("形成文書数", 0)),
        )

    @property
    def sha256(self) -> str:
        payload = json.dumps(
            self.辞書化(), ensure_ascii=False, sort_keys=True, separators=(",", ":")
        ).encode("utf-8")
        return hashlib.sha256(payload).hexdigest()


@dataclass(frozen=True, slots=True)
class 条件付き記号分布:
    文脈: tuple[str, ...]
    確率: tuple[tuple[str, Fraction], ...]

    def __post_init__(self) -> None:
        if sum((p for _, p in self.確率), Fraction(0, 1)) != Fraction(1, 1):
            raise ValueError("条件付き分布は厳密に1へ正規化される必要がある")
        if any(p < 0 for _, p in self.確率):
            raise ValueError("負確率は許可しない")

    def 辞書(self) -> dict[str, Fraction]:
        return dict(self.確率)

    def 確率_of(self, 記号: str) -> Fraction:
        return self.辞書().get(記号, Fraction(0, 1))


@dataclass(frozen=True, slots=True)
class 言語確率監査結果:
    合格: bool
    検査文脈数: int
    終端確率下限: Fraction
    理由: tuple[str, ...] = ()


class MINIDORA厳密言語模型:
    """非ニューラル・決定論的な厳密Language Model核。

    形成済みの有限n-gram計数とadditive smoothingから、各prefixに対する
    exact rationalな次記号条件分布を返す。系列確率はchain ruleとEOSで閉じる。
    samplingはこの模型核の責任ではない。
    """

    def __init__(self, 状態: 言語確率模型状態) -> None:
        self.状態 = 状態
        self._語彙 = tuple(状態.語彙)
        self._語彙集合 = frozenset(self._語彙)
        self._counts: dict[tuple[str, ...], dict[str, int]] = {
            context: dict(rows) for context, rows in 状態.遷移計数
        }

    @classmethod
    def 形成(
        cls,
        文書群: Iterable[str] = (),
        *,
        次数: int = 3,
        加算平滑化: int = 1,
    ) -> "MINIDORA厳密言語模型":
        if 次数 < 1:
            raise ValueError("次数は1以上である必要がある")
        if 加算平滑化 < 1:
            raise ValueError("加算平滑化は1以上である必要がある")

        docs = tuple(_正規化(text) for text in 文書群)
        observed = {char for text in docs for char in text}
        vocabulary = tuple(sorted((*observed, UNK記号, EOS記号)))
        counts: dict[tuple[str, ...], Counter[str]] = defaultdict(Counter)

        for text in docs:
            history: list[str] = [BOS記号] * max(0, 次数 - 1)
            for token in (*tuple(text), EOS記号):
                for width in range(0, 次数):
                    context = tuple(history[-width:]) if width else ()
                    counts[context][token] += 1
                history.append(token)

        frozen_counts = tuple(
            (context, tuple(sorted(counter.items())))
            for context, counter in sorted(counts.items(), key=lambda row: row[0])
        )
        return cls(
            言語確率模型状態(
                次数=次数,
                加算平滑化=加算平滑化,
                語彙=vocabulary,
                遷移計数=frozen_counts,
                形成文書数=len(docs),
            )
        )

    @classmethod
    def 復元(cls, data: Mapping[str, object]) -> "MINIDORA厳密言語模型":
        return cls(言語確率模型状態.復元(data))

    def 辞書化(self) -> dict[str, object]:
        return self.状態.辞書化()

    @property
    def 状態sha256(self) -> str:
        return self.状態.sha256

    def _符号化(self, text: str) -> tuple[str, ...]:
        normalized = _正規化(text)
        return tuple(char if char in self._語彙集合 else UNK記号 for char in normalized)

    def _有効文脈(self, history: Sequence[str]) -> tuple[str, ...]:
        padded = [BOS記号] * max(0, self.状態.次数 - 1) + list(history)
        for width in range(self.状態.次数 - 1, -1, -1):
            context = tuple(padded[-width:]) if width else ()
            if context in self._counts:
                return context
        return ()

    def _分布_for_context(self, context: tuple[str, ...]) -> 条件付き記号分布:
        raw = self._counts.get(context, {})
        alpha = self.状態.加算平滑化
        denominator = sum(raw.values()) + alpha * len(self._語彙)
        probabilities = tuple(
            (token, Fraction(raw.get(token, 0) + alpha, denominator))
            for token in self._語彙
        )
        return 条件付き記号分布(context, probabilities)

    def _分布_for_history(self, history: Sequence[str]) -> 条件付き記号分布:
        return self._分布_for_context(self._有効文脈(history))

    def 次記号分布(self, 接頭辞: str = "") -> 条件付き記号分布:
        return self._分布_for_history(self._符号化(接頭辞))

    def 系列確率(self, text: str) -> Fraction:
        history: list[str] = []
        probability = Fraction(1, 1)
        for token in (*self._符号化(text), EOS記号):
            dist = self._分布_for_history(history)
            probability *= dist.確率_of(token)
            history.append(token)
        return probability

    def 条件付き系列確率(self, 接頭辞: str, 続き: str) -> Fraction:
        history = list(self._符号化(接頭辞))
        probability = Fraction(1, 1)
        for token in (*self._符号化(続き), EOS記号):
            dist = self._分布_for_history(history)
            probability *= dist.確率_of(token)
            history.append(token)
        return probability

    def 最尤次記号(self, 接頭辞: str = "") -> str:
        dist = self.次記号分布(接頭辞)
        # 同率時は語彙順で決定し、samplingを持ち込まない。
        return max(dist.確率, key=lambda row: (row[1], -self._語彙.index(row[0])))[0]

    def 正規化監査(self) -> 言語確率監査結果:
        contexts = tuple(self._counts) or ((),)
        reasons: list[str] = []
        eos_values: list[Fraction] = []
        for context in contexts:
            dist = self._分布_for_context(context)
            total = sum((p for _, p in dist.確率), Fraction(0, 1))
            if total != Fraction(1, 1):
                reasons.append(f"非正規化:{context!r}:{total}")
            eos = dist.確率_of(EOS記号)
            if eos <= 0:
                reasons.append(f"EOS非正:{context!r}")
            eos_values.append(eos)
        lower = min(eos_values, default=Fraction(0, 1))
        if lower <= 0:
            reasons.append("終端確率下限が正ではない")
        return 言語確率監査結果(not reasons, len(contexts), lower, tuple(reasons))


def 最小厳密言語模型() -> MINIDORA厳密言語模型:
    """世界知識を埋め込まない最小基底LM。

    空の形成資料でもadditive priorによりUNK/EOS上の厳密確率法則を持つ。
    能力の高さやLarge呼称を意味しない。
    """

    return MINIDORA厳密言語模型.形成((), 次数=3, 加算平滑化=1)


__all__ = [
    "言語確率法則版", "BOS記号", "EOS記号", "UNK記号",
    "言語確率模型状態", "条件付き記号分布", "言語確率監査結果",
    "MINIDORA厳密言語模型", "最小厳密言語模型",
]

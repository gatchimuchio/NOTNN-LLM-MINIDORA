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
    """MINIDORA厳密LMの持続模型状態。"""

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
        if self.形成文書数 < 0:
            raise ValueError("形成文書数は0以上である必要がある")
        if EOS記号 not in self.語彙 or UNK記号 not in self.語彙:
            raise ValueError("語彙にはEOS/UNKが必要")
        if BOS記号 in self.語彙:
            raise ValueError("BOSは出力語彙へ含めない")
        if len(self.語彙) != len(set(self.語彙)):
            raise ValueError("語彙は一意である必要がある")

        vocabulary = frozenset(self.語彙)
        contexts: set[tuple[str, ...]] = set()
        for context, rows in self.遷移計数:
            if context in contexts:
                raise ValueError("遷移計数の文脈は一意である必要がある")
            contexts.add(context)
            if len(context) >= self.次数:
                raise ValueError("遷移計数の文脈長は次数未満である必要がある")
            if any(token != BOS記号 and token not in vocabulary for token in context):
                raise ValueError("遷移計数の文脈に語彙外記号がある")
            seen_tokens: set[str] = set()
            for token, count in rows:
                if token in seen_tokens:
                    raise ValueError("同一文脈内の遷移記号は一意である必要がある")
                seen_tokens.add(token)
                if token not in vocabulary:
                    raise ValueError("遷移計数に語彙外記号がある")
                if count <= 0:
                    raise ValueError("遷移計数は正整数である必要がある")

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
        for token, probability in self.確率:
            if token == 記号:
                return probability
        return Fraction(0, 1)


@dataclass(frozen=True, slots=True)
class 言語確率監査結果:
    合格: bool
    検査文脈数: int
    終端確率下限: Fraction
    理由: tuple[str, ...] = ()


class MINIDORA厳密言語模型:
    """非ニューラル・決定論的な厳密Language Model核。"""

    def __init__(self, 状態: 言語確率模型状態) -> None:
        self.状態 = 状態
        self._語彙 = tuple(状態.語彙)
        self._語彙集合 = frozenset(self._語彙)
        self._counts: dict[tuple[str, ...], dict[str, int]] = {
            context: dict(rows) for context, rows in 状態.遷移計数
        }

    @staticmethod
    def _形成へ追加(
        text: str,
        *,
        次数: int,
        observed: set[str],
        counts: dict[tuple[str, ...], Counter[str]],
    ) -> None:
        normalized = _正規化(text)
        observed.update(normalized)
        max_history = max(0, 次数 - 1)
        history: tuple[str, ...] = (BOS記号,) * max_history
        for token in (*normalized, EOS記号):
            for width in range(次数):
                context = history[-width:] if width else ()
                counts[context][token] += 1
            if max_history:
                history = (*history, token)[-max_history:]

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

        observed: set[str] = set()
        counts: dict[tuple[str, ...], Counter[str]] = defaultdict(Counter)
        document_count = 0
        for text in 文書群:
            cls._形成へ追加(str(text), 次数=次数, observed=observed, counts=counts)
            document_count += 1

        vocabulary = tuple(sorted((*observed, UNK記号, EOS記号)))
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
                形成文書数=document_count,
            )
        )

    def 追加形成(self, 文書群: Iterable[str]) -> "MINIDORA厳密言語模型":
        """現在状態だけを基点にDataを増分形成し、新しい模型を返す。"""
        observed = set(self._語彙) - {UNK記号, EOS記号}
        counts: dict[tuple[str, ...], Counter[str]] = defaultdict(Counter)
        for context, rows in self.状態.遷移計数:
            counts[context].update(dict(rows))
        document_count = self.状態.形成文書数
        for text in 文書群:
            self._形成へ追加(str(text), 次数=self.状態.次数, observed=observed, counts=counts)
            document_count += 1
        vocabulary = tuple(sorted((*observed, UNK記号, EOS記号)))
        frozen_counts = tuple(
            (context, tuple(sorted(counter.items())))
            for context, counter in sorted(counts.items(), key=lambda row: row[0])
        )
        return type(self)(
            言語確率模型状態(
                次数=self.状態.次数,
                加算平滑化=self.状態.加算平滑化,
                語彙=vocabulary,
                遷移計数=frozen_counts,
                形成文書数=document_count,
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
        max_history = max(0, self.状態.次数 - 1)
        tail = tuple(history[-max_history:]) if max_history else ()
        padded = (BOS記号,) * max(0, max_history - len(tail)) + tail
        for width in range(max_history, -1, -1):
            context = padded[-width:] if width else ()
            if context in self._counts:
                return context
        return ()

    def _分母(self, context: tuple[str, ...]) -> tuple[dict[str, int], int, int]:
        raw = self._counts.get(context, {})
        alpha = self.状態.加算平滑化
        denominator = sum(raw.values()) + alpha * len(self._語彙)
        return raw, alpha, denominator

    def _確率_for_context(self, context: tuple[str, ...], token: str) -> Fraction:
        raw, alpha, denominator = self._分母(context)
        return Fraction(raw.get(token, 0) + alpha, denominator)

    def _分布_for_context(self, context: tuple[str, ...]) -> 条件付き記号分布:
        raw, alpha, denominator = self._分母(context)
        probabilities = tuple(
            (token, Fraction(raw.get(token, 0) + alpha, denominator))
            for token in self._語彙
        )
        return 条件付き記号分布(context, probabilities)

    def _分布_for_history(self, history: Sequence[str]) -> 条件付き記号分布:
        return self._分布_for_context(self._有効文脈(history))

    def _確率_for_history(self, history: Sequence[str], token: str) -> Fraction:
        return self._確率_for_context(self._有効文脈(history), token)

    def 次記号分布(self, 接頭辞: str = "") -> 条件付き記号分布:
        return self._分布_for_history(self._符号化(接頭辞))

    def _系列確率(self, history: tuple[str, ...], tokens: Sequence[str]) -> Fraction:
        probability = Fraction(1, 1)
        max_history = max(0, self.状態.次数 - 1)
        for token in (*tokens, EOS記号):
            probability *= self._確率_for_history(history, token)
            if max_history:
                history = (*history, token)[-max_history:]
        return probability

    def 系列確率(self, text: str) -> Fraction:
        return self._系列確率((), self._符号化(text))

    def 条件付き系列確率(self, 接頭辞: str, 続き: str) -> Fraction:
        max_history = max(0, self.状態.次数 - 1)
        encoded_prefix = self._符号化(接頭辞)
        history = encoded_prefix[-max_history:] if max_history else ()
        return self._系列確率(history, self._符号化(続き))

    def 最尤次記号(self, 接頭辞: str = "") -> str:
        dist = self.次記号分布(接頭辞)
        # maxは同率時に最初の要素を保持する。分布自体が語彙順なので決定論性を維持する。
        return max(dist.確率, key=lambda row: row[1])[0]

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
    return MINIDORA厳密言語模型.形成((), 次数=3, 加算平滑化=1)


__all__ = [
    "言語確率法則版", "BOS記号", "EOS記号", "UNK記号",
    "言語確率模型状態", "条件付き記号分布", "言語確率監査結果",
    "MINIDORA厳密言語模型", "最小厳密言語模型",
]

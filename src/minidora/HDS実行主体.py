from __future__ import annotations

from dataclasses import dataclass, fields, is_dataclass
from enum import StrEnum
from hashlib import sha256
import json
from typing import Any, Callable, Protocol, Sequence


HDS実行主体版 = "HDS-FIRST-CORE-v1"


def _正規化(value: object) -> object:
    """状態署名用の決定論的なJSON互換表現へ落とす。

    未知objectは実行主体の意味正本へ昇格させず、型名とreprだけを監査署名へ使う。
    """
    if value is None or isinstance(value, (str, int, float, bool)):
        return value
    if isinstance(value, dict):
        return {
            str(key): _正規化(item)
            for key, item in sorted(value.items(), key=lambda row: str(row[0]))
        }
    if isinstance(value, (tuple, list)):
        return [_正規化(item) for item in value]
    if isinstance(value, (set, frozenset)):
        return sorted((_正規化(item) for item in value), key=repr)
    if isinstance(value, StrEnum):
        return value.value
    if is_dataclass(value) and not isinstance(value, type):
        return {
            item.name: _正規化(getattr(value, item.name))
            for item in fields(value)
        }
    return {"型": type(value).__qualname__, "表現": repr(value)}


def _署名(value: object) -> str:
    payload = json.dumps(
        _正規化(value),
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
    return sha256(payload).hexdigest()


class HDS終端(StrEnum):
    実行中 = "RUNNING"
    採用 = "COMMIT"
    保留 = "SUSPEND"
    失敗 = "FAIL"


class HDS作用状態(StrEnum):
    成立 = "成立"
    保留 = "保留"
    失敗 = "失敗"
    非適用 = "非適用"


@dataclass(frozen=True, slots=True)
class HDS実行状態:
    """HDS-first coreが所有する最小作業状態。

    K3、候補得点、GPQA、製品能力型には依存しない。既存部品は作用Adapterを介して
    この状態へ成果・残差・成立状態を帰還させる。
    """

    目的: tuple[str, ...] = ()
    要求状態: frozenset[str] = frozenset()
    成立状態: frozenset[str] = frozenset()
    残差: frozenset[str] = frozenset()
    成果: tuple[tuple[str, object], ...] = ()
    主体状態: tuple[tuple[str, object], ...] = ()
    版: int = 0

    def __post_init__(self) -> None:
        if self.版 < 0:
            raise ValueError("HDS実行状態の版は0以上である必要がある")
        成果名 = [name for name, _ in self.成果]
        if len(成果名) != len(set(成果名)):
            raise ValueError("HDS実行状態の成果名は一意である必要がある")
        主体名 = [name for name, _ in self.主体状態]
        if len(主体名) != len(set(主体名)):
            raise ValueError("HDS実行状態の主体状態名は一意である必要がある")

    @property
    def 未達状態(self) -> frozenset[str]:
        return frozenset(self.要求状態.difference(self.成立状態))

    @property
    def 閉包済み(self) -> bool:
        return not self.未達状態 and not self.残差

    @property
    def 状態署名(self) -> str:
        return _署名((
            self.目的,
            tuple(sorted(self.要求状態)),
            tuple(sorted(self.成立状態)),
            tuple(sorted(self.残差)),
            self.成果,
            self.主体状態,
        ))

    def 成果辞書(self) -> dict[str, object]:
        return dict(self.成果)

    def 主体辞書(self) -> dict[str, object]:
        return dict(self.主体状態)


@dataclass(frozen=True, slots=True)
class HDS状態差:
    前状態署名: str
    後状態署名: str
    追加状態: tuple[str, ...] = ()
    削除状態: tuple[str, ...] = ()
    解消残差: tuple[str, ...] = ()
    追加残差: tuple[str, ...] = ()
    変更成果: tuple[str, ...] = ()
    変更主体状態: tuple[str, ...] = ()

    @property
    def 変化有無(self) -> bool:
        return self.前状態署名 != self.後状態署名


@dataclass(frozen=True, slots=True)
class HDS作用機会:
    作用ID: str
    作用入力署名: str
    入力状態: frozenset[str] = frozenset()
    出力状態: frozenset[str] = frozenset()
    解消対象: frozenset[str] = frozenset()
    資源負荷: int = 1
    優先度: float = 0.0
    状態変更可能: bool = True
    根拠: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        if not self.作用ID:
            raise ValueError("HDS作用IDは空にできない")
        if not self.作用入力署名:
            raise ValueError("HDS作用入力署名は空にできない")
        if self.資源負荷 < 0:
            raise ValueError("HDS作用の資源負荷は0以上である必要がある")


@dataclass(frozen=True, slots=True)
class HDS作用結果:
    状態: HDS作用状態
    追加状態: frozenset[str] = frozenset()
    削除状態: frozenset[str] = frozenset()
    解消残差: frozenset[str] = frozenset()
    追加残差: frozenset[str] = frozenset()
    成果: tuple[tuple[str, object], ...] = ()
    主体状態差分: tuple[tuple[str, object], ...] = ()
    理由: tuple[str, ...] = ()
    停止要求: bool = False

    def __post_init__(self) -> None:
        names = [name for name, _ in self.成果]
        if len(names) != len(set(names)):
            raise ValueError("HDS作用結果の成果名は一意である必要がある")
        subject_names = [name for name, _ in self.主体状態差分]
        if len(subject_names) != len(set(subject_names)):
            raise ValueError("HDS作用結果の主体状態名は一意である必要がある")


@dataclass(frozen=True, slots=True)
class HDS作用記録:
    番号: int
    作用ID: str
    作用入力署名: str
    作用状態: HDS作用状態
    前状態署名: str
    後状態署名: str
    状態差: HDS状態差
    対象残差: tuple[str, ...]
    対象未達状態: tuple[str, ...]
    理由: tuple[str, ...] = ()


@dataclass(frozen=True, slots=True)
class HDS実行結果:
    終端: HDS終端
    状態: HDS実行状態
    履歴: tuple[HDS作用記録, ...]
    理由: tuple[str, ...] = ()


class HDS作用器(Protocol):
    作用ID: str

    def 機会(self, 状態: HDS実行状態) -> HDS作用機会 | None: ...

    def 実行(self, 状態: HDS実行状態) -> HDS作用結果: ...


class 標準HDS作用選択器:
    """残差と未達状態を主語に、次に実行する既存作用を選ぶ。

    能力得点や回答ラベルを勝者選択へ流用しない。直接解消できる残差/未達状態を
    最優先し、同率では作用側が宣言した優先度、資源負荷、作用IDだけで決定する。
    中間状態を作る作用も、他に直接進展する作用が無い場合は候補に残す。
    """

    def 選択(
        self,
        状態: HDS実行状態,
        機会群: Sequence[HDS作用機会],
        履歴: Sequence[HDS作用記録] = (),
    ) -> HDS作用機会 | None:
        used = {(item.作用ID, item.作用入力署名) for item in 履歴}
        rows: list[tuple[int, float, float, int, str, HDS作用機会]] = []
        for offer in 機会群:
            if not offer.状態変更可能:
                continue
            if not offer.入力状態.issubset(状態.成立状態):
                continue
            if (offer.作用ID, offer.作用入力署名) in used:
                continue
            residual_coverage = len(状態.残差.intersection(offer.解消対象))
            state_coverage = len(状態.未達状態.intersection(offer.出力状態))
            direct = residual_coverage + state_coverage
            specificity = (
                direct / max(1, len(offer.解消対象) + len(offer.出力状態))
                if direct else 0.0
            )
            rows.append((
                direct,
                specificity,
                float(offer.優先度),
                max(0, int(offer.資源負荷)),
                offer.作用ID,
                offer,
            ))
        if not rows:
            return None
        rows.sort(key=lambda row: (-row[0], -row[1], -row[2], row[3], row[4]))
        return rows[0][-1]


class HDS関数作用:
    """既存の決定論的部品をHDS作用へ接続する薄いAdapter。"""

    def __init__(
        self,
        作用ID: str,
        実行関数: Callable[[HDS実行状態], HDS作用結果],
        *,
        入力状態: Sequence[str] = (),
        出力状態: Sequence[str] = (),
        解消対象: Sequence[str] = (),
        資源負荷: int = 1,
        優先度: float = 0.0,
        根拠: Sequence[str] = (),
        機会判定: Callable[[HDS実行状態], bool] | None = None,
        入力署名: Callable[[HDS実行状態], str] | None = None,
    ) -> None:
        if not 作用ID:
            raise ValueError("作用IDは空にできない")
        self.作用ID = 作用ID
        self._実行関数 = 実行関数
        self._入力状態 = frozenset(str(x) for x in 入力状態)
        self._出力状態 = frozenset(str(x) for x in 出力状態)
        self._解消対象 = frozenset(str(x) for x in 解消対象)
        self._資源負荷 = int(資源負荷)
        self._優先度 = float(優先度)
        self._根拠 = tuple(str(x) for x in 根拠)
        self._機会判定 = 機会判定
        self._入力署名 = 入力署名

    def 機会(self, 状態: HDS実行状態) -> HDS作用機会 | None:
        if self._機会判定 is not None and not bool(self._機会判定(状態)):
            return None
        signature = self._入力署名(状態) if self._入力署名 is not None else 状態.状態署名
        return HDS作用機会(
            self.作用ID,
            str(signature),
            self._入力状態,
            self._出力状態,
            self._解消対象,
            self._資源負荷,
            self._優先度,
            True,
            self._根拠,
        )

    def 実行(self, 状態: HDS実行状態) -> HDS作用結果:
        result = self._実行関数(状態)
        if not isinstance(result, HDS作用結果):
            raise TypeError("HDS作用の実行関数はHDS作用結果を返す必要がある")
        return result


class HDS実行主体:
    """MINIDORA内部で制御権・状態所有権・採否権・再作用権を持つHDS主体。"""

    def __init__(
        self,
        作用群: Sequence[HDS作用器],
        *,
        作用選択器: 標準HDS作用選択器 | None = None,
        最大作用回数: int = 32,
    ) -> None:
        if not 1 <= int(最大作用回数) <= 4096:
            raise ValueError("HDS最大作用回数は1..4096である必要がある")
        actions = tuple(作用群)
        ids = [str(item.作用ID) for item in actions]
        if len(ids) != len(set(ids)):
            raise ValueError("HDS作用IDは実行主体内で一意である必要がある")
        self.作用群 = actions
        self.作用選択器 = 作用選択器 or 標準HDS作用選択器()
        self.最大作用回数 = int(最大作用回数)

    @staticmethod
    def _状態更新(前: HDS実行状態, result: HDS作用結果) -> tuple[HDS実行状態, HDS状態差]:
        states = set(前.成立状態)
        states.difference_update(result.削除状態)
        states.update(result.追加状態)

        residuals = set(前.残差)
        residuals.difference_update(result.解消残差)
        residuals.update(result.追加残差)

        outputs = 前.成果辞書()
        outputs.update(dict(result.成果))
        subject = 前.主体辞書()
        subject.update(dict(result.主体状態差分))

        provisional = HDS実行状態(
            前.目的,
            前.要求状態,
            frozenset(states),
            frozenset(residuals),
            tuple(sorted(outputs.items(), key=lambda row: row[0])),
            tuple(sorted(subject.items(), key=lambda row: row[0])),
            前.版,
        )
        changed = provisional.状態署名 != 前.状態署名
        後 = HDS実行状態(
            provisional.目的,
            provisional.要求状態,
            provisional.成立状態,
            provisional.残差,
            provisional.成果,
            provisional.主体状態,
            前.版 + 1 if changed else 前.版,
        )

        before_outputs = 前.成果辞書()
        after_outputs = 後.成果辞書()
        changed_outputs = tuple(sorted(
            key for key in set(before_outputs) | set(after_outputs)
            if _正規化(before_outputs.get(key)) != _正規化(after_outputs.get(key))
        ))
        before_subject = 前.主体辞書()
        after_subject = 後.主体辞書()
        changed_subject = tuple(sorted(
            key for key in set(before_subject) | set(after_subject)
            if _正規化(before_subject.get(key)) != _正規化(after_subject.get(key))
        ))
        delta = HDS状態差(
            前.状態署名,
            後.状態署名,
            tuple(sorted(後.成立状態 - 前.成立状態)),
            tuple(sorted(前.成立状態 - 後.成立状態)),
            tuple(sorted(前.残差 - 後.残差)),
            tuple(sorted(後.残差 - 前.残差)),
            changed_outputs,
            changed_subject,
        )
        return 後, delta

    def 実行(self, 初期状態: HDS実行状態) -> HDS実行結果:
        if not isinstance(初期状態, HDS実行状態):
            raise TypeError("HDS実行主体にはHDS実行状態が必要")
        current = 初期状態
        history: list[HDS作用記録] = []

        for 番号 in range(1, self.最大作用回数 + 1):
            if current.閉包済み:
                return HDS実行結果(
                    HDS終端.採用,
                    current,
                    tuple(history),
                    ("HDS_GOAL_CLOSED",),
                )

            offers: list[HDS作用機会] = []
            by_id: dict[str, HDS作用器] = {}
            for action in self.作用群:
                offer = action.機会(current)
                if offer is None:
                    continue
                if offer.作用ID != action.作用ID:
                    raise ValueError("HDS作用器と作用機会の作用IDが一致しない")
                offers.append(offer)
                by_id[offer.作用ID] = action

            selected = self.作用選択器.選択(current, tuple(offers), tuple(history))
            if selected is None:
                return HDS実行結果(
                    HDS終端.保留,
                    current,
                    tuple(history),
                    ("HDS_NO_PRODUCTIVE_ACTION",),
                )

            before = current
            result = by_id[selected.作用ID].実行(before)
            current, delta = self._状態更新(before, result)
            record = HDS作用記録(
                番号,
                selected.作用ID,
                selected.作用入力署名,
                result.状態,
                before.状態署名,
                current.状態署名,
                delta,
                tuple(sorted(before.残差.intersection(selected.解消対象))),
                tuple(sorted(before.未達状態.intersection(selected.出力状態))),
                tuple(result.理由),
            )
            history.append(record)

            if result.停止要求:
                terminal = HDS終端.失敗 if result.状態 == HDS作用状態.失敗 else HDS終端.保留
                return HDS実行結果(
                    terminal,
                    current,
                    tuple(history),
                    tuple(dict.fromkeys(("HDS_ACTION_REQUESTED_STOP", *result.理由))),
                )

        if current.閉包済み:
            return HDS実行結果(HDS終端.採用, current, tuple(history), ("HDS_GOAL_CLOSED",))
        return HDS実行結果(
            HDS終端.保留,
            current,
            tuple(history),
            ("HDS_ACTION_BUDGET_EXHAUSTED",),
        )


__all__ = [
    "HDS実行主体版",
    "HDS終端",
    "HDS作用状態",
    "HDS実行状態",
    "HDS状態差",
    "HDS作用機会",
    "HDS作用結果",
    "HDS作用記録",
    "HDS実行結果",
    "HDS作用器",
    "標準HDS作用選択器",
    "HDS関数作用",
    "HDS実行主体",
]

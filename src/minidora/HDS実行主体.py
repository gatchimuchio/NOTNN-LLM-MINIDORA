from __future__ import annotations

from dataclasses import dataclass, fields, is_dataclass
from enum import StrEnum
from hashlib import sha256
import json
import math
from typing import Callable, Protocol, Sequence


HDS実行主体版 = "HDS実行主体-v1"


def _正規化(値: object) -> object:
    """状態署名用の決定論的なJSON互換表現へ落とす。

    未知objectは実行主体の意味正本へ昇格させず、型名とreprだけを監査署名へ使う。
    """
    if 値 is None or isinstance(値, (str, int, float, bool)):
        return 値
    if isinstance(値, dict):
        return {
            str(鍵): _正規化(要素)
            for 鍵, 要素 in sorted(値.items(), key=lambda 行: str(行[0]))
        }
    if isinstance(値, (tuple, list)):
        return [_正規化(要素) for 要素 in 値]
    if isinstance(値, (set, frozenset)):
        return sorted((_正規化(要素) for 要素 in 値), key=repr)
    if isinstance(値, StrEnum):
        return 値.value
    if is_dataclass(値) and not isinstance(値, type):
        return {
            項目.name: _正規化(getattr(値, 項目.name))
            for 項目 in fields(値)
        }
    return {"型": type(値).__qualname__, "表現": repr(値)}


def _署名(値: object) -> str:
    符号列 = json.dumps(
        _正規化(値),
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
    return sha256(符号列).hexdigest()


def _文字集合を検査(名前: str, 値: frozenset[str]) -> None:
    if not isinstance(値, frozenset):
        raise TypeError(f"{名前}はfrozensetである必要がある")
    if any(not isinstance(要素, str) or not 要素.strip() for 要素 in 値):
        raise ValueError(f"{名前}は空でない文字列だけを持つ必要がある")


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
    """HDS駆動コアが所有する最小作業状態。

    K3、候補得点、GPQA、製品能力型には依存しない。既存部品は作用適合器を介して
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
        if type(self.版) is not int or self.版 < 0:
            raise ValueError("HDS実行状態の版は0以上の整数である必要がある")
        if not isinstance(self.目的, tuple) or any(not isinstance(項目, str) or not 項目.strip() for 項目 in self.目的):
            raise ValueError("HDS実行状態の目的は空でない文字列tupleである必要がある")
        _文字集合を検査("要求状態", self.要求状態)
        _文字集合を検査("成立状態", self.成立状態)
        _文字集合を検査("残差", self.残差)
        if not isinstance(self.成果, tuple):
            raise TypeError("HDS実行状態の成果はtupleである必要がある")
        成果名 = [名前 for 名前, _ in self.成果]
        if any(not isinstance(名前, str) or not 名前.strip() for 名前 in 成果名):
            raise ValueError("HDS実行状態の成果名は空でない文字列である必要がある")
        if len(成果名) != len(set(成果名)):
            raise ValueError("HDS実行状態の成果名は一意である必要がある")
        if not isinstance(self.主体状態, tuple):
            raise TypeError("HDS実行状態の主体状態はtupleである必要がある")
        主体名群 = [名前 for 名前, _ in self.主体状態]
        if any(not isinstance(名前, str) or not 名前.strip() for 名前 in 主体名群):
            raise ValueError("HDS実行状態の主体状態名は空でない文字列である必要がある")
        if len(主体名群) != len(set(主体名群)):
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
        if not isinstance(self.作用ID, str) or not self.作用ID.strip():
            raise ValueError("HDS作用IDは空にできない")
        if not isinstance(self.作用入力署名, str) or not self.作用入力署名.strip():
            raise ValueError("HDS作用入力署名は空にできない")
        _文字集合を検査("作用入力状態", self.入力状態)
        _文字集合を検査("作用出力状態", self.出力状態)
        _文字集合を検査("作用解消対象", self.解消対象)
        if type(self.資源負荷) is not int or self.資源負荷 < 0:
            raise ValueError("HDS作用の資源負荷は0以上の整数である必要がある")
        if type(self.優先度) not in (int, float) or not math.isfinite(float(self.優先度)):
            raise ValueError("HDS作用の優先度は有限数である必要がある")
        if type(self.状態変更可能) is not bool:
            raise TypeError("HDS作用の状態変更可能はboolである必要がある")
        if not isinstance(self.根拠, tuple) or any(not isinstance(項目, str) for 項目 in self.根拠):
            raise TypeError("HDS作用の根拠は文字列tupleである必要がある")


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
        if not isinstance(self.状態, HDS作用状態):
            raise TypeError("HDS作用結果の状態型が不正")
        _文字集合を検査("追加状態", self.追加状態)
        _文字集合を検査("削除状態", self.削除状態)
        _文字集合を検査("解消残差", self.解消残差)
        _文字集合を検査("追加残差", self.追加残差)
        if self.追加状態.intersection(self.削除状態):
            raise ValueError("同じ成立状態を一作用で追加・削除できない")
        if self.解消残差.intersection(self.追加残差):
            raise ValueError("同じ残差を一作用で解消・再追加できない")
        if not isinstance(self.成果, tuple):
            raise TypeError("HDS作用結果の成果はtupleである必要がある")
        成果名 = [名前 for 名前, _ in self.成果]
        if any(not isinstance(名前, str) or not 名前.strip() for 名前 in 成果名):
            raise ValueError("HDS作用結果の成果名は空でない文字列である必要がある")
        if len(成果名) != len(set(成果名)):
            raise ValueError("HDS作用結果の成果名は一意である必要がある")
        if not isinstance(self.主体状態差分, tuple):
            raise TypeError("HDS作用結果の主体状態差分はtupleである必要がある")
        主体名群 = [名前 for 名前, _ in self.主体状態差分]
        if any(not isinstance(名前, str) or not 名前.strip() for 名前 in 主体名群):
            raise ValueError("HDS作用結果の主体状態名は空でない文字列である必要がある")
        if len(主体名群) != len(set(主体名群)):
            raise ValueError("HDS作用結果の主体状態名は一意である必要がある")
        if not isinstance(self.理由, tuple) or any(not isinstance(項目, str) for 項目 in self.理由):
            raise TypeError("HDS作用結果の理由は文字列tupleである必要がある")
        if type(self.停止要求) is not bool:
            raise TypeError("HDS作用結果の停止要求はboolである必要がある")


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
        使用済み = {(項目.作用ID, 項目.作用入力署名) for 項目 in 履歴}
        候補列: list[tuple[int, float, float, int, str, HDS作用機会]] = []
        for 機会 in 機会群:
            if not 機会.状態変更可能:
                continue
            if not 機会.入力状態.issubset(状態.成立状態):
                continue
            if (機会.作用ID, 機会.作用入力署名) in 使用済み:
                continue
            残差被覆 = len(状態.残差.intersection(機会.解消対象))
            状態被覆 = len(状態.未達状態.intersection(機会.出力状態))
            直接被覆 = 残差被覆 + 状態被覆
            特異度 = (
                直接被覆 / max(1, len(機会.解消対象) + len(機会.出力状態))
                if 直接被覆 else 0.0
            )
            候補列.append((
                直接被覆,
                特異度,
                float(機会.優先度),
                max(0, int(機会.資源負荷)),
                機会.作用ID,
                機会,
            ))
        if not 候補列:
            return None
        候補列.sort(key=lambda 行: (-行[0], -行[1], -行[2], 行[3], 行[4]))
        return 候補列[0][-1]


class HDS関数作用:
    """既存の決定論的部品をHDS作用へ接続する薄い適合器。"""

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
        署名 = self._入力署名(状態) if self._入力署名 is not None else 状態.状態署名
        return HDS作用機会(
            self.作用ID,
            str(署名),
            self._入力状態,
            self._出力状態,
            self._解消対象,
            self._資源負荷,
            self._優先度,
            True,
            self._根拠,
        )

    def 実行(self, 状態: HDS実行状態) -> HDS作用結果:
        結果 = self._実行関数(状態)
        if not isinstance(結果, HDS作用結果):
            raise TypeError("HDS作用の実行関数はHDS作用結果を返す必要がある")
        return 結果


class HDS実行主体:
    """MINIDORA内部で制御権・状態所有権・採否権・再作用権を持つHDS主体。"""

    def __init__(
        self,
        作用群: Sequence[HDS作用器],
        *,
        作用選択器: 標準HDS作用選択器 | None = None,
        最大作用回数: int = 32,
    ) -> None:
        if type(最大作用回数) is not int or not 1 <= 最大作用回数 <= 4096:
            raise ValueError("HDS最大作用回数は1..4096の整数である必要がある")
        固定作用群 = tuple(作用群)
        作用ID群 = [str(項目.作用ID) for 項目 in 固定作用群]
        if any(not 作用ID.strip() for 作用ID in 作用ID群):
            raise ValueError("HDS作用IDは空にできない")
        if len(作用ID群) != len(set(作用ID群)):
            raise ValueError("HDS作用IDは実行主体内で一意である必要がある")
        self.作用群 = 固定作用群
        self.作用選択器 = 作用選択器 or 標準HDS作用選択器()
        self.最大作用回数 = 最大作用回数

    @staticmethod
    def _状態更新(前: HDS実行状態, 作用結果: HDS作用結果) -> tuple[HDS実行状態, HDS状態差]:
        成立状態群 = set(前.成立状態)
        成立状態群.difference_update(作用結果.削除状態)
        成立状態群.update(作用結果.追加状態)

        残差群 = set(前.残差)
        残差群.difference_update(作用結果.解消残差)
        残差群.update(作用結果.追加残差)

        成果辞書 = 前.成果辞書()
        成果辞書.update(dict(作用結果.成果))
        主体辞書 = 前.主体辞書()
        主体辞書.update(dict(作用結果.主体状態差分))

        暫定 = HDS実行状態(
            前.目的,
            前.要求状態,
            frozenset(成立状態群),
            frozenset(残差群),
            tuple(sorted(成果辞書.items(), key=lambda 行: 行[0])),
            tuple(sorted(主体辞書.items(), key=lambda 行: 行[0])),
            前.版,
        )
        変化 = 暫定.状態署名 != 前.状態署名
        後 = HDS実行状態(
            暫定.目的,
            暫定.要求状態,
            暫定.成立状態,
            暫定.残差,
            暫定.成果,
            暫定.主体状態,
            前.版 + 1 if 変化 else 前.版,
        )

        前成果 = 前.成果辞書()
        後成果 = 後.成果辞書()
        変更成果 = tuple(sorted(
            鍵 for 鍵 in set(前成果) | set(後成果)
            if _正規化(前成果.get(鍵)) != _正規化(後成果.get(鍵))
        ))
        前主体 = 前.主体辞書()
        後主体 = 後.主体辞書()
        変更主体 = tuple(sorted(
            鍵 for 鍵 in set(前主体) | set(後主体)
            if _正規化(前主体.get(鍵)) != _正規化(後主体.get(鍵))
        ))
        状態差 = HDS状態差(
            前.状態署名,
            後.状態署名,
            tuple(sorted(後.成立状態 - 前.成立状態)),
            tuple(sorted(前.成立状態 - 後.成立状態)),
            tuple(sorted(前.残差 - 後.残差)),
            tuple(sorted(後.残差 - 前.残差)),
            変更成果,
            変更主体,
        )
        return 後, 状態差

    def 実行(self, 初期状態: HDS実行状態) -> HDS実行結果:
        if not isinstance(初期状態, HDS実行状態):
            raise TypeError("HDS実行主体にはHDS実行状態が必要")
        現在 = 初期状態
        履歴: list[HDS作用記録] = []

        for 番号 in range(1, self.最大作用回数 + 1):
            if 現在.閉包済み:
                return HDS実行結果(
                    HDS終端.採用,
                    現在,
                    tuple(履歴),
                    ("HDS_GOAL_CLOSED",),
                )

            機会群: list[HDS作用機会] = []
            ID別作用: dict[str, HDS作用器] = {}
            for 作用 in self.作用群:
                機会 = 作用.機会(現在)
                if 機会 is None:
                    continue
                if 機会.作用ID != 作用.作用ID:
                    raise ValueError("HDS作用器と作用機会の作用IDが一致しない")
                機会群.append(機会)
                ID別作用[機会.作用ID] = 作用

            選択 = self.作用選択器.選択(現在, tuple(機会群), tuple(履歴))
            if 選択 is None:
                return HDS実行結果(
                    HDS終端.保留,
                    現在,
                    tuple(履歴),
                    ("HDS_NO_PRODUCTIVE_ACTION",),
                )

            前状態 = 現在
            作用結果 = ID別作用[選択.作用ID].実行(前状態)
            if not isinstance(作用結果, HDS作用結果):
                raise TypeError("HDS作用器はHDS作用結果を返す必要がある")
            現在, 状態差 = self._状態更新(前状態, 作用結果)
            記録 = HDS作用記録(
                番号,
                選択.作用ID,
                選択.作用入力署名,
                作用結果.状態,
                前状態.状態署名,
                現在.状態署名,
                状態差,
                tuple(sorted(前状態.残差.intersection(選択.解消対象))),
                tuple(sorted(前状態.未達状態.intersection(選択.出力状態))),
                tuple(作用結果.理由),
            )
            履歴.append(記録)

            if 作用結果.停止要求:
                終端 = HDS終端.失敗 if 作用結果.状態 == HDS作用状態.失敗 else HDS終端.保留
                return HDS実行結果(
                    終端,
                    現在,
                    tuple(履歴),
                    tuple(dict.fromkeys(("HDS_ACTION_REQUESTED_STOP", *作用結果.理由))),
                )

        if 現在.閉包済み:
            return HDS実行結果(HDS終端.採用, 現在, tuple(履歴), ("HDS_GOAL_CLOSED",))
        return HDS実行結果(
            HDS終端.保留,
            現在,
            tuple(履歴),
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

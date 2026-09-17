from __future__ import annotations

from typing import Mapping, Sequence

from .HDS実行主体 import HDS実行主体, HDS実行状態, HDS作用器, HDS実行結果
from .統合駆動_v2.政策 import HDS運用政策
from .統合駆動_v2.認識 import HDS認識項目
from .統合駆動_v2.観測 import HDS観測器, HDS観測要求
from .統合駆動_v2.仮説 import HDS仮説, HDS仮説雛型, HDS作業枝
from .統合駆動_v2.依存 import HDS依存辺
from .統合駆動_v2.記憶 import HDS記憶
from .統合駆動_v2.検証 import HDS検証器, HDS草案
from .統合駆動_v2.形成 import HDS形成関係
from .統合駆動_v2.入力境界 import HDS異種表象, HDS異種入力作用


HDS駆動コア版 = "MINIDORA-HDS-FIRST-v3"


class HDS駆動コア:
    """MINIDORA内部のHDS-first公開実行入口。

    外向きLLM成立用の厳密言語模型核を置換しない。ここではHDSが目的・状態・残差を所有し、
    MINIDORAの構文化器・参照・計算・模型・能力モジュール等を作用器として起動する。

    `目的` は説明であり完了条件ではない。COMMITには、呼出側が `要求状態`、
    `初期残差` または `要求認識` によって閉包条件を明示する必要がある。構文化の成功だけを利用者目的の
    達成へ読み替えない。
    """

    def __init__(
        self,
        *,
        HDSコンパイラ=None,
        最大作用回数: int = 32,
        政策: HDS運用政策 | None = None,
        観測器: Sequence[HDS観測器] = (),
        仮説雛型: Sequence[HDS仮説雛型] = (),
        検証器: Sequence[HDS検証器] = (),
        最終検証器: Sequence[HDS検証器] = (),
        関係規則=(),
        未来制約=(),
    ) -> None:
        self.HDSコンパイラ = HDSコンパイラ
        if type(最大作用回数) is not int or not 1 <= 最大作用回数 <= 4096:
            raise ValueError("最大作用回数は1..4096の整数が必要")
        self.最大作用回数 = 最大作用回数
        self.政策 = 政策
        self.観測器 = tuple(観測器)
        self.仮説雛型 = tuple(仮説雛型)
        self.検証器 = tuple(検証器)
        self.最終検証器 = tuple(最終検証器)
        self.関係規則 = tuple(関係規則)
        self.未来制約 = tuple(未来制約)

    def 実行(
        self,
        問合せ: str,
        *,
        目的: Sequence[str] = (),
        要求状態: Sequence[str] = (),
        追加作用: Sequence[HDS作用器] = (),
        初期成立状態: Sequence[str] = (),
        初期残差: Sequence[str] | None = None,
        初期成果: Mapping[str, object] | None = None,
        主体状態: Mapping[str, object] | None = None,
        前回結果: object = None,
        HDS履歴=(),
        文脈=None,
        初期認識: Sequence[HDS認識項目] = (),
        要求認識: Sequence[str] = (),
        初期依存: Sequence[HDS依存辺] = (),
        観測要求: Sequence[HDS観測要求] = (),
        初期記憶: HDS記憶 | None = None,
        初期仮説: Sequence[HDS仮説] = (),
        初期枝: Sequence[HDS作業枝] = (),
        初期草案: Sequence[HDS草案] = (),
        形成関係: Sequence[HDS形成関係] = (),
        異種表象: Sequence[HDS異種表象] = (),
    ) -> HDS実行結果:
        if not isinstance(問合せ, str) or not 問合せ.strip():
            raise ValueError("HDS駆動コアの問合せは空でない文字列である必要がある")
        明示要求状態 = tuple(str(x) for x in 要求状態)
        明示残差 = tuple(str(x) for x in (初期残差 or ()))
        明示要求認識 = frozenset(要求認識)
        if not 明示要求状態 and not 明示残差 and not 明示要求認識:
            raise ValueError(
                "HDS駆動コアには要求状態・初期残差・要求認識のいずれかによる明示的な完了条件が必要"
            )

        作用群: list[HDS作用器] = []
        残差群 = set(明示残差)
        if self.HDSコンパイラ is not None:
            from .HDS構文化作用 import HDS構文化作用
            残差群.add("入力未構文化")
            作用群.append(HDS構文化作用(
                self.HDSコンパイラ,
                問合せ,
                前回結果=前回結果,
                HDS履歴=tuple(HDS履歴),
                文脈=文脈,
            ))
        if 異種表象:
            残差群.add("異種入力未接続")
            作用群.append(HDS異種入力作用(tuple(異種表象)))
        作用群.extend(tuple(追加作用))

        初期 = HDS実行状態(
            tuple(str(x) for x in 目的),
            frozenset(明示要求状態),
            frozenset(str(x) for x in 初期成立状態),
            frozenset(残差群),
            tuple(sorted(dict(初期成果 or {}).items(), key=lambda 行: 行[0])),
            tuple(sorted(dict(主体状態 or {}).items(), key=lambda 行: 行[0])),
            0,
            認識=tuple(初期認識), 要求認識=明示要求認識,
            依存=tuple(初期依存), 観測要求=tuple(観測要求),
            記憶=初期記憶 if 初期記憶 is not None else HDS記憶(),
            仮説=tuple(初期仮説), 枝=tuple(初期枝), 草案=tuple(初期草案),
            形成関係=tuple(形成関係),
        )
        return HDS実行主体(
            tuple(作用群),
            最大作用回数=self.最大作用回数,
            政策=self.政策, 観測器=self.観測器, 仮説雛型=self.仮説雛型,
            検証器=self.検証器, 最終検証器=self.最終検証器,
            関係規則=self.関係規則, 未来制約=self.未来制約,
        ).実行(初期)


__all__ = ["HDS駆動コア版", "HDS駆動コア"]

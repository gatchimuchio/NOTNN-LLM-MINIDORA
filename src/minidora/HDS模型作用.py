from __future__ import annotations

from hashlib import sha256
from typing import Mapping, Sequence

from .HDS実行主体 import HDS作用機会, HDS作用結果, HDS作用状態, HDS実行状態
from .HDS中間表現 import HDSIR
from .HDS模型射影 import HDSMINIDORA模型評価
from .HDS構文化記録_v1_3 import HDS作用差分構造
from .模型 import MINIDORA模型核


class HDS模型評価作用:
    """既存MINIDORA能力模型をHDSの一作用として使用するAdapter。

    `HDSMINIDORA模型評価` が返すAPPROVE/SUSPENDは模型作用の局所閉包状態であり、
    HDS-first core全体のCOMMITではない。回答ラベル・模型結果は成果としてHDSへ帰還する。
    """

    def __init__(
        self,
        質問IR: HDSIR,
        候補IR: Mapping[str, HDSIR],
        資料IR: Sequence[HDSIR],
        *,
        模型核: MINIDORA模型核 | None = None,
        参照識別子: Sequence[str] | None = None,
        参照信頼: Sequence[float] | None = None,
        作用差分構造群: Sequence[HDS作用差分構造] = (),
        入力状態: Sequence[str] = (),
        出力状態: str = "模型評価閉包",
        解消対象: Sequence[str] = (),
        資源負荷: int = 2,
    ) -> None:
        if not isinstance(質問IR, HDSIR):
            raise TypeError("HDS模型評価作用にはHDSIRの質問が必要")
        self.質問IR = 質問IR
        self.候補IR = dict(候補IR)
        self.資料IR = tuple(資料IR)
        self.模型核 = 模型核
        self.参照識別子 = tuple(参照識別子) if 参照識別子 is not None else None
        self.参照信頼 = tuple(参照信頼) if 参照信頼 is not None else None
        self.作用差分構造群 = tuple(作用差分構造群)
        self.入力状態 = frozenset(str(x) for x in 入力状態)
        self.出力状態 = str(出力状態)
        self.解消対象 = frozenset(str(x) for x in 解消対象)
        self.資源負荷 = max(0, int(資源負荷))
        self.作用ID = "MINIDORA能力模型評価"
        raw = repr((
            self.質問IR,
            tuple(sorted(self.候補IR.items())),
            self.資料IR,
            self.参照識別子,
            self.参照信頼,
            self.作用差分構造群,
        )).encode("utf-8")
        self._固定入力署名 = sha256(raw).hexdigest()

    def 機会(self, 状態: HDS実行状態) -> HDS作用機会 | None:
        if not self.入力状態.issubset(状態.成立状態):
            return None
        return HDS作用機会(
            self.作用ID,
            f"{self._固定入力署名}:{状態.状態署名}",
            self.入力状態,
            frozenset({self.出力状態}),
            self.解消対象,
            self.資源負荷,
            0.0,
            True,
            ("MINIDORA_MODEL_AS_HDS_ACTION",),
        )

    def 実行(self, 状態: HDS実行状態) -> HDS作用結果:
        result = HDSMINIDORA模型評価(
            self.質問IR,
            self.候補IR,
            self.資料IR,
            模型核=self.模型核,
            判断主体=None,
            参照識別子=self.参照識別子,
            参照信頼=self.参照信頼,
            作用差分構造群=self.作用差分構造群,
        )
        artifact = (
            ("MINIDORA模型射影", result),
            ("MINIDORA模型回答ラベル", result.回答ラベル),
        )
        if result.状態 == "APPROVE" and result.回答ラベル is not None:
            return HDS作用結果(
                HDS作用状態.成立,
                追加状態=frozenset({self.出力状態}),
                解消残差=self.解消対象,
                成果=artifact,
                理由=tuple(dict.fromkeys((
                    "MODEL_ACTION_CLOSED",
                    *tuple(result.理由),
                ))),
            )

        residual = "模型評価未閉包:" + "|".join(tuple(result.理由)[:8])
        return HDS作用結果(
            HDS作用状態.保留,
            追加残差=frozenset({residual}),
            成果=artifact,
            理由=tuple(dict.fromkeys((
                "MODEL_ACTION_SUSPENDED",
                *tuple(result.理由),
            ))),
        )


__all__ = ["HDS模型評価作用"]

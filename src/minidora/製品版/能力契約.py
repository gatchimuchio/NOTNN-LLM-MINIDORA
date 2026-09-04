from __future__ import annotations
from dataclasses import dataclass
from typing import Protocol, Any
from .型 import 能力結果, 参照資料

能力契約版 = "MINIDORA-CAPABILITY-CONTRACT-v1"

@dataclass(frozen=True, slots=True)
class 能力文脈:
    入力文: str
    セッションID: str
    直前応答: str = ""
    直前参照: tuple[参照資料, ...] = ()
    履歴: tuple[tuple[str, str], ...] = ()
    補助: dict[str, Any] | None = None

class 能力Module(Protocol):
    名前: str
    版: str
    優先度: int
    def 判定(self, 文脈: 能力文脈) -> float: ...
    def 実行(self, 文脈: 能力文脈) -> 能力結果: ...

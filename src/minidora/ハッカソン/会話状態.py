from __future__ import annotations

from dataclasses import dataclass, field
from threading import RLock

from .型 import ニュース項目


@dataclass(slots=True)
class 会話状態:
    セッションID: str
    履歴: list[tuple[str, str]] = field(default_factory=list)
    直前応答: str = ""
    直前経路: str = ""
    直前追跡ID: str = ""
    直前ニュース: tuple[ニュース項目, ...] = ()

    def 記録(self, *, 入力文: str, 応答文: str, 経路: str, 追跡ID: str, ニュース: tuple[ニュース項目, ...] = ()) -> None:
        self.履歴.append(("user", 入力文))
        self.履歴.append(("assistant", 応答文))
        if len(self.履歴) > 100:
            del self.履歴[:-100]
        self.直前応答 = 応答文
        self.直前経路 = 経路
        self.直前追跡ID = 追跡ID
        if ニュース:
            self.直前ニュース = tuple(ニュース)
        elif 経路 not in {"要約"}:
            self.直前ニュース = ()


class 会話状態庫:
    def __init__(self) -> None:
        self._states: dict[str, 会話状態] = {}
        self._lock = RLock()

    def 取得(self, セッションID: str) -> 会話状態:
        key = str(セッションID or "default")
        with self._lock:
            state = self._states.get(key)
            if state is None:
                state = 会話状態(key)
                self._states[key] = state
            return state

from __future__ import annotations
from dataclasses import dataclass, field, asdict
from datetime import datetime
from typing import Any

@dataclass(frozen=True, slots=True)
class 参照資料:
    識別子: str
    題名: str
    出典: str
    URL: str = ""
    公開時刻: datetime | None = None
    本文: str = ""

    def 辞書化(self) -> dict[str, Any]:
        data = asdict(self)
        data["公開時刻"] = self.公開時刻.isoformat() if self.公開時刻 else None
        return data

@dataclass(frozen=True, slots=True)
class 能力結果:
    成立: bool
    本文: str
    根拠: tuple[str, ...] = ()
    参照: tuple[参照資料, ...] = ()
    データ: dict[str, Any] = field(default_factory=dict)
    保留理由: str = ""

@dataclass(frozen=True, slots=True)
class 製品応答:
    セッションID: str
    本文: str
    状態: str
    経路: str
    追跡ID: str
    監査ハッシュ: str
    参照: tuple[参照資料, ...] = ()
    能力: tuple[str, ...] = ()
    メタデータ: dict[str, Any] = field(default_factory=dict)

    def 辞書化(self) -> dict[str, Any]:
        return {
            "session_id": self.セッションID,
            "response": self.本文,
            "status": self.状態,
            "route": self.経路,
            "trace_id": self.追跡ID,
            "trace_hash": self.監査ハッシュ,
            "capabilities": list(self.能力),
            "sources": [r.辞書化() for r in self.参照],
            "metadata": self.メタデータ,
        }

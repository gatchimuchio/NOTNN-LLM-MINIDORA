from __future__ import annotations
from dataclasses import dataclass
from typing import Any

@dataclass(frozen=True, slots=True)
class 意味要求:
    要求種: str
    対象: str | None = None
    関係列: tuple[str, ...] = ()
    式: str | None = None
    表出言語: str = "ja"

@dataclass(frozen=True, slots=True)
class 応答:
    値: Any
    表出: str | None
    状態: str
    理由: tuple[str, ...]
    参照: tuple[dict[str, Any], ...] = ()
    履歴: tuple[dict[str, Any], ...] = ()
    未解: tuple[str, ...] = ()
    矛盾: tuple[str, ...] = ()

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from .layer0 import Layer0
from .参照 import 参照供給器, 参照記録
from .命令 import 手順
from .採否 import 採否, 採否結果


@dataclass(frozen=True, slots=True)
class 要求:
    問合せ: str
    手順: 手順
    初期状態: dict[str, Any] = field(default_factory=dict)
    参照必須: bool = False


@dataclass(frozen=True, slots=True)
class 結果:
    値: Any
    状態: dict[str, Any]
    参照: tuple[参照記録, ...]
    履歴: tuple[dict[str, Any], ...]
    採否: 採否結果


class ミニドラ:
    """Layer-0 + 日本語命令P + 外部参照R の最小統合実行系。"""

    def __init__(self, 参照供給器_: 参照供給器 | None = None, layer0: Layer0 | None = None) -> None:
        self.参照供給器 = 参照供給器_
        self.layer0 = layer0 or Layer0()

    def 実行(self, 要求_: 要求) -> 結果:
        参照 = ()
        if self.参照供給器 is not None:
            参照 = self.参照供給器.検索(要求_.問合せ)
        if 要求_.参照必須 and not 参照:
            判定 = 採否(根拠数=0)
            return 結果(None, dict(要求_.初期状態), (), (), 判定)

        初期 = dict(要求_.初期状態)
        初期["参照"] = 参照
        文脈 = self.layer0.実行(要求_.手順, 初期)
        値 = 文脈.状態.get("結果")
        判定 = 採否(根拠数=len(参照) if 要求_.参照必須 else 1)
        return 結果(値, dict(文脈.状態), tuple(参照), tuple(文脈.履歴), 判定)

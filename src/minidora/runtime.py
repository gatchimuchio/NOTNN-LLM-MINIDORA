from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Mapping

from .layer0 import Layer0
from .主体 import 主体主幹, 主体状態, 主体更新提案, 主体整合結果, 主体更新記録
from .参照 import 参照供給器, 参照記録
from .命令 import 手順
from .採否 import 実行状態, 採否, 採否結果


@dataclass(frozen=True, slots=True)
class 要求:
    問合せ: str
    手順: 手順
    初期状態: dict[str, Any] = field(default_factory=dict)
    参照必須: bool = False
    主体更新提案: 主体更新提案 | None = None
    主体整合必須: bool = True
    矛盾数: int = 0
    境界違反: bool = False


@dataclass(frozen=True, slots=True)
class 結果:
    値: Any
    状態: dict[str, Any]
    参照: tuple[参照記録, ...]
    履歴: tuple[dict[str, Any], ...]
    採否: 採否結果
    主体状態: 主体状態 | None = None
    主体整合: 主体整合結果 | None = None
    主体監査履歴: tuple[主体更新記録, ...] = ()


class ミニドラ:
    """Layer-0 v4責任上に、日本語命令P・参照R・主体主幹を接続する非ニューラル実行系。"""

    def __init__(
        self,
        参照供給器_: 参照供給器 | None = None,
        layer0: Layer0 | None = None,
        主体主幹_: 主体主幹 | None = None,
    ) -> None:
        self.参照供給器 = 参照供給器_
        self.layer0 = layer0 or Layer0()
        self.主体主幹 = 主体主幹_ or 主体主幹()

    @property
    def 主体状態(self) -> 主体状態:
        return self.主体主幹.現在

    def _主体更新提案(self, 文脈状態: Mapping[str, Any], 要求_: 要求) -> 主体更新提案 | None:
        候補 = 文脈状態.get("主体更新提案", 要求_.主体更新提案)
        if 候補 is None:
            return None
        if isinstance(候補, 主体更新提案):
            return 候補
        if isinstance(候補, Mapping):
            return 主体更新提案(
                変更=候補.get("変更", {}),
                理由=tuple(候補.get("理由", ())),
                根拠=tuple(候補.get("根拠", ())),
            )
        raise TypeError("主体更新提案は 主体更新提案 または mapping である必要がある")

    def _採否合成(self, 基礎: 採否結果, 主体: 主体整合結果, 必須: bool) -> 採否結果:
        if not 必須 or 主体.状態 in {実行状態.合格, 実行状態.非適用}:
            return 基礎
        if 主体.状態 == 実行状態.失敗:
            return 採否結果(実行状態.失敗, 基礎.理由 + 主体.理由)
        return 採否結果(実行状態.保留, 基礎.理由 + 主体.理由)

    def 実行(self, 要求_: 要求) -> 結果:
        参照 = ()
        if self.参照供給器 is not None:
            参照 = self.参照供給器.検索(要求_.問合せ)
        if 要求_.参照必須 and not 参照:
            判定 = 採否(根拠数=0)
            主体整合 = self.主体主幹.非適用結果("参照不足のため主体更新未実行")
            return 結果(
                None,
                dict(要求_.初期状態),
                (),
                (),
                判定,
                self.主体主幹.現在,
                主体整合,
                self.主体主幹.履歴,
            )

        初期 = dict(要求_.初期状態)
        初期["参照"] = 参照
        初期["主体状態"] = self.主体主幹.状態辞書()
        文脈 = self.layer0.実行(要求_.手順, 初期)
        値 = 文脈.状態.get("結果")

        提案 = self._主体更新提案(文脈.状態, 要求_)
        主体整合 = self.主体主幹.評価更新(提案)

        結果根拠数 = len(参照) if 要求_.参照必須 else (1 if 値 is not None else 0)
        基礎判定 = 採否(根拠数=結果根拠数, 矛盾数=要求_.矛盾数, 危険=要求_.境界違反)
        判定 = self._採否合成(基礎判定, 主体整合, 要求_.主体整合必須)
        if 要求_.主体整合必須 and 判定.状態 in {実行状態.保留, 実行状態.失敗}:
            値 = None

        return 結果(
            値,
            dict(文脈.状態),
            tuple(参照),
            tuple(文脈.履歴),
            判定,
            self.主体主幹.現在,
            主体整合,
            self.主体主幹.履歴,
        )

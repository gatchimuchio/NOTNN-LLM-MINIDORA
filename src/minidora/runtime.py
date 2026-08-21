from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Mapping

from .layer0 import Layer0
from .主体 import 主体主幹, 主体状態, 主体更新提案, 主体整合結果, 主体更新記録
from .参照 import 参照供給器, 参照記録
from .命令 import 手順
from .採否 import 実行状態, 採否, 採否結果
from .言語 import 自然言語器, 言語計画
from .hds_ir import HDSIR


@dataclass(frozen=True, slots=True)
class 要求:
    問合せ: str
    手順: 手順 | None = None
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
    言語計画: str | None = None
    HDS_IR: HDSIR | None = None


class ミニドラ:
    """HDS意味IRを入力境界とし、Layer-0・P・R・主体主幹まで閉じた非ニューラル実行系。"""

    def __init__(
        self,
        参照供給器_: 参照供給器 | None = None,
        layer0: Layer0 | None = None,
        主体主幹_: 主体主幹 | None = None,
        自然言語器_: 自然言語器 | None = None,
    ) -> None:
        self.参照供給器 = 参照供給器_
        self.layer0 = layer0 or Layer0()
        self.主体主幹 = 主体主幹_ or 主体主幹()
        self.自然言語器 = 自然言語器_ or 自然言語器()

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
        自動計画 = 要求_.手順 is None
        HDS_IR_ = self.自然言語器.compiler.コンパイル(要求_.問合せ) if 自動計画 else None
        計画 = None
        if HDS_IR_ is not None and HDS_IR_.手順 is not None:
            計画 = 言語計画(HDS_IR_.手順, dict(HDS_IR_.初期状態), HDS_IR_.参照必須, HDS_IR_.種別)
        手順_ = 計画.手順 if 計画 is not None else 要求_.手順
        参照必須 = 要求_.参照必須 or bool(HDS_IR_ and HDS_IR_.参照必須)

        if 自動計画 and 手順_ is None:
            主体整合 = self.主体主幹.非適用結果("HDS-IR未閉包")
            return 結果(
                None, {}, (), (),
                採否結果(実行状態.保留, ("HDS-IR未閉包", "意味残差保持")),
                self.主体主幹.現在, 主体整合, self.主体主幹.履歴,
                HDS_IR_.種別 if HDS_IR_ else None, HDS_IR_,
            )

        参照 = ()
        if self.参照供給器 is not None:
            参照 = self.参照供給器.検索(要求_.問合せ)
        if HDS_IR_ is not None and 参照:
            HDS_IR_ = self.自然言語器.compiler.参照統合(HDS_IR_, tuple(参照))
        if 参照必須 and not 参照:
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
                HDS_IR_.種別 if HDS_IR_ else (計画.種別 if 計画 else None),
                HDS_IR_,
            )

        初期 = dict(要求_.初期状態)
        if 計画 is not None:
            初期.update(計画.初期状態)
        初期["参照"] = 参照
        初期["主体状態"] = self.主体主幹.状態辞書()

        try:
            文脈 = self.layer0.実行(手順_, 初期)
        except (ValueError, TypeError, ZeroDivisionError) as exc:
            if not 自動計画:
                raise
            主体整合 = self.主体主幹.非適用結果("HDS-IR実行失敗")
            return 結果(
                None,
                初期,
                tuple(参照),
                (),
                採否結果(実行状態.失敗, ("HDS-IR実行失敗", str(exc))),
                self.主体主幹.現在,
                主体整合,
                self.主体主幹.履歴,
                HDS_IR_.種別 if HDS_IR_ else (計画.種別 if 計画 else None),
                HDS_IR_,
            )

        値 = 文脈.状態.get("結果")
        提案 = self._主体更新提案(文脈.状態, 要求_)
        主体整合 = self.主体主幹.評価更新(提案)

        if 参照必須:
            結果根拠数 = len(参照) if 値 is not None else 0
        else:
            結果根拠数 = 1 if 値 is not None else 0
        HDS矛盾数 = sum(1 for r in HDS_IR_.残差 if r.種別 == "contradiction") if HDS_IR_ is not None else 0
        基礎判定 = 採否(
            根拠数=結果根拠数,
            矛盾数=要求_.矛盾数 + HDS矛盾数,
            危険=要求_.境界違反,
        )
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
            HDS_IR_.種別 if HDS_IR_ else (計画.種別 if 計画 else None),
            HDS_IR_,
        )

    def コンパイル(self, 問合せ: str) -> HDSIR:
        return self.自然言語器.compiler.コンパイル(問合せ)

    def 応答(self, 問合せ: str) -> str:
        """通常利用入口。自然言語文字列を受け、HDS-IR経由で自然言語文字列を返す。"""

        result = self.実行(要求(問合せ))
        return self.自然言語器.表面化(
            result.値,
            result.採否.状態.value,
            result.採否.理由,
        )

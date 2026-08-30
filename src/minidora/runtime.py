from __future__ import annotations

from collections.abc import Sequence
from fractions import Fraction

from .hds_choice_runtime import HDS選択問題
from .hds_reference import HDS参照予算選択
from .hds_runtime_projection import HDSR質問射影
from .hds介入制御 import HDS介入制御, 標準HDS介入制御
from .hds参照拡張 import HDS参照検索強化
from .hds監督選択runtime import HDS監督選択実行
from .runtime_v03 import ミニドラ as _ミニドラV03, 結果, 要求
from .模型 import MINIDORA模型核, 模型結果, 成立候補, 言語状態
from .能力状態差循環 import 標準能力模型核
from .言語確率法則 import (
    MINIDORA厳密言語模型,
    条件付き記号分布,
    言語確率監査結果,
    最小厳密言語模型,
)
from .計算実行器 import 計算実行器


_標準HDS監督 = object()


class ミニドラ(_ミニドラV03):
    """MINIDORA v0.5 Runtime。

    構成定義v8に従い、厳密言語模型核と能力模型核を分離する。

    - ``言語模型核``: 完全言語状態上の整合した確率法則を担う非ニューラル厳密言語模型。
    - ``能力模型核``: 候補・証拠・関係評価と状態差起動の能力側。
    - ``計算実行器``: 算術・比較等の決定論的計算境界。
    - ``HDS監督制御``: 選択問題が既存能力だけで閉じない時に、既存作用へだけ介入する制御系。

    HDS監督制御は回答ラベル・候補得点を受け取らず、回答を生成・採用しない。
    最終回答は既存MINIDORA能力resolverが決める。旧output-only/outer HDS判断ラッパーはactive pathで使わない。

    既存 ``模型核`` 属性は後方互換のため ``能力模型核`` の互換名として保持する。
    候補得点を確率へ読み替えて厳密言語模型を偽装しない。
    """

    def __init__(
        self,
        参照供給器_=None,
        layer0=None,
        主体主幹_=None,
        自然言語器_=None,
        HDSコンパイラ_=None,
        Trinity文脈_=None,
        K3能力核_=None,
        *,
        模型核_: MINIDORA模型核 | None = None,
        言語模型核_: MINIDORA厳密言語模型 | None = None,
        計算実行器_: 計算実行器 | None = None,
        HDS監督制御_: HDS介入制御 | None | object = _標準HDS監督,
    ) -> None:
        executor = 計算実行器_ or layer0 or 計算実行器()
        super().__init__(
            参照供給器_=参照供給器_,
            layer0=executor,
            主体主幹_=主体主幹_,
            自然言語器_=自然言語器_,
            HDSコンパイラ_=HDSコンパイラ_,
            Trinity文脈_=Trinity文脈_,
            K3能力核_=K3能力核_,
        )
        self.言語模型核 = 言語模型核_ or 最小厳密言語模型()
        self.能力模型核 = 模型核_ or 標準能力模型核()
        self.模型核 = self.能力模型核
        self.計算実行器 = executor
        self.layer0 = executor
        self.HDS監督制御 = 標準HDS介入制御() if HDS監督制御_ is _標準HDS監督 else HDS監督制御_

    @property
    def K3能力核(self):
        """旧helperへ能力模型核だけを接続する。"""
        core = super().K3能力核
        setattr(core, "_minidora_model_core", self.能力模型核)
        return core

    def 実行(self, 要求_: 要求) -> 結果:
        """選択問題だけ監督統合経路へ送り、それ以外は既存Runtimeをそのまま使う。"""
        if 要求_.手順 is None and self.HDSコンパイラ is not None:
            try:
                hds_ir = self.コンパイル(要求_.問合せ)
            except (ValueError, TypeError):
                return super().実行(要求_)
            if HDS選択問題(hds_ir):
                references = ()
                if self.参照供給器 is not None:
                    budget = HDS参照予算選択(hds_ir)
                    references = HDS参照検索強化(
                        self.参照供給器,
                        HDSR質問射影(hds_ir),
                        上限=budget.取得上限,
                        一問合せ上限=budget.一問合せ上限,
                        最大問合せ並列=budget.最大問合せ並列,
                    )
                supervised = HDS監督選択実行(
                    hds_ir,
                    tuple(references),
                    コンパイル=self.コンパイル,
                    基礎能力核=self.K3能力核,
                    模型核=self.能力模型核,
                    参照供給器=self.参照供給器,
                    HDS制御=self.HDS監督制御,
                )
                return self._HDS選択結果(要求_, hds_ir, supervised.参照, supervised.選択)
        return super().実行(要求_)

    def 言語確率(self, 文章: str) -> Fraction:
        return self.言語模型核.系列確率(文章)

    def 次記号分布(self, 接頭辞: str = "") -> 条件付き記号分布:
        return self.言語模型核.次記号分布(接頭辞)

    def 言語模型監査(self) -> 言語確率監査結果:
        return self.言語模型核.正規化監査()

    def 言語評価(
        self,
        文脈: str | 言語状態,
        候補群: Sequence[str | 言語状態 | 成立候補],
        *,
        言語体系: str = "自然言語:ja",
        履歴: Sequence[str | 言語状態] = (),
        条件: Sequence[str] = (),
        参照状態: Sequence[str | 言語状態] = (),
    ) -> 模型結果:
        """候補言語状態の成立差を決定論的に返す能力API。"""
        current = 文脈 if isinstance(文脈, 言語状態) else 言語状態(str(文脈), 言語体系)
        history_states = tuple(
            item if isinstance(item, 言語状態) else 言語状態(str(item), current.言語体系)
            for item in 履歴
        )
        reference_states = tuple(
            item if isinstance(item, 言語状態) else 言語状態(str(item), current.言語体系)
            for item in 参照状態
        )
        candidates: list[成立候補] = []
        for index, item in enumerate(候補群):
            if isinstance(item, 成立候補):
                candidates.append(item)
            elif isinstance(item, 言語状態):
                candidates.append(成立候補(item.識別子 or f"候補{index + 1}", item))
            else:
                candidates.append(成立候補(f"候補{index + 1}", 言語状態(str(item), current.言語体系)))
        return self.能力模型核.評価言語状態(
            current,
            tuple(candidates),
            履歴=history_states,
            条件=条件,
            参照状態=reference_states,
        )


__all__ = ["ミニドラ", "要求", "結果"]

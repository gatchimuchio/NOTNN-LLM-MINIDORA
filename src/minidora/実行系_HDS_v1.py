from __future__ import annotations

from dataclasses import replace

from .HDS参照 import HDS参照予算選択, HDS参照検索
from .HDS実行主体 import HDS終端
from .HDS実行系射影 import HDSR質問射影
from .HDS選択実行系 import HDS選択実行結果, HDS選択問題
from .HDS選択継承循環 import 回答成果名, 参照成果名, 現行結果成果名
from .HDS駆動コア import HDS駆動コア, HDS駆動コア版, HDS継承基準版
from .実行系 import ミニドラ as _MINIDORAV05
from .実行系_v03 import 結果, 要求


def _選択肢(ir) -> tuple[str, ...]:
    rows = [
        (coord.座標ID.split(":", 1)[1], str(coord.内容))
        for coord in ir.座標
        if coord.座標ID.startswith("選択肢:")
    ]
    return tuple(value for _, value in sorted(rows, key=lambda row: row[0]))


def _作用履歴(実行結果) -> tuple[str, ...]:
    return tuple(record.作用ID for record in 実行結果.履歴)


class HDS駆動ミニドラ(_MINIDORAV05):
    """HDS-first Core v5を選択問題の実運用入口へ接続するMINIDORA実行系。

    MINIDORA30系のformal模型核と、更新前HDS-MINIDORAの追加参照・計算・再評価・
    非退行下限を `HDS駆動コア.選択実行` の通常循環として継承する。
    """

    版 = "v2-hds-first-core-inheritance"

    def _初期参照(self, ir):
        if self.参照供給器 is None:
            return ()
        予算 = HDS参照予算選択(ir)
        return HDS参照検索(
            self.参照供給器,
            HDSR質問射影(ir),
            上限=予算.取得上限,
            一問合せ上限=予算.一問合せ上限,
            最大問合せ並列=予算.最大問合せ並列,
        )

    def 実行(self, 要求_: 要求) -> 結果:
        if 要求_.手順 is not None or self.HDSコンパイラ is None:
            return super().実行(要求_)
        try:
            ir = self.コンパイル(要求_.問合せ)
        except (ValueError, TypeError):
            return super().実行(要求_)
        if not HDS選択問題(ir):
            return super().実行(要求_)

        choices = _選択肢(ir)
        if len(choices) < 2:
            return super().実行(要求_)

        initial_references = self._初期参照(ir)
        core = HDS駆動コア(
            HDSコンパイラ=self.HDSコンパイラ,
            最大作用回数=32,
        )
        driven = core.選択実行(
            要求_.問合せ,
            choices,
            初期参照=initial_references,
            参照供給器=self.参照供給器,
            計算実行器_=self.計算実行器,
            模型核=self.能力模型核,
            最大回復回数=6,
        )

        成果 = driven.状態.成果辞書()
        selection = 成果.get(現行結果成果名)
        if not isinstance(selection, HDS選択実行結果):
            raise RuntimeError("HDS-first Coreが選択評価結果を帰還しなかった")

        final_references = 成果.get(参照成果名, initial_references)
        if not isinstance(final_references, tuple):
            raise TypeError("HDS-first Coreの参照成果はtupleである必要がある")

        core_reasons = tuple(dict.fromkeys((*tuple(selection.理由), *tuple(driven.理由))))
        if driven.終端 == HDS終端.採用:
            answer_label = 成果.get(回答成果名)
            if answer_label is None or selection.回答ラベル != answer_label:
                raise RuntimeError("HDS-first CoreのCOMMIT回答と選択評価結果が一致しない")
            selection = replace(
                selection,
                状態="APPROVE",
                理由=tuple(dict.fromkeys((*core_reasons, "HDS_FIRST_CORE_COMMIT"))),
            )
        else:
            terminal_reason = (
                "HDS_FIRST_CORE_FAIL" if driven.終端 == HDS終端.失敗
                else "HDS_FIRST_CORE_SUSPEND"
            )
            selection = replace(
                selection,
                状態="SUSPEND",
                回答ラベル=None,
                回答内容=None,
                理由=tuple(dict.fromkeys((*core_reasons, terminal_reason))),
            )

        result = self._HDS選択結果(要求_, ir, final_references, selection)
        state = dict(result.状態)
        state["HDS駆動コアRun"] = {
            "終端": driven.終端.value,
            "コア版": HDS駆動コア版,
            "継承基準": HDS継承基準版,
            "状態版": driven.状態.版,
            "参照数": len(final_references),
            "成立状態": tuple(sorted(driven.状態.成立状態)),
            "残差": tuple(sorted(driven.状態.残差)),
            "作用履歴": _作用履歴(driven),
            "理由": tuple(driven.理由),
        }
        history = result.履歴 + ({
            "op": "HDS_FIRST_CORE_INHERITANCE_RUN",
            "terminal": driven.終端.value,
            "core_version": HDS駆動コア版,
            "inheritance_baseline": HDS継承基準版,
            "actions": _作用履歴(driven),
        },)
        return replace(result, 状態=state, 履歴=history)


__all__ = ["HDS駆動ミニドラ"]

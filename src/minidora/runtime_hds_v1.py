from __future__ import annotations

from dataclasses import replace

from .hds_choice_runtime import HDS選択問題
from .hds統合runtime import HDS駆動選択実行
from .runtime import ミニドラ as _MINIDORAV05
from .runtime_v03 import 結果, 要求


class HDS駆動ミニドラ(_MINIDORAV05):
    """HDS Judgement Subjectを選択問題の唯一のCOMMIT主体に置くMINIDORA v1試作Runtime。"""

    版 = "v1-hds-judgement-subject-prototype"

    def 実行(self, 要求_: 要求) -> 結果:
        if 要求_.手順 is not None or self.HDSコンパイラ is None:
            return super().実行(要求_)
        try:
            ir = self.コンパイル(要求_.問合せ)
        except (ValueError, TypeError):
            return super().実行(要求_)
        if not HDS選択問題(ir):
            return super().実行(要求_)

        driven = HDS駆動選択実行(self, ir, 参照必須=要求_.参照必須)
        if driven.状態 == "APPROVE":
            legacy_selection = replace(
                driven.選択,
                状態="APPROVE",
                理由=driven.理由,
            )
        else:
            legacy_selection = replace(
                driven.選択,
                状態="SUSPEND",
                回答ラベル=None,
                回答内容=None,
                理由=driven.理由,
            )
        result = self._HDS選択結果(要求_, ir, driven.参照, legacy_selection)

        state = dict(result.状態)
        state["HDS判断主体Run"] = {
            "run_id": driven.認知世界.run_id,
            "状態": driven.認知世界.状態,
            "版": driven.認知世界.版,
            "委任目的": driven.認知世界.委任目的,
            "参照数": driven.認知世界.参照数,
            "評価状態": driven.認知世界.評価状態,
            "暫定性": driven.認知世界.暫定性,
            "残差": driven.認知世界.残差,
            "作用履歴": driven.認知世界.作用履歴,
        }
        history = result.履歴 + ({
            "op": "HDS_JUDGEMENT_SUBJECT_RUN",
            "run_id": driven.認知世界.run_id,
            "state": driven.認知世界.状態,
            "actions": tuple(action for action, _ in driven.認知世界.作用履歴),
        },)
        return replace(result, 状態=state, 履歴=history)


__all__ = ["HDS駆動ミニドラ"]

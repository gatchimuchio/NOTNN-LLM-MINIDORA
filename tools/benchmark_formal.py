from __future__ import annotations

"""HDS駆動v1 + 能力経路v2を使うリポジトリ標準ベンチ入口。

既存 ``tools/benchmark.py`` のData取得・保存・controlled A/B実装は再利用する。
候補調停規則は ``src/minidora/hds適応候補調停.py`` を正本とし、
R/C能力経路は ``src/minidora/hds能力経路_v2.py`` を正本とする。
このファイルにはベンチ固有の正解規則を持たせない。
"""

from dataclasses import replace

import benchmark as _benchmark
import gpqa_measure_current as _gpqa

from minidora.hds_choice_runtime import HDS選択推論実行 as _HDS選択推論実行
from minidora.hds統合runtime import HDS駆動選択実行
from minidora.hds能力経路_v2 import HDS参照検索V2
from minidora.hds適応候補調停 import HDS適応候補提案実行
from minidora.能力状態差循環 import 標準能力模型核


class _ベンチHDS環境:
    """取得済み参照DataをHDS駆動v1へ渡す最小環境。"""

    def __init__(self, コンパイル, 基礎能力核, 能力模型核) -> None:
        self.コンパイル = コンパイル
        self.K3能力核 = 基礎能力核
        self.能力模型核 = 能力模型核
        self.参照供給器 = None


def _正式HDS選択推論実行(*args, **kwargs):
    # controlled baselineは従来どおり同一質問IR・同一取得資料の旧helperを使う。
    legacy_baseline = (
        kwargs.get("作業再作用") is False
        and kwargs.get("局所再照合") is False
    )
    if legacy_baseline:
        return _HDS選択推論実行(*args, **kwargs)

    if len(args) < 2:
        raise TypeError("HDS駆動ベンチ経路は question_ir と references を必要とする")
    question_ir = args[0]
    references = tuple(args[1])
    コンパイル = kwargs.get("コンパイル")
    基礎能力核 = kwargs.get("基礎能力核")
    if コンパイル is None or 基礎能力核 is None:
        raise TypeError("HDS駆動ベンチ経路は コンパイル と 基礎能力核 を必要とする")

    environment = _ベンチHDS環境(コンパイル, 基礎能力核, 標準能力模型核())
    driven = HDS駆動選択実行(
        environment,
        question_ir,
        参照必須=bool(getattr(question_ir, "参照必須", False)),
        参照実行=lambda _ir: references,
        評価実行=lambda ir, refs: HDS適応候補提案実行(
            ir,
            tuple(refs),
            コンパイル=コンパイル,
            基礎能力核=基礎能力核,
            模型核=environment.能力模型核,
        ),
    )

    selected = driven.選択
    if driven.状態 == "APPROVE":
        return replace(selected, 状態="APPROVE", 理由=driven.理由)
    return replace(
        selected,
        状態="SUSPEND",
        回答ラベル=None,
        回答内容=None,
        理由=driven.理由,
    )


# GPQA取得も正式runtimeと同じR v2へ揃える。current/baselineは同一取得資料を共有する。
_gpqa.HDS参照検索 = HDS参照検索V2
_gpqa.HDS選択推論実行 = _正式HDS選択推論実行


_original_result_payload = _benchmark._result_payload


def _正式_result_payload(*args, **kwargs):
    payload = _original_result_payload(*args, **kwargs)
    protocol = payload.setdefault("protocol", {})
    protocol["runtime"] = "current repository checkout; R-v2 candidate coverage→HDS駆動v1→C-v2 observation-change evaluation→adaptive arbitration→J_hds COMMIT/SUSPEND"
    protocol["formal_model_core"] = True
    protocol["hds_judgement_subject"] = "v1-bounded-domain-projection"
    protocol["candidate_commit_separation"] = "PROPOSE != COMMIT"
    protocol["reference_route"] = "generic primary後も候補query被覆不足を検査し、未被覆候補だけtargeted fallback。candidate sourceを対称にfloor保持。gold非参照"
    protocol["capability_route"] = "同Dataの候補縮小再投票を禁止。同source local viewという実観測表現変化時だけ全候補再評価し、強い再評価だけ採用"
    protocol["adaptive_selection"] = "専門作用実消費またはlocal/new-reference実観測変化を経た能力PROPOSEだけを優先。raw candidate_cross_updates単独は不採用。未成立時は同一Dataの基礎経路。gold非参照"
    protocol["adaptive_selection_source"] = "src/minidora/hds適応候補調停.py"
    protocol["capability_route_source"] = "src/minidora/hds能力経路_v2.py"
    protocol["capability_projection"] = "日本語基底・観測変化起動能力作用 v2"
    if protocol.get("controlled_ab"):
        protocol["controlled_ab_definition"] = "同一質問IR・同一R-v2取得資料。baseline=旧v0.3 helperで作業再作用/局所再照合なし、current=HDS駆動v1 + 能力経路v2 + 実観測変化適応調停"
    return payload


_benchmark._result_payload = _正式_result_payload


if __name__ == "__main__":
    raise SystemExit(_benchmark.main())

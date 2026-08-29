from __future__ import annotations

"""HDS駆動v1を使うリポジトリ標準ベンチ入口。

既存 ``tools/benchmark.py`` のData取得・保存・controlled A/B実装は再利用する。
currentでは、候補生成をCOMMITから分離したHDS Judgement Subjectを通し、
状態差の成立状況に応じて能力経路と基礎経路を調停する。

正解ラベルは推論経路へ渡さない。
"""

from dataclasses import replace

import benchmark as _benchmark
import gpqa_measure_current as _gpqa

from minidora.hds_choice_runtime import HDS選択実行結果, HDS選択推論実行 as _HDS選択推論実行
from minidora.hds候補提案runtime import HDS候補提案実行
from minidora.hds統合runtime import HDS駆動選択実行
from minidora.能力状態差循環 import 標準能力模型核


class _ベンチHDS環境:
    """取得済み参照DataをHDS駆動v1へ渡す最小環境。"""

    def __init__(self, コンパイル, 基礎能力核, 能力模型核) -> None:
        self.コンパイル = コンパイル
        self.K3能力核 = 基礎能力核
        self.能力模型核 = 能力模型核
        self.参照供給器 = None


def _基礎結果を提案化(result: HDS選択実行結果, reason: str) -> HDS選択実行結果:
    if result.状態 != "APPROVE" or result.回答ラベル is None or result.回答内容 is None:
        return result
    return replace(
        result,
        状態="PROPOSE",
        理由=tuple(dict.fromkeys(tuple(result.理由) + (reason, "CANDIDATE_GENERATION_HAS_NO_COMMIT_AUTHORITY"))),
    )


def _適応候補提案(question_ir, references, *, コンパイル, 基礎能力核) -> HDS選択実行結果:
    """状態差成立度を見て、二つの候補生成workerを調停する。

    規則はケース固有ラベルやgoldを参照しない。

    - 二段目の候補横断更新まで成立した能力経路は、その新状態差を採用理由として優先する。
    - そこまで成立しない場合、基礎経路が閉じるなら安定側の提案を使う。
    - 二段差分も基礎閉包も無い場合は、primary単独提案を救済せずSUSPENDする。
    """

    primary = HDS候補提案実行(
        question_ir,
        tuple(references),
        コンパイル=コンパイル,
        基礎能力核=基礎能力核,
        模型核=標準能力模型核(),
    )

    if primary.状態 == "PROPOSE" and primary.候補横断更新数 > 0:
        return replace(
            primary,
            理由=tuple(dict.fromkeys(tuple(primary.理由) + (
                "HDS_ADAPTIVE_PRIMARY_SELECTED",
                "SECOND_ORDER_STATE_DIFFERENCE_SUPPORTED",
            ))),
        )

    base = _HDS選択推論実行(
        question_ir,
        tuple(references),
        コンパイル=コンパイル,
        基礎能力核=基礎能力核,
        作業再作用=False,
        局所再照合=False,
    )
    base_proposal = _基礎結果を提案化(base, "HDS_ADAPTIVE_BASE_SELECTED")
    if base_proposal.状態 == "PROPOSE":
        return base_proposal

    reasons = tuple(dict.fromkeys(
        tuple(primary.理由)
        + tuple(base.理由)
        + ("HDS_ADAPTIVE_NO_COMMITTABLE_PROPOSAL", "PRIMARY_WITHOUT_SECOND_ORDER_SUPPORT_NOT_COMMITTED")
    ))
    return replace(
        primary,
        状態="SUSPEND",
        回答ラベル=None,
        回答内容=None,
        理由=reasons,
    )


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
        評価実行=lambda ir, refs: _適応候補提案(
            ir,
            refs,
            コンパイル=コンパイル,
            基礎能力核=基礎能力核,
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


_gpqa.HDS選択推論実行 = _正式HDS選択推論実行


_original_result_payload = _benchmark._result_payload


def _正式_result_payload(*args, **kwargs):
    payload = _original_result_payload(*args, **kwargs)
    protocol = payload.setdefault("protocol", {})
    protocol["runtime"] = "current repository checkout; fixed R→HDS駆動v1→adaptive candidate workers→J_hds COMMIT/SUSPEND"
    protocol["formal_model_core"] = True
    protocol["hds_judgement_subject"] = "v1-bounded-domain-projection"
    protocol["candidate_commit_separation"] = "PROPOSE != COMMIT"
    protocol["adaptive_selection"] = "二段候補横断更新が成立した能力経路を優先。未成立時は同一Dataの基礎経路だけを監査候補として使用。双方未閉包ならSUSPEND。gold非参照"
    protocol["capability_projection"] = "日本語基底・状態差起動能力作用 v1"
    if protocol.get("controlled_ab"):
        protocol["controlled_ab_definition"] = "同一質問IR・同一取得資料。baseline=旧v0.3 helperで作業再作用/局所再照合なし、current=HDS駆動v1による状態差適応調停"
    return payload


_benchmark._result_payload = _正式_result_payload


if __name__ == "__main__":
    raise SystemExit(_benchmark.main())

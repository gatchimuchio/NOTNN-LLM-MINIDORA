from __future__ import annotations

"""HDS監督介入制御 v1 を使うリポジトリ標準GPQAベンチ入口。

測定差分をHDS制御だけへ限定するため、controlled A/Bは次で固定する。

- baseline: 同一初期Rを使い、既存MINIDORAのK3/direct/Working/local/能力模型を全て実行する。
- current : 同一初期Rから開始し、HDS監督制御が未閉包時だけ既存作用を選択する。追加RはHDS効果として許可する。

HDSは回答ラベル・候補得点を判断入力として受け取らない。goldは双方の推論後の採点だけに使う。
"""

from collections import Counter

import benchmark as _benchmark
import gpqa_measure_current as _gpqa

from minidora.hds_choice_runtime import HDS選択実行結果
from minidora.hds_reference import HDS参照検索 as _標準初期参照検索
from minidora.hds介入制御 import 既存作用, 標準HDS介入制御
from minidora.hds監督選択runtime import HDS監督選択実行, _Session
from minidora.能力状態差循環 import 標準能力模型核


_現在Provider = None


def _監督初期参照検索(provider, ir, **kwargs):
    """製品runtimeと同じ標準初期Rを使い、currentの追加R用Providerだけ保持する。"""
    global _現在Provider
    _現在Provider = provider
    return _標準初期参照検索(provider, ir, **kwargs)


def _既存全能力baseline(
    question_ir,
    references,
    *,
    コンパイル,
    基礎能力核,
) -> HDS選択実行結果:
    """HDSなしで既存能力群を全実行するcontrolled baseline。

    HDSに作用選択させず、K3/directの初回評価・能力模型・Working・localを全て同じ初期Dataへ
    実行する。追加Rは行わない。最終候補は既存MINIDORA resolverだけが解決する。
    """
    session = _Session(
        question_ir,
        tuple(references),
        コンパイル=コンパイル,
        基礎能力核=基礎能力核,
        模型核=標準能力模型核(),
        参照供給器=None,
    )
    session.evaluate_base()
    session.run_action(既存作用.作業再作用)
    session.run_action(既存作用.局所再照合)
    return session.final_result(
        records=(),
        stop_reasons=("BENCH_BASELINE_FULL_EXISTING_MINIDORA_CAPABILITIES",),
    )


def _監督HDS選択推論実行(*args, **kwargs):
    if len(args) < 2:
        raise TypeError("監督制御ベンチ経路は question_ir と references を必要とする")
    question_ir = args[0]
    references = tuple(args[1])
    コンパイル = kwargs.get("コンパイル")
    基礎能力核 = kwargs.get("基礎能力核")
    if コンパイル is None or 基礎能力核 is None:
        raise TypeError("監督制御ベンチ経路は コンパイル と 基礎能力核 を必要とする")

    controlled_baseline = (
        kwargs.get("作業再作用") is False
        and kwargs.get("局所再照合") is False
    )
    if controlled_baseline:
        return _既存全能力baseline(
            question_ir,
            references,
            コンパイル=コンパイル,
            基礎能力核=基礎能力核,
        )

    supervised = HDS監督選択実行(
        question_ir,
        references,
        コンパイル=コンパイル,
        基礎能力核=基礎能力核,
        模型核=標準能力模型核(),
        参照供給器=_現在Provider,
        HDS制御=標準HDS介入制御(),
        HDS介入予算=6,
    )
    return supervised.選択


_gpqa.HDS参照検索 = _監督初期参照検索
_gpqa.HDS選択推論実行 = _監督HDS選択推論実行


_original_result_payload = _benchmark._result_payload


def _介入統計(details):
    total = 0
    cases = 0
    actions: Counter[str] = Counter()
    for row in details:
        found = 0
        for reason in row.get("reasons", []):
            text = str(reason)
            if text.startswith("HDS_SUPERVISORY_INTERVENTIONS:"):
                try:
                    found = int(text.rsplit(":", 1)[1])
                except ValueError:
                    found = 0
            elif text.startswith("HDS_INTERVENTION_ACTION:"):
                actions[text.split(":", 1)[1]] += 1
        total += found
        cases += int(found > 0)
    return total, cases, dict(sorted(actions.items()))


def _監督_result_payload(*args, **kwargs):
    payload = _original_result_payload(*args, **kwargs)
    protocol = payload.setdefault("protocol", {})
    protocol["runtime"] = "current repository checkout; existing MINIDORA + HDS supervisory intervention control v1"
    protocol["hds_role"] = "既存MINIDORAの未閉包状態を観測し、既存作用の起動・再起動・停止だけを制御。回答生成・候補勝者選択・最終HDSラッパーなし"
    protocol["initial_reference_route"] = "製品runtimeと同じ標準HDS参照検索"
    protocol["current_additional_reference"] = "HDSが観測不足等を検出した場合だけ追加Rを許可し、追加観測もHDS効果として測定"
    protocol["candidate_resolution"] = "existing MINIDORA capability resolver; HDS does not receive answer labels or candidate scores"
    protocol["formal_model_core"] = False
    protocol["final_hds_judgement_wrapper"] = False
    protocol["gold_boundary"] = "gold used only after baseline/current inference for scoring"
    if protocol.get("controlled_ab"):
        protocol["controlled_ab_definition"] = (
            "same question IR + same initial retrieved references. "
            "baseline=existing MINIDORA full capabilities (K3/direct/Working/local/capability model), no HDS and no additional R; "
            "current=same initial state + HDS supervisory intervention, with additional R allowed only when HDS requests it"
        )

    details = payload.get("details", [])
    interventions, intervention_cases, action_counts = _介入統計(details)
    metrics = payload.setdefault("metrics", {})
    metrics["hds_supervisory_interventions"] = interventions
    metrics["hds_intervention_cases"] = intervention_cases
    metrics["hds_intervention_action_counts"] = action_counts
    return payload


_benchmark._result_payload = _監督_result_payload


if __name__ == "__main__":
    raise SystemExit(_benchmark.main())

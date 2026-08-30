from __future__ import annotations

"""HDS安全弁を使うリポジトリ標準GPQAベンチ入口。

controlled A/Bでは同じ質問IR・同じ初期R・同じ通常MINIDORA初期結果を共有する。
baselineはHDS非介入の通常MINIDORA、currentはその結果が未閉包の時だけHDS安全弁を作動させる。
"""

from collections import Counter

import benchmark as _benchmark
import gpqa_measure_current as _gpqa

from minidora.hds_choice_runtime import HDS選択実行結果
from minidora.hds_reference import HDS参照検索 as _標準初期参照検索
from minidora.hds介入制御 import 標準HDS介入制御
from minidora.hds監督選択runtime import HDS監督選択実行
from minidora.能力状態差循環 import 標準能力模型核


_現在Provider = None
_通常MINIDORA選択推論 = _gpqa.HDS選択推論実行
_直前baseline_key = None
_直前baseline_result: HDS選択実行結果 | None = None


def _baseline_key(question_ir, references):
    return (
        id(question_ir),
        tuple((r.識別子, r.信頼, r.条件) for r in references),
    )


def _監督初期参照検索(provider, ir, **kwargs):
    """初期RはHDS投入前MINIDORAと同じ標準経路を使う。追加R用Providerだけ保持する。"""
    global _現在Provider
    _現在Provider = provider
    return _標準初期参照検索(provider, ir, **kwargs)


def _通常MINIDORA推論(
    question_ir,
    references,
    *,
    コンパイル,
    基礎能力核,
) -> HDS選択実行結果:
    """HDS安全弁を含まない通常MINIDORA選択をそのまま実行する。"""
    return _通常MINIDORA選択推論(
        question_ir,
        tuple(references),
        コンパイル=コンパイル,
        基礎能力核=基礎能力核,
    )


def _監督HDS選択推論実行(*args, **kwargs):
    global _直前baseline_key, _直前baseline_result

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
    key = _baseline_key(question_ir, references)

    if controlled_baseline:
        baseline = _通常MINIDORA推論(
            question_ir,
            references,
            コンパイル=コンパイル,
            基礎能力核=基礎能力核,
        )
        _直前baseline_key = key
        _直前baseline_result = baseline
        return baseline

    if _直前baseline_key == key and _直前baseline_result is not None:
        initial = _直前baseline_result
        _直前baseline_key = None
        _直前baseline_result = None
    else:
        initial = _通常MINIDORA推論(
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
        初期選択=initial,
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
    protocol["runtime"] = "current repository checkout; normal MINIDORA feedback loop + HDS safety valve on anomaly only"
    protocol["hds_role"] = "通常MINIDORAを俯瞰監視し、未閉包・競合・観測不足等の異常時だけ既存作用を起動。正常推論は完全透過"
    protocol["initial_reference_route"] = "HDS投入前と同じ標準HDS参照検索。追加RはHDS介入時だけ"
    protocol["current_additional_reference"] = "HDSが観測不足等を検出した場合だけ追加Rを許可"
    protocol["candidate_resolution"] = "normal MINIDORA selection only; no supervisory resolver and no HDS winner selection"
    protocol["formal_model_core"] = False
    protocol["final_hds_judgement_wrapper"] = False
    protocol["gold_boundary"] = "gold used only after baseline/current inference for scoring"
    protocol["non_intervention_invariant"] = "HDS interventions=0 => current selection object is the exact normal MINIDORA baseline result"
    if protocol.get("controlled_ab"):
        protocol["controlled_ab_definition"] = (
            "same question IR + same initial retrieved references + same initial normal MINIDORA result. "
            "baseline=normal MINIDORA without HDS intervention; "
            "current=exact baseline result when closed, otherwise HDS-triggered existing actions followed by normal MINIDORA re-evaluation"
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

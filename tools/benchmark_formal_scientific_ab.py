from __future__ import annotations

"""現行正式GPQA経路に既存科学専門能力だけを重ねるcontrolled A/B入口。

baseline:
    現行 ``tools/benchmark_formal.py`` の正式MINIDORA + HDS安全弁。

current:
    baselineと同じ質問IR・同じ取得参照に対して、リポジトリ既存の
    ``科学専門能力を通常MINIDORAへ接続`` を先に適用する。
    科学専門能力が一意かつ絶対支持できなければ、baselineで得た同一選択結果を
    そのまま返す。したがって差分は科学専門能力の発火だけに限定される。

GPQAのgoldは ``tools/benchmark.py`` が両推論完了後に採点へだけ使う。
"""

from collections import Counter
from types import ModuleType

import benchmark as _benchmark
import benchmark_formal as _formal
import gpqa_measure_current as _gpqa

import minidora.hds_choice_runtime as _choice_runtime
from minidora.科学専門能力統合 import 科学専門能力を通常MINIDORAへ接続


_正式現行推論 = _formal._監督HDS選択推論実行
_直前baseline_key = None
_直前baseline_result = None


def _pair_key(question_ir, references):
    return (
        id(question_ir),
        tuple((r.識別子, r.信頼, r.条件) for r in references),
    )


def _正式現行を実行(question_ir, references, *, コンパイル, 基礎能力核):
    """benchmark_formalのcurrent側を明示的に実行する。"""
    return _正式現行推論(
        question_ir,
        tuple(references),
        コンパイル=コンパイル,
        基礎能力核=基礎能力核,
        作業再作用=True,
        局所再照合=True,
    )


def _baseline透過(question_ir, references, *args, **kwargs):
    """科学専門能力が不発火なら、直前baselineを同一オブジェクトで返す。"""
    global _直前baseline_key, _直前baseline_result
    key = _pair_key(question_ir, references)
    if _直前baseline_key == key and _直前baseline_result is not None:
        return _直前baseline_result

    コンパイル = kwargs.get("コンパイル")
    基礎能力核 = kwargs.get("基礎能力核")
    if コンパイル is None or 基礎能力核 is None:
        raise TypeError("科学専門能力A/B経路は コンパイル と 基礎能力核 を必要とする")
    return _正式現行を実行(
        question_ir,
        references,
        コンパイル=コンパイル,
        基礎能力核=基礎能力核,
    )


_科学能力runtime = ModuleType("minidora_scientific_specialist_ab_runtime")
_科学能力runtime.HDS選択推論実行 = _baseline透過
_科学能力runtime.HDS選択問題 = _choice_runtime.HDS選択問題
_科学能力runtime.HDS選択実行結果 = _choice_runtime.HDS選択実行結果
科学専門能力を通常MINIDORAへ接続(_科学能力runtime)
_科学専門能力付き推論 = _科学能力runtime.HDS選択推論実行


def _科学専門能力AB選択推論実行(*args, **kwargs):
    global _直前baseline_key, _直前baseline_result

    if len(args) < 2:
        raise TypeError("科学専門能力A/B経路は question_ir と references を必要とする")
    question_ir = args[0]
    references = tuple(args[1])
    コンパイル = kwargs.get("コンパイル")
    基礎能力核 = kwargs.get("基礎能力核")
    if コンパイル is None or 基礎能力核 is None:
        raise TypeError("科学専門能力A/B経路は コンパイル と 基礎能力核 を必要とする")

    controlled_baseline = (
        kwargs.get("作業再作用") is False
        and kwargs.get("局所再照合") is False
    )
    key = _pair_key(question_ir, references)

    if controlled_baseline:
        baseline = _正式現行を実行(
            question_ir,
            references,
            コンパイル=コンパイル,
            基礎能力核=基礎能力核,
        )
        _直前baseline_key = key
        _直前baseline_result = baseline
        return baseline

    if _直前baseline_key != key or _直前baseline_result is None:
        _直前baseline_key = key
        _直前baseline_result = _正式現行を実行(
            question_ir,
            references,
            コンパイル=コンパイル,
            基礎能力核=基礎能力核,
        )

    try:
        return _科学専門能力付き推論(
            question_ir,
            references,
            コンパイル=コンパイル,
            基礎能力核=基礎能力核,
        )
    finally:
        _直前baseline_key = None
        _直前baseline_result = None


# benchmark.pyが既に参照しているgpqa名前空間だけを差し替える。
# benchmark_formal本体や通常runtimeの実装は変更しない。
_gpqa.HDS選択推論実行 = _科学専門能力AB選択推論実行


_original_result_payload = _benchmark._result_payload


def _科学solver統計(details):
    counts: Counter[str] = Counter()
    fired_cases = 0
    exact_fallback_cases = 0
    prefix = "SCIENTIFIC_CAPABILITY_SOLVER:"
    for row in details:
        reasons = tuple(str(x) for x in row.get("reasons", []))
        solver = None
        for reason in reasons:
            if reason.startswith(prefix):
                solver = reason[len(prefix):]
                break
        if solver is not None:
            counts[solver] += 1
            fired_cases += 1
        elif (
            row.get("predicted") == row.get("baseline_predicted")
            and row.get("status") == row.get("baseline_status")
        ):
            exact_fallback_cases += 1
    return dict(sorted(counts.items())), fired_cases, exact_fallback_cases


def _科学専門能力_result_payload(*args, **kwargs):
    payload = _original_result_payload(*args, **kwargs)
    protocol = payload.setdefault("protocol", {})
    protocol["runtime"] = "current formal MINIDORA + HDS safety valve; repo-native scientific capability controlled A/B"
    protocol["candidate_resolution"] = (
        "baseline=current formal MINIDORA. specialist_on=existing scientific capability may close only a uniquely and absolutely supported candidate; otherwise exact baseline result is returned"
    )
    protocol["specialist_source"] = "existing src/minidora/科学専門能力*.py via 科学専門能力を通常MINIDORAへ接続; no new GPQA solver in this wrapper"
    protocol["gold_boundary"] = "gold used only after baseline and specialist_on inference for scoring"
    protocol["non_intervention_invariant"] = "scientific specialist not fired => specialist_on returns the exact baseline selection object"
    if protocol.get("controlled_ab"):
        protocol["controlled_ab_definition"] = (
            "same question IR + exact same initial retrieved references. "
            "baseline=current formal MINIDORA with HDS safety valve. "
            "specialist_on=repo-native scientific capability first; if it cannot uniquely and absolutely support one candidate, return exact baseline selection object."
        )

    details = payload.get("details", [])
    solver_counts, fired_cases, exact_fallback_cases = _科学solver統計(details)
    payload["scientific_specialist"] = {
        "fired_cases": fired_cases,
        "exact_fallback_cases": exact_fallback_cases,
        "solver_counts": solver_counts,
    }
    return payload


_benchmark._result_payload = _科学専門能力_result_payload


if __name__ == "__main__":
    raise SystemExit(_benchmark.main())

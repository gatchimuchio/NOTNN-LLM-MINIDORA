from __future__ import annotations

"""MINIDORA能力主体C + HDS判断主体Jを使うリポジトリ標準ベンチ入口。

既存 ``tools/benchmark.py`` のData取得・保存・controlled A/B実装は再利用し、
推論関数だけを現行正式経路へ固定する。
"""

import benchmark as _benchmark
import gpqa_measure_current as _gpqa

from minidora.hds_choice_runtime import HDS選択推論実行 as _HDS選択推論実行
from minidora.能力状態差循環 import 標準能力模型核


def _正式HDS選択推論実行(*args, **kwargs):
    # controlled A/Bでは同一参照資料で旧helperと現行能力経路の差を測る。
    legacy_baseline = (
        kwargs.get("作業再作用") is False
        and kwargs.get("局所再照合") is False
    )
    kwargs["正式模型評価"] = not legacy_baseline
    if not legacy_baseline:
        kwargs["模型核"] = 標準能力模型核()
    return _HDS選択推論実行(*args, **kwargs)


_gpqa.HDS選択推論実行 = _正式HDS選択推論実行


_original_result_payload = _benchmark._result_payload


def _正式_result_payload(*args, **kwargs):
    payload = _original_result_payload(*args, **kwargs)
    protocol = payload.setdefault("protocol", {})
    protocol["runtime"] = "current repository checkout; R→HDS意味構造/作用差分→MINIDORA能力主体C→HDS判断主体J"
    protocol["formal_model_core"] = True
    protocol["hds_judgement_subject"] = True
    protocol["capability_projection"] = "日本語基底・状態差起動能力作用 v1"
    if protocol.get("controlled_ab"):
        protocol["controlled_ab_definition"] = "同一質問IR・同一取得資料。baseline=旧v0.3 helperで作業再作用/局所再照合なし、current=状態差起動MINIDORA C + HDS J"
    return payload


_benchmark._result_payload = _正式_result_payload


if __name__ == "__main__":
    raise SystemExit(_benchmark.main())

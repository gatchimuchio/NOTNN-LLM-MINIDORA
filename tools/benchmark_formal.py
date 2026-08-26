from __future__ import annotations

"""MINIDORA正式模型核を使うリポジトリ標準ベンチ入口。

既存`tools/benchmark.py`のデータ取得・checkpoint・controlled A/B実装は再利用し、
推論関数だけをv0.4正式模型核へ固定する。GitHub Actionsと手動測定はこの入口を使う。
"""

import benchmark as _benchmark
import gpqa_measure_current as _gpqa

from minidora.hds_choice_runtime import HDS選択推論実行 as _HDS選択推論実行
from minidora.模型 import 標準模型核


def _正式HDS選択推論実行(*args, **kwargs):
    # controlled A/Bでは同一R資料で legacy v0.3 helper と正式模型核の経路差を測る。
    legacy_baseline = (
        kwargs.get("作業再作用") is False
        and kwargs.get("局所再照合") is False
    )
    kwargs["正式模型評価"] = not legacy_baseline
    if not legacy_baseline:
        # ベンチ入口ではhelper側への隠し属性注入に依存せず、正式模型核を明示注入する。
        kwargs["模型核"] = 標準模型核()
    return _HDS選択推論実行(*args, **kwargs)


# benchmark.pyは同じmodule objectを参照するため、推論入口だけを正式模型核へ差し替えられる。
_gpqa.HDS選択推論実行 = _正式HDS選択推論実行


_original_result_payload = _benchmark._result_payload


def _正式_result_payload(*args, **kwargs):
    payload = _original_result_payload(*args, **kwargs)
    protocol = payload.setdefault("protocol", {})
    protocol["runtime"] = "current repository checkout; R->HDS semantic IR->MINIDORA formal model core; legacy K3 helper diagnostic-only"
    protocol["formal_model_core"] = True
    protocol["capability_projection"] = "LLM action-law projection v1"
    if protocol.get("controlled_ab"):
        protocol["controlled_ab_definition"] = "same question IR + same retrieved references; baseline=legacy v0.3 helper with working/local off; current=formal MINIDORA model core only"
    return payload


_benchmark._result_payload = _正式_result_payload


if __name__ == "__main__":
    raise SystemExit(_benchmark.main())

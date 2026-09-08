from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any


CONTRACT_SCHEMA = "minidora.benchmark.contract.v1"
GPQA_E2E_LIVE_ID = "gpqa-diamond-e2e-live-v1"
GPQA_FIXED_REPLAY_ID = "gpqa-diamond-fixed-replay-v1"


def _canonical_sha256(payload: Any) -> str:
    raw = json.dumps(
        payload,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
    return hashlib.sha256(raw).hexdigest()


def _file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def gpqa_e2e_live_contract(protocol: dict[str, Any]) -> dict[str, Any]:
    condition = {
        "dataset_csv_sha256": protocol.get("dataset_csv_sha256"),
        "selected_indices": protocol.get("selected_indices"),
        "choice_shuffle_seed": protocol.get("choice_shuffle_seed"),
        "openalex_enabled": bool(protocol.get("openalex_enabled")),
        "wikipedia_languages": protocol.get("wikipedia_languages", []),
        "compiler": protocol.get("compiler"),
        "runtime": protocol.get("runtime"),
        "initial_reference_route": protocol.get("initial_reference_route"),
        "current_additional_reference": protocol.get("current_additional_reference"),
    }
    return {
        "schema": CONTRACT_SCHEMA,
        "benchmark_id": GPQA_E2E_LIVE_ID,
        "task": "GPQA Diamond",
        "evaluation_class": "GENERIC_E2E_SNAPSHOT",
        "input_boundary": "question + choices + references retrieved at execution time",
        "retrieval_mode": "LIVE",
        "condition_fingerprint_sha256": _canonical_sha256(condition),
        "input_snapshot_sha256": None,
        "within_run_controlled_ab_direct": True,
        "cross_run_code_delta_direct": False,
        "claim_scope": [
            "汎用E2E経路を、その実行時点の参照取得環境を含めて測ったスナップショット",
            "同一run内controlled A/Bは同一取得資料を共有するため直接差分として扱える",
        ],
        "forbidden_claims": [
            "異なる日時のLIVE run間の得点差をコード変更だけの因果差とみなすこと",
            "FIXED_REPLAYの得点を汎用E2E性能として読み替えること",
        ],
    }


def fixed_replay_contract(input_path: Path, *, task: str = "GPQA Diamond") -> dict[str, Any]:
    bundle_hash = _file_sha256(input_path)
    return {
        "schema": CONTRACT_SCHEMA,
        "benchmark_id": GPQA_FIXED_REPLAY_ID,
        "task": task,
        "evaluation_class": "FIXED_REPLAY_DELTA",
        "input_boundary": "frozen question + choices + reference/Data bundle",
        "retrieval_mode": "FROZEN_REPLAY",
        "condition_fingerprint_sha256": bundle_hash,
        "input_snapshot_sha256": bundle_hash,
        "within_run_controlled_ab_direct": True,
        "cross_run_code_delta_direct": True,
        "claim_scope": [
            "同一固定入力に対する実装差分・回帰差分",
        ],
        "forbidden_claims": [
            "固定Replay得点を未知参照環境を含む汎用E2E性能として主張すること",
        ],
    }


def direct_comparison_verdict(left: dict[str, Any], right: dict[str, Any]) -> tuple[bool, str]:
    l = left.get("benchmark_contract") or left
    r = right.get("benchmark_contract") or right
    if l.get("schema") != CONTRACT_SCHEMA or r.get("schema") != CONTRACT_SCHEMA:
        return False, "benchmark contract v1が両結果に存在しない"
    if l.get("benchmark_id") != r.get("benchmark_id"):
        return False, "benchmark_idが異なる"
    if l.get("evaluation_class") != r.get("evaluation_class"):
        return False, "evaluation_classが異なる"
    if l.get("evaluation_class") == "FIXED_REPLAY_DELTA":
        if not l.get("input_snapshot_sha256") or l.get("input_snapshot_sha256") != r.get("input_snapshot_sha256"):
            return False, "固定Replayのinput snapshot hashが一致しない"
        return True, "同一固定入力なので実装差分を直接比較できる"
    if l.get("evaluation_class") == "GENERIC_E2E_SNAPSHOT":
        return False, "LIVE参照取得を含むため別run間をコード変更だけの直接差分にはできない"
    return False, "未知のevaluation_class"


def attach_contract(result: dict[str, Any], contract: dict[str, Any]) -> dict[str, Any]:
    out = dict(result)
    out["benchmark_contract"] = contract
    return out

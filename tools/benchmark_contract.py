from __future__ import annotations

import hashlib
import json
from typing import Any


CONTRACT_SCHEMA = "minidora.benchmark.contract.v2"
GPQA_E2E_LIVE_ID = "gpqa-diamond-e2e-live-v2"
GPQA_CANONICAL_TOTAL = 198
GPQA_CANONICAL_DATASET_CSV_SHA256 = "41d1213cd7a4998605a26c2798500652572007161b3a92817ba46b35befcd305"
GPQA_CANONICAL_CHOICE_SHUFFLE_SEED = 0
GPQA_CANONICAL_OPENALEX_ENABLED = False
GPQA_CANONICAL_WIKIPEDIA_LANGUAGES = ("en",)


def _canonical_sha256(payload: Any) -> str:
    raw = json.dumps(
        payload,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
    return hashlib.sha256(raw).hexdigest()


def validate_gpqa_canonical_protocol(protocol: dict[str, Any]) -> tuple[str, ...]:
    """GPQA正本E2Eの外部評価条件を検査する。

    固定するのは問題集合・seed・参照経路の構成であり、検索結果そのものではない。
    参照結果をrun間で固定・再生することは正本GPQAでは禁止する。
    """
    errors: list[str] = []
    if protocol.get("dataset_csv_sha256") != GPQA_CANONICAL_DATASET_CSV_SHA256:
        errors.append("GPQA dataset hashが正本値と一致しない")
    if protocol.get("full_benchmark_total") != GPQA_CANONICAL_TOTAL:
        errors.append("GPQA総問題数が198ではない")
    if protocol.get("selected_indices") != list(range(GPQA_CANONICAL_TOTAL)):
        errors.append("GPQA正本は198/198全数実行でなければならない")
    if protocol.get("choice_shuffle_seed") != GPQA_CANONICAL_CHOICE_SHUFFLE_SEED:
        errors.append("choice shuffle seedが0ではない")
    if bool(protocol.get("openalex_enabled")) != GPQA_CANONICAL_OPENALEX_ENABLED:
        errors.append("OpenAlex条件が正本条件と一致しない")
    if tuple(protocol.get("wikipedia_languages", ())) != GPQA_CANONICAL_WIKIPEDIA_LANGUAGES:
        errors.append("Wikipedia言語条件が正本条件と一致しない")
    if not bool(protocol.get("controlled_ab")):
        errors.append("正本GPQAは同一run内controlled A/Bを必須とする")
    return tuple(errors)


def gpqa_e2e_live_contract(protocol: dict[str, Any]) -> dict[str, Any]:
    errors = validate_gpqa_canonical_protocol(protocol)
    if errors:
        raise ValueError("; ".join(errors))

    condition = {
        "dataset_csv_sha256": protocol.get("dataset_csv_sha256"),
        "full_benchmark_total": protocol.get("full_benchmark_total"),
        "selected_indices": protocol.get("selected_indices"),
        "choice_shuffle_seed": protocol.get("choice_shuffle_seed"),
        "openalex_enabled": bool(protocol.get("openalex_enabled")),
        "wikipedia_languages": protocol.get("wikipedia_languages", []),
        "controlled_ab": bool(protocol.get("controlled_ab")),
        "retrieval_mode": "LIVE_ONLY",
    }
    return {
        "schema": CONTRACT_SCHEMA,
        "benchmark_id": GPQA_E2E_LIVE_ID,
        "task": "GPQA Diamond",
        "evaluation_class": "GENERIC_E2E_CANONICAL",
        "input_boundary": "question + choices + references newly retrieved during this run",
        "retrieval_mode": "LIVE_ONLY",
        "fixed_reference_data_allowed": False,
        "condition_fingerprint_sha256": _canonical_sha256(condition),
        "input_snapshot_sha256": None,
        "canonical_full_run": True,
        "canonical_score_field": "metrics.correct",
        "within_run_controlled_ab_direct": True,
        "cross_run_code_delta_direct": False,
        "snapshot_score_chronology_allowed": True,
        "claim_scope": [
            "同一の正本GPQA運用規則で、その実行時点の外部参照環境を含めた汎用E2E性能スナップショット",
            "同一run内controlled A/Bは、そのrunで取得した同一資料を共有するため直接差分として扱える",
            "同一正本運用規則で得た各runの得点は時系列セーブポイントとして保持できる",
        ],
        "forbidden_claims": [
            "保存済み参照結果・C2・Replay bundle等の固定参照DataをGPQA正本性能評価へ利用すること",
            "部分実行値をGPQA正本性能として採用すること",
            "異なる日時のLIVE run間の得点差をコード変更だけの因果差とみなすこと",
        ],
    }


def direct_comparison_verdict(left: dict[str, Any], right: dict[str, Any]) -> tuple[bool, str]:
    l = left.get("benchmark_contract") or left
    r = right.get("benchmark_contract") or right
    if l.get("schema") != CONTRACT_SCHEMA or r.get("schema") != CONTRACT_SCHEMA:
        return False, "benchmark contract v2が両結果に存在しない"
    if l.get("benchmark_id") != r.get("benchmark_id"):
        return False, "benchmark_idが異なる"
    if l.get("evaluation_class") != "GENERIC_E2E_CANONICAL" or r.get("evaluation_class") != "GENERIC_E2E_CANONICAL":
        return False, "GPQA正本以外の評価種別は直接比較対象外"
    if l.get("fixed_reference_data_allowed") is not False or r.get("fixed_reference_data_allowed") is not False:
        return False, "固定参照Dataを許可したGPQA結果は正本比較対象外"
    return False, "LIVE参照取得を含むため別run間をコード変更だけの直接差分にはできない。得点は時系列E2Eセーブポイントとして扱う"


def attach_contract(result: dict[str, Any], contract: dict[str, Any]) -> dict[str, Any]:
    out = dict(result)
    out["benchmark_contract"] = contract
    return out

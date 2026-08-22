from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import urllib.request
import zipfile
from collections import Counter
from pathlib import Path
from typing import Any

import gpqa_measure_current as gpqa


BENCHMARKS = {
    "gpqa-diamond": {
        "description": "GPQA Diamond 198問。現行MINIDORAのR→HDS→K→Jを実測する。",
        "full_total": 198,
        "comparison": {
            "model": "Kimi K3",
            "score_percent": 93.5,
            "source": "https://huggingface.co/moonshotai/Kimi-K3/blob/main/.eval_results/gpqa.yaml",
            "verified_date_jst": "2026-08-23",
        },
    },
}


def _標準入出力をUTF8化() -> None:
    """日本語基底のベンチCLIをOS既定コードページから分離する。"""
    for stream in (sys.stdin, sys.stdout, sys.stderr):
        reconfigure = getattr(stream, "reconfigure", None)
        if reconfigure is not None:
            reconfigure(encoding="utf-8", errors="strict")


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="python tools/benchmark.py",
        description="MINIDORA リポジトリ標準ベンチランナー",
    )
    parser.add_argument("--list", action="store_true", dest="list_mode", help="利用可能なベンチを表示する")
    sub = parser.add_subparsers(dest="benchmark")

    gpqa_parser = sub.add_parser("gpqa-diamond", help=BENCHMARKS["gpqa-diamond"]["description"])
    gpqa_parser.add_argument("--out", type=Path, default=Path("gpqa_current_measurement.json"), help="結果JSON出力先")
    gpqa_parser.add_argument("--cache-dir", type=Path, default=Path(".cache/minidora-bench"), help="ベンチデータのキャッシュ先")
    gpqa_parser.add_argument("--refresh-dataset", action="store_true", help="GPQA dataset.zipを再取得する")
    gpqa_parser.add_argument("--start-index", type=int, default=0, help="0始まりの開始問題番号")
    gpqa_parser.add_argument("--limit", type=int, default=None, help="実行問題数。省略時は末尾まで")
    gpqa_parser.add_argument("--resume", action="store_true", help="同一commit・同一条件の既存outから続行する")
    gpqa_parser.add_argument("--checkpoint-every", type=int, default=1, help="何問ごとに途中結果JSONを書き出すか")
    gpqa_parser.add_argument("--no-openalex", action="store_true", help="OPENALEX_API_KEYが存在してもOpenAlexを使わない")
    return parser


def _git_head() -> str:
    completed = subprocess.run(
        ["git", "rev-parse", "HEAD"],
        text=True,
        encoding="utf-8",
        capture_output=True,
        check=False,
    )
    if completed.returncode != 0:
        return "UNKNOWN"
    return completed.stdout.strip() or "UNKNOWN"


def _atomic_write(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(path.name + ".tmp")
    tmp.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    tmp.replace(path)


def _prepare_gpqa_dataset(cache_dir: Path, *, refresh: bool) -> tuple[Path, str, str]:
    cache_dir.mkdir(parents=True, exist_ok=True)
    archive = cache_dir / "gpqa_dataset.zip"
    if refresh or not archive.exists():
        request = urllib.request.Request(
            gpqa.DATASET_URL,
            headers={"User-Agent": "MINIDORA-Repository-Benchmark/1.0"},
        )
        with urllib.request.urlopen(request, timeout=60) as response, archive.open("wb") as out:
            out.write(response.read())

    zip_hash = gpqa._sha256(archive)
    extract_dir = cache_dir / f"gpqa-{zip_hash[:16]}"
    extract_dir.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(archive) as zf:
        matches = [name for name in zf.namelist() if name.endswith("gpqa_diamond.csv")]
        if len(matches) != 1:
            raise RuntimeError(f"gpqa_diamond.csv not uniquely found: {matches}")
        csv_path = extract_dir / matches[0]
        if not csv_path.exists():
            zf.extract(matches[0], path=extract_dir, pwd=gpqa.DATASET_PASSWORD)
    return csv_path, zip_hash, gpqa._sha256(csv_path)


def _selected_range(total: int, start: int, limit: int | None) -> range:
    if start < 0 or start >= total:
        raise SystemExit(f"--start-index は 0..{total - 1} の範囲で指定してください。")
    if limit is not None and limit <= 0:
        raise SystemExit("--limit は1以上で指定してください。")
    stop = total if limit is None else min(total, start + limit)
    return range(start, stop)


def _load_resume(
    path: Path,
    *,
    selected: range,
    csv_hash: str,
    repository_commit: str,
    openalex_enabled: bool,
) -> dict[int, dict[str, Any]]:
    if not path.exists():
        return {}
    payload = json.loads(path.read_text(encoding="utf-8"))
    protocol = payload.get("protocol", {})
    if protocol.get("dataset_csv_sha256") != csv_hash:
        raise SystemExit("--resume対象のdataset hashが現行GPQAと一致しません。")
    if protocol.get("repository_commit") != repository_commit:
        raise SystemExit("--resume対象のrepository commitが現在のcheckoutと一致しません。")
    if bool(protocol.get("openalex_enabled")) != openalex_enabled:
        raise SystemExit("--resume対象のOpenAlex条件が今回の実行条件と一致しません。")
    expected = list(selected)
    if protocol.get("selected_indices") != expected:
        raise SystemExit("--resume対象の実行範囲が今回の --start-index/--limit と一致しません。")
    result: dict[int, dict[str, Any]] = {}
    for detail in payload.get("details", []):
        index = int(detail["index"])
        if index in selected:
            result[index] = detail
    return result


def _metrics(details: list[dict[str, Any]], *, selected_total: int) -> dict[str, Any]:
    correct = sum(bool(d.get("correct")) for d in details)
    answered = sum(bool(d.get("answered")) for d in details)
    suspended = len(details) - answered
    wrong = answered - correct
    retrieval_empty = sum(int(d.get("retrieved", 0)) == 0 for d in details)
    documents_retrieved = sum(int(d.get("retrieved", 0)) for d in details)
    data_compiled = sum(int(d.get("data_compiled", 0)) for d in details)
    data_failed = sum(int(d.get("data_compile_failed", 0)) for d in details)
    k_facts_added = sum(int(d.get("k_facts_added", 0)) for d in details)
    evidence_facts = sum(int(d.get("evidence_facts", 0)) for d in details)
    blocked_evidence = sum(int(d.get("blocked_evidence_facts", 0)) for d in details)
    reason_counts: Counter[str] = Counter()
    effort_counts: Counter[str] = Counter()
    source_counts: Counter[str] = Counter()
    for detail in details:
        reason_counts.update(str(x) for x in detail.get("reasons", []))
        effort = detail.get("effort")
        if effort:
            effort_counts[str(effort)] += 1
        source_counts.update(str(x) for x in detail.get("sources", []))

    measured = len(details)
    accuracy = 100.0 * correct / measured if measured else 0.0
    answer_rate = 100.0 * answered / measured if measured else 0.0
    answered_accuracy = 100.0 * correct / answered if answered else 0.0
    retrieval_empty_rate = 100.0 * retrieval_empty / measured if measured else 0.0
    return {
        "completed": measured,
        "selected_total": selected_total,
        "correct": correct,
        "wrong": wrong,
        "accuracy_percent": accuracy,
        "answered": answered,
        "answer_rate_percent": answer_rate,
        "answered_accuracy_percent": answered_accuracy,
        "suspended": suspended,
        "retrieval_empty": retrieval_empty,
        "retrieval_empty_rate_percent": retrieval_empty_rate,
        "documents_retrieved": documents_retrieved,
        "data_compiled": data_compiled,
        "data_compile_failed": data_failed,
        "k_facts_added": k_facts_added,
        "evidence_facts": evidence_facts,
        "blocked_evidence_facts": blocked_evidence,
        "source_counts": dict(sorted(source_counts.items())),
        "reason_counts": dict(sorted(reason_counts.items())),
        "effort_counts": dict(sorted(effort_counts.items())),
    }


def _result_payload(
    *,
    details: list[dict[str, Any]],
    selected: range,
    zip_hash: str,
    csv_hash: str,
    repository_commit: str,
    openalex_enabled: bool,
) -> dict[str, Any]:
    selected_total = len(selected)
    metrics = _metrics(details, selected_total=selected_total)
    full_run = selected.start == 0 and selected.stop == BENCHMARKS["gpqa-diamond"]["full_total"]
    k3_score = float(BENCHMARKS["gpqa-diamond"]["comparison"]["score_percent"])
    comparison = dict(BENCHMARKS["gpqa-diamond"]["comparison"])
    comparison["directly_comparable"] = full_run and metrics["completed"] == selected_total
    comparison["minidora_score_percent"] = metrics["accuracy_percent"] if comparison["directly_comparable"] else None
    comparison["score_gap_points"] = (
        k3_score - metrics["accuracy_percent"] if comparison["directly_comparable"] else None
    )
    comparison["k3_score_ratio_percent"] = (
        100.0 * metrics["accuracy_percent"] / k3_score
        if comparison["directly_comparable"] and k3_score
        else None
    )
    return {
        "schema": "minidora.benchmark.repository-runner.v1",
        "protocol": {
            "benchmark": "GPQA Diamond",
            "dataset": "official idavidrein/gpqa dataset.zip / gpqa_diamond.csv",
            "dataset_url": gpqa.DATASET_URL,
            "dataset_zip_sha256": zip_hash,
            "dataset_csv_sha256": csv_hash,
            "full_benchmark_total": BENCHMARKS["gpqa-diamond"]["full_total"],
            "selected_indices": list(selected),
            "choice_shuffle_seed": gpqa.SEED,
            "compiler": "MINIDORA public standard HDS Compiler; Japanese-base role projection; benchmark-agnostic",
            "gold_boundary": "gold used only after inference for scoring",
            "repository_commit": repository_commit,
            "openalex_enabled": openalex_enabled,
            "wikipedia_languages": ["en"],
            "runtime": "current repository checkout; HDS choice native R->HDS->K->J",
            "checkpoint_resume": "same dataset + selected range + repository commit + OpenAlex condition only",
        },
        "metrics": metrics,
        "comparison_reference": comparison,
        "baseline_reference_only_not_directly_comparable": {
            "correct": 8,
            "total": 198,
            "accuracy_percent": 4.040404040404041,
            "reason": "prototype baseline used a different private HDS Compiler whose exact executable implementation is unavailable",
        },
        "details": details,
    }


def _run_gpqa(args: argparse.Namespace) -> int:
    csv_path, zip_hash, csv_hash = _prepare_gpqa_dataset(args.cache_dir, refresh=args.refresh_dataset)
    cases = gpqa._load_cases(csv_path)
    if len(cases) != 198:
        raise RuntimeError(f"GPQA Diamond expected 198 rows, got {len(cases)}")
    selected = _selected_range(len(cases), args.start_index, args.limit)
    if args.checkpoint_every <= 0:
        raise SystemExit("--checkpoint-every は1以上で指定してください。")

    repository_commit = _git_head()
    api_key = None if args.no_openalex else (os.getenv("OPENALEX_API_KEY", "").strip() or None)
    completed = (
        _load_resume(
            args.out,
            selected=selected,
            csv_hash=csv_hash,
            repository_commit=repository_commit,
            openalex_enabled=api_key is not None,
        )
        if args.resume
        else {}
    )
    provider = gpqa.一般知識参照供給器(
        OpenAlex_API_key=api_key,
        Wikipedia言語=("en",),
        timeout=8.0,
        最大本文文字数=6000,
        並列=True,
        最大並列=4,
    )
    compiler = gpqa.汎用意味射影Compiler()
    base_core = gpqa.K3相当能力核()

    processed_since_checkpoint = 0
    for index in selected:
        if index in completed:
            print(f"CASE {index + 1:03d}/198 resume=skip", flush=True)
            continue
        question, choices, gold = cases[index]
        question_ir = compiler.問題IR(question, choices)
        references = gpqa.HDS参照検索(provider, question_ir)
        inference = gpqa.HDS選択推論実行(
            question_ir,
            tuple(references),
            コンパイル=compiler.コンパイル,
            基礎能力核=base_core,
        )
        predicted = inference.回答ラベル
        answered = inference.状態 == "APPROVE" and predicted is not None
        correct = bool(answered and predicted == gold)
        completed[index] = {
            "index": index,
            "predicted": predicted,
            "gold": gold,
            "correct": correct,
            "answered": answered,
            "status": inference.状態,
            "reasons": list(inference.理由),
            "retrieved": len(references),
            "sources": [r.供給器 for r in references],
            "data_compiled": inference.Dataコンパイル数,
            "data_compile_failed": inference.Dataコンパイル失敗数,
            "k_facts_added": inference.K追加事実数,
            "evidence_facts": inference.K証拠事実数,
            "blocked_evidence_facts": inference.K証拠阻害事実数,
            "effort": inference.K3結果.努力水準 if inference.K3結果 else None,
            "candidate_diagnostics": [
                {
                    "label": d.候補,
                    "score": d.合計得点,
                    "evidence_score": d.証拠得点,
                    "graph_score": d.graph得点,
                    "independent_sources": d.独立出典数,
                }
                for d in (inference.K3結果.候補診断 if inference.K3結果 else ())
            ],
        }
        processed_since_checkpoint += 1
        print(
            f"CASE {index + 1:03d}/198 status={inference.状態} pred={predicted} "
            f"correct={correct} retrieved={len(references)}",
            flush=True,
        )
        if processed_since_checkpoint >= args.checkpoint_every:
            details = [completed[i] for i in sorted(completed) if i in selected]
            _atomic_write(
                args.out,
                _result_payload(
                    details=details,
                    selected=selected,
                    zip_hash=zip_hash,
                    csv_hash=csv_hash,
                    repository_commit=repository_commit,
                    openalex_enabled=api_key is not None,
                ),
            )
            processed_since_checkpoint = 0

    details = [completed[i] for i in sorted(completed) if i in selected]
    result = _result_payload(
        details=details,
        selected=selected,
        zip_hash=zip_hash,
        csv_hash=csv_hash,
        repository_commit=repository_commit,
        openalex_enabled=api_key is not None,
    )
    _atomic_write(args.out, result)
    print("MINIDORA_BENCHMARK_RESULT=" + json.dumps(result["metrics"], ensure_ascii=False), flush=True)
    print("K3_COMPARISON=" + json.dumps(result["comparison_reference"], ensure_ascii=False), flush=True)
    print(f"RESULT_FILE={args.out}", flush=True)
    return 0


def main() -> int:
    _標準入出力をUTF8化()
    parser = _parser()
    args = parser.parse_args()
    if args.list_mode:
        for name, meta in BENCHMARKS.items():
            print(f"{name}\t{meta['description']}")
        return 0
    if args.benchmark == "gpqa-diamond":
        return _run_gpqa(args)
    parser.print_help()
    return 2


if __name__ == "__main__":
    raise SystemExit(main())

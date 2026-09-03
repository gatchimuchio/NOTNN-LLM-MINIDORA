from __future__ import annotations

"""保存済み正式GPQA個票へ既存科学専門能力を重ねる高速replay監査。

外部参照の再取得・Formal coreの再実行は行わない。保存済み個票をbaselineとして固定し、
同じGPQA問題/選択肢へ現行 ``科学専門能力を通常MINIDORAへ接続`` を適用する。

baseline取得commitから現在HEADまでFormal core責任範囲に変更がある場合は実行を拒否する。
これによりlive A/B完走前でも、既存科学専門能力の純粋な上書き寄与を再現可能に測る。
"""

import argparse
import json
import subprocess
import sys
from collections import Counter
from pathlib import Path
from types import ModuleType, SimpleNamespace

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
sys.path.insert(0, str(SRC))

import benchmark as _benchmark
import gpqa_measure_current as _gpqa
import minidora.hds_choice_runtime as _choice_runtime
from minidora.hds_compiler_v1 import 公開HDSコンパイラ
from minidora.科学専門能力統合 import 科学専門能力を通常MINIDORAへ接続


DEFAULT_BASELINE = ROOT / "gpqa_precision_gate_v1_measurement.json"
DEFAULT_OUT = ROOT / "gpqa_scientific_specialist_replay.json"
FORMAL_CORE_PATHS = {
    "tools/benchmark.py",
    "tools/benchmark_formal.py",
    "tools/gpqa_measure_current.py",
}
FORMAL_CORE_PREFIXES = ("src/minidora/",)


def _git_changed_paths(base: str) -> tuple[str, ...]:
    completed = subprocess.run(
        ["git", "diff", "--name-only", f"{base}..HEAD"],
        cwd=ROOT,
        text=True,
        encoding="utf-8",
        capture_output=True,
        check=False,
    )
    if completed.returncode != 0:
        raise RuntimeError(completed.stderr.strip() or "git diff failed")
    return tuple(line.strip() for line in completed.stdout.splitlines() if line.strip())


def _assert_formal_core_unchanged(base: str) -> tuple[str, ...]:
    changed = _git_changed_paths(base)
    forbidden = [
        path
        for path in changed
        if path in FORMAL_CORE_PATHS or any(path.startswith(prefix) for prefix in FORMAL_CORE_PREFIXES)
    ]
    if forbidden:
        raise RuntimeError(
            "保存baseline以後にFormal core責任範囲が変更されているためreplayを拒否: "
            + ", ".join(forbidden)
        )
    return changed


def _metric(correct: int, answered: int, total: int) -> dict[str, float | int]:
    return {
        "correct": correct,
        "total": total,
        "accuracy_percent": 100.0 * correct / total if total else 0.0,
        "answered": answered,
        "answer_rate_percent": 100.0 * answered / total if total else 0.0,
        "answered_accuracy_percent": 100.0 * correct / answered if answered else 0.0,
        "suspended": total - answered,
    }


def _solver(reasons) -> str | None:
    prefix = "SCIENTIFIC_CAPABILITY_SOLVER:"
    for reason in reasons:
        text = str(reason)
        if text.startswith(prefix):
            return text[len(prefix):]
    return None


def run(*, baseline_path: Path, out: Path, cache_dir: Path) -> dict:
    baseline_payload = json.loads(baseline_path.read_text(encoding="utf-8"))
    protocol = baseline_payload.get("protocol", {})
    baseline_commit = str(protocol.get("repository_commit", ""))
    if not baseline_commit:
        raise RuntimeError("baseline protocolにrepository_commitがない")
    changed_paths = _assert_formal_core_unchanged(baseline_commit)

    csv_path, zip_hash, csv_hash = _benchmark._prepare_gpqa_dataset(cache_dir, refresh=False)
    if csv_hash != protocol.get("dataset_csv_sha256"):
        raise RuntimeError("baselineとreplayのGPQA CSV hashが一致しない")
    if int(protocol.get("choice_shuffle_seed", -1)) != int(_gpqa.SEED):
        raise RuntimeError("baselineとreplayのchoice shuffle seedが一致しない")

    cases = _gpqa._load_cases(csv_path)
    if len(cases) != 198:
        raise RuntimeError(f"GPQA Diamond expected 198 rows, got {len(cases)}")
    baseline_rows = {int(row["index"]): row for row in baseline_payload.get("details", [])}
    if sorted(baseline_rows) != list(range(198)):
        raise RuntimeError("baseline個票が198問全件揃っていない")

    compiler = 公開HDSコンパイラ()
    current_baseline = None

    def baseline_fallback(question_ir, references, *args, **kwargs):
        if current_baseline is None:
            raise RuntimeError("baseline replay state is not set")
        return current_baseline

    specialist_module = ModuleType("minidora_scientific_specialist_replay_runtime")
    specialist_module.HDS選択推論実行 = baseline_fallback
    specialist_module.HDS選択問題 = _choice_runtime.HDS選択問題
    specialist_module.HDS選択実行結果 = _choice_runtime.HDS選択実行結果
    科学専門能力を通常MINIDORAへ接続(specialist_module)
    specialist_runtime = specialist_module.HDS選択推論実行

    b_correct = b_answered = 0
    s_correct = s_answered = 0
    improved = regressed = changed = fired = 0
    solver_counts: Counter[str] = Counter()
    details = []

    for index, (question, choices, gold) in enumerate(cases):
        row = baseline_rows[index]
        if str(row.get("gold")) != gold:
            raise RuntimeError(f"case {index}: baseline goldとreplay goldが一致しない")

        b_status = str(row.get("status", ""))
        b_pred = row.get("predicted")
        b_answered_case = b_status == "APPROVE" and b_pred is not None
        b_correct_case = bool(b_answered_case and b_pred == gold)
        b_correct += int(b_correct_case)
        b_answered += int(b_answered_case)

        current_baseline = SimpleNamespace(
            状態=b_status,
            回答ラベル=b_pred,
            理由=tuple(row.get("reasons", [])),
            専門作用起動数=int(row.get("specialist_actions_invoked", 0) or 0),
        )
        question_ir = compiler.問題IR(question, choices)
        result = specialist_runtime(question_ir, ())
        s_status = str(getattr(result, "状態", ""))
        s_pred = getattr(result, "回答ラベル", None)
        reasons = tuple(str(x) for x in getattr(result, "理由", ()) or ())
        specialist_actions = int(getattr(result, "専門作用起動数", 0) or 0)
        solver = _solver(reasons)

        s_answered_case = s_status == "APPROVE" and s_pred is not None
        s_correct_case = bool(s_answered_case and s_pred == gold)
        s_correct += int(s_correct_case)
        s_answered += int(s_answered_case)
        improved_case = not b_correct_case and s_correct_case
        regressed_case = b_correct_case and not s_correct_case
        changed_case = b_status != s_status or b_pred != s_pred
        improved += int(improved_case)
        regressed += int(regressed_case)
        changed += int(changed_case)
        fired += int(specialist_actions > 0)
        if solver:
            solver_counts[solver] += 1

        details.append(
            {
                "index": index,
                "gold": gold,
                "baseline_status": b_status,
                "baseline_predicted": b_pred,
                "baseline_correct": b_correct_case,
                "specialist_status": s_status,
                "specialist_predicted": s_pred,
                "specialist_correct": s_correct_case,
                "specialist_actions_invoked": specialist_actions,
                "specialist_solver": solver,
                "improved": improved_case,
                "regressed": regressed_case,
                "changed": changed_case,
            }
        )

    total = len(cases)
    baseline_metrics = _metric(b_correct, b_answered, total)
    specialist_metrics = _metric(s_correct, s_answered, total)
    result = {
        "schema": "minidora.gpqa.scientific-specialist-replay.v1",
        "protocol": {
            "benchmark": "GPQA Diamond",
            "baseline_file": str(baseline_path.relative_to(ROOT)),
            "baseline_repository_commit": baseline_commit,
            "current_head": subprocess.run(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True, encoding="utf-8", capture_output=True, check=True).stdout.strip(),
            "formal_core_unchanged_since_baseline": True,
            "changed_paths_since_baseline": list(changed_paths),
            "dataset_zip_sha256": zip_hash,
            "dataset_csv_sha256": csv_hash,
            "choice_shuffle_seed": _gpqa.SEED,
            "gold_boundary": "gold used only after repo-native scientific specialist inference",
            "specialist_source": "existing src/minidora/科学専門能力*.py via 科学専門能力を通常MINIDORAへ接続",
            "replay_boundary": "no retrieval replay and no Formal core rerun; unfired cases inherit saved baseline exactly",
        },
        "baseline": baseline_metrics,
        "specialist_on": specialist_metrics,
        "delta": {
            "correct_delta": s_correct - b_correct,
            "accuracy_points": specialist_metrics["accuracy_percent"] - baseline_metrics["accuracy_percent"],
            "answered_delta": s_answered - b_answered,
            "answer_rate_points": specialist_metrics["answer_rate_percent"] - baseline_metrics["answer_rate_percent"],
            "answered_accuracy_points": specialist_metrics["answered_accuracy_percent"] - baseline_metrics["answered_accuracy_percent"],
            "changed_answers": changed,
            "improved_cases": improved,
            "regressed_cases": regressed,
            "net_improved_cases": improved - regressed,
            "specialist_fired_cases": fired,
        },
        "solver_counts": dict(sorted(solver_counts.items())),
        "details": details,
    }
    out.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return result


def main() -> int:
    parser = argparse.ArgumentParser(description="GPQA scientific specialist fast replay")
    parser.add_argument("--baseline", type=Path, default=DEFAULT_BASELINE)
    parser.add_argument("--out", type=Path, default=DEFAULT_OUT)
    parser.add_argument("--cache-dir", type=Path, default=ROOT / ".cache/minidora-bench")
    args = parser.parse_args()
    result = run(baseline_path=args.baseline.resolve(), out=args.out.resolve(), cache_dir=args.cache_dir.resolve())
    print("MINIDORA_GPQA_SCIENTIFIC_REPLAY=" + json.dumps({
        "baseline": result["baseline"],
        "specialist_on": result["specialist_on"],
        "delta": result["delta"],
        "solver_counts": result["solver_counts"],
    }, ensure_ascii=False), flush=True)
    print(f"RESULT_FILE={args.out}", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

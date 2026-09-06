from __future__ import annotations

"""Frozen-Reference GPQA A/B for sandbox v0.6.

Each case retrieves R exactly once.  The control arm is the current formal
selection core with no supervisory actions; the v0.6 arm is the unified state
session/evaluator.  Thus both arms consume exactly the same immutable R tuple.
Gold is used only after both outputs.  Sandbox branch only.
"""

import json
import os
from pathlib import Path
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
sys.path.insert(0, str(SRC))

import gpqa_measure_current as gpqa  # noqa: E402
from minidora.hds_choice_runtime import HDS選択推論実行  # noqa: E402
from minidora.hds_compiler_v1 import 公開HDSコンパイラ  # noqa: E402
from minidora.hds_reference import HDS参照検索  # noqa: E402
from minidora.hds統一実行 import HDS統一選択評価  # noqa: E402
from minidora.hds統一状態循環 import HDS統一状態Session  # noqa: E402
from minidora.standard_reference import 一般知識参照供給器  # noqa: E402
from minidora.能力状態差循環 import 標準能力模型核  # noqa: E402


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


def _control(question_ir, references, *, compiler):
    return HDS選択推論実行(
        question_ir,
        tuple(references),
        コンパイル=compiler.コンパイル,
        基礎能力核=None,
        模型核=標準能力模型核(),
        正式模型評価=True,
    )


def _v06(question_ir, references, *, compiler):
    query = str(getattr(question_ir, "正規化文", "") or getattr(question_ir, "原文", ""))
    session = HDS統一状態Session(
        query,
        tuple(references),
        主体状態=None,
        認知世界ID=str(getattr(question_ir, "認知世界ID", "") or ""),
    )
    result = HDS統一選択評価(
        question_ir,
        tuple(references),
        コンパイル=compiler.コンパイル,
        模型核=標準能力模型核(),
        統一session=session,
        主体状態=None,
    )
    if tuple(session.参照正本) != tuple(references):
        raise RuntimeError("v0.6 mutated frozen Reference archive")
    return result, session.snapshot()


def main() -> int:
    start = int(os.environ["MINIDORA_V06_AB_START"])
    end = int(os.environ["MINIDORA_V06_AB_END"])
    out = Path(os.environ.get("MINIDORA_V06_AB_OUT", f"v06_frozen_ab_{start:03d}-{end-1:03d}.json"))
    if not (0 <= start < end <= 198):
        raise ValueError(f"invalid range {start}:{end}")

    with tempfile.TemporaryDirectory(prefix="minidora-v06-frozen-") as td:
        csv_path, zip_hash, csv_hash = gpqa._download_dataset(Path(td))
        all_cases = gpqa._load_cases(csv_path)
        if len(all_cases) != 198:
            raise RuntimeError(f"GPQA Diamond expected 198 rows, got {len(all_cases)}")
        cases = all_cases[start:end]

        api_key = os.getenv("OPENALEX_API_KEY", "").strip() or None
        provider = 一般知識参照供給器(
            OpenAlex_API_key=api_key,
            Wikipedia言語=("en",),
            timeout=8.0,
            最大本文文字数=6000,
            並列=True,
            最大並列=4,
        )
        compiler = 公開HDSコンパイラ()

        c_correct = c_answered = v_correct = v_answered = 0
        improved = regressed = changed = 0
        docs = empty = 0
        details: list[dict[str, object]] = []

        for index, (question, choices, gold) in enumerate(cases, start=start):
            ir = compiler.問題IR(question, choices)
            refs = tuple(HDS参照検索(provider, ir))
            docs += len(refs)
            empty += int(not refs)

            control = _control(ir, refs, compiler=compiler)
            v06, snapshot = _v06(ir, refs, compiler=compiler)

            cp = control.回答ラベル
            ca = control.状態 == "APPROVE" and cp is not None
            cc = bool(ca and cp == gold)
            vp = v06.回答ラベル
            va = v06.状態 == "APPROVE" and vp is not None
            vc = bool(va and vp == gold)

            c_correct += int(cc)
            c_answered += int(ca)
            v_correct += int(vc)
            v_answered += int(va)
            imp = (not cc) and vc
            reg = cc and (not vc)
            chg = control.状態 != v06.状態 or cp != vp
            improved += int(imp)
            regressed += int(reg)
            changed += int(chg)

            details.append({
                "index": index,
                "gold": gold,
                "reference_count": len(refs),
                "control_status": control.状態,
                "control_predicted": cp,
                "control_correct": cc,
                "v06_status": v06.状態,
                "v06_predicted": vp,
                "v06_correct": vc,
                "v06_cycle": snapshot.cycle,
                "v06_action_history": list(snapshot.作用履歴),
                "improved": imp,
                "regressed": reg,
                "changed": chg,
            })
            print(f"CASE {index+1:03d}/198 R={len(refs)} control={control.状態}:{cp} v06={v06.状態}:{vp} gold={gold}", flush=True)

        total = end - start
        cm = _metric(c_correct, c_answered, total)
        vm = _metric(v_correct, v_answered, total)
        payload = {
            "schema": "minidora.gpqa.v06-frozen-reference-ab.segment.v1",
            "protocol": {
                "benchmark": "GPQA Diamond",
                "dataset_zip_sha256": zip_hash,
                "dataset_csv_sha256": csv_hash,
                "choice_shuffle_seed": gpqa.SEED,
                "selected_start": start,
                "selected_end_exclusive": end,
                "reference_rule": "one immutable Reference tuple per case shared by both arms",
                "control_arm": "current HDS formal selection core; no HDS supervisory action",
                "v06_arm": "unified state session -> unified selection evaluation -> HDS/J",
                "gold_boundary": "gold used only after both outputs for scoring",
                "openalex_enabled": api_key is not None,
                "main_modified": False,
                "sandbox_branch_only": True,
            },
            "control": cm,
            "v06_unified": vm,
            "delta": {
                "correct_delta": v_correct - c_correct,
                "answered_delta": v_answered - c_answered,
                "changed_cases": changed,
                "improved_cases": improved,
                "regressed_cases": regressed,
                "net_improved_cases": improved - regressed,
            },
            "retrieval": {"reference_documents": docs, "retrieval_empty_cases": empty},
            "details": details,
        }
        out.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        print("FROZEN_SEGMENT_RESULT=" + json.dumps({"range": [start, end], "control": cm, "v06": vm, "delta": payload["delta"]}, ensure_ascii=False), flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

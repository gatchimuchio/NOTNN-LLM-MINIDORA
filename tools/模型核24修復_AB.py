from __future__ import annotations

'24点系模型核と現行模型核を同一Question/参照で比較する因果A/B。\n\n外部参照は各問題につき一度だけ取得し、その同一参照recordを両模型核へ渡す。\nGoldは両推論完了後の採点にのみ使用する。\n'

import argparse
import json
import os
from pathlib import Path
from typing import Any

import benchmark as bench
import gpqa_measure_current as gpqa

from minidora.HDS選択実行系 import HDS選択推論実行 as 現行模型核選択
from minidora.HDS選択実行系_v24 import HDS選択推論実行 as 模型核24選択
from minidora.HDS構文化器_v1 import 公開HDSコンパイラ
from minidora.HDS参照 import HDS参照検索
from minidora.標準参照 import 一般知識参照供給器
from minidora.能力状態差循環 import 標準能力模型核


def _parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser()
    p.add_argument("--out", type=Path, required=True)
    p.add_argument("--snapshot-out", type=Path, required=True)
    p.add_argument("--cache-dir", type=Path, default=Path(".cache/minidora-core-ab"))
    p.add_argument("--start-index", type=int, default=0)
    p.add_argument("--limit", type=int, default=None)
    p.add_argument("--no-openalex", action="store_true")
    return p


def _参照辞書(r) -> dict[str, Any]:
    return {
        "識別子": str(r.識別子),
        "対象": str(r.対象),
        "内容": str(r.内容),
        "由来": str(r.由来),
        "供給器": str(r.供給器),
        "信頼": float(r.信頼),
        "意味キー": r.意味キー,
        "値": r.値,
        "時点": r.時点,
        "範囲": r.範囲,
        "条件": [[str(k), str(v)] for k, v in r.条件],
        "意味確定": bool(r.意味確定),
    }


def _結果辞書(結果, gold: str) -> dict[str, Any]:
    pred = 結果.回答ラベル
    answered = 結果.状態 == "APPROVE" and pred is not None
    return {
        "predicted": pred,
        "status": 結果.状態,
        "answered": answered,
        "correct": bool(answered and pred == gold),
        "reasons": list(結果.理由),
        '検査点_reactivations': int(結果.検査点再活性数),
        "global_reconciliations": int(結果.大域再照合数),
        '候補_cross_updates': int(結果.候補横断更新数),
        "specialist_actions": int(結果.専門作用起動数),
        "local_windows": int(結果.局所Window数),
        "local_reconciliations": int(結果.局所再照合数),
    }


def main() -> int:
    args = _parser().parse_args()
    csv_path, zip_hash, csv_hash = bench._prepare_gpqa_dataset(args.cache_dir, refresh=False)
    cases = gpqa._load_cases(csv_path)
    selected = bench._selected_range(len(cases), args.start_index, args.limit)

    api_key = None if args.no_openalex else (os.getenv("OPENALEX_API_KEY", "").strip() or None)
    provider = 一般知識参照供給器(
        OpenAlex_API_key=api_key,
        Wikipedia言語=("en",),
        timeout=8.0,
        最大本文文字数=6000,
        並列=True,
        最大並列=4,
    )
    構文化器 = 公開HDSコンパイラ()
    details: list[dict[str, Any]] = []
    snapshots: list[dict[str, Any]] = []

    for index in selected:
        question, choices, gold = cases[index]
        question_ir = 構文化器.問題IR(question, choices)
        references = tuple(HDS参照検索(provider, question_ir))

        baseline = 模型核24選択(
            question_ir,
            references,
            コンパイル=構文化器.コンパイル,
            基礎能力核=None,
            模型核=標準能力模型核(),
            正式模型評価=True,
        )
        current = 現行模型核選択(
            question_ir,
            references,
            コンパイル=構文化器.コンパイル,
            基礎能力核=None,
            模型核=標準能力模型核(),
            正式模型評価=True,
        )

        b = _結果辞書(baseline, gold)
        c = _結果辞書(current, gold)
        details.append({
            "index": index,
            "gold": gold,
            "retrieved": len(references),
            '模型核24': b,
            "current": c,
            "improved": bool(c["correct"] and not b["correct"]),
            "regressed": bool(b["correct"] and not c["correct"]),
            "answer_changed": b["predicted"] != c["predicted"],
        })
        snapshots.append({
            "index": index,
            "question": question,
            "choices": list(choices),
            "gold": gold,
            "references": [_参照辞書(r) for r in references],
        })
        print(
            f"CASE {index + 1:03d}/198 core24={b['predicted']} current={c['predicted']} "
            f"improved={details[-1]['improved']} regressed={details[-1]['regressed']} refs={len(references)}",
            flush=True,
        )

    baseline_correct = sum(int(x['模型核24']["correct"]) for x in details)
    current_correct = sum(int(x["current"]["correct"]) for x in details)
    improved = sum(int(x["improved"]) for x in details)
    regressed = sum(int(x["regressed"]) for x in details)
    current_specialist = sum(int(x["current"]["specialist_actions"]) for x in details)
    local_selected = sum("FORMAL_LOCAL_VIEW_RECHECK_SELECTED" in x["current"]["reasons"] for x in details)

    payload = {
        "契約形式": 'minidora.模型核24-current.same-参照-ab.v1',
        "protocol": {
            "dataset_zip_sha256": zip_hash,
            "資料集合CSV_SHA256": csv_hash,
            "選択肢シャッフル種": gpqa.SEED,
            "選択番号群": list(selected),
            'same_参照_records': True,
            'gold_境界': "gold used only after Core24 and current inference",
            "baseline": "HDS選択実行系_v24.HDS選択推論実行",
            "current": "HDS選択実行系.HDS選択推論実行",
            'specialist_モジュール': False,
            "OpenAlex有効": api_key is not None,
        },
        "metrics": {
            "completed": len(details),
            '模型核24_correct': baseline_correct,
            "current_correct": current_correct,
            "correct_delta": current_correct - baseline_correct,
            "improved_cases": improved,
            "regressed_cases": regressed,
            "net_improved_cases": improved - regressed,
            "answer_changed_cases": sum(int(x["answer_changed"]) for x in details),
            "current_specialist_actions": current_specialist,
            "current_local_view_selected_cases": local_selected,
        },
        "details": details,
    }
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.snapshot_out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    args.snapshot_out.write_text(json.dumps({
        "契約形式": 'minidora.gpqa.参照-snapshot.v1',
        "資料集合CSV_SHA256": csv_hash,
        "選択肢シャッフル種": gpqa.SEED,
        "cases": snapshots,
    }, ensure_ascii=False, indent=2, default=str) + "\n", encoding="utf-8")
    print("CORE_AB=" + json.dumps(payload["metrics"], ensure_ascii=False), flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

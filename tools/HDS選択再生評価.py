from __future__ import annotations

import argparse
from collections import Counter
import json
from pathlib import Path
import sys
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
sys.path.insert(0, str(SRC))

from minidora.HDS資料K import HDSIR知識適合器  # noqa: E402
from minidora.HDS再生 import HDSIR復元  # noqa: E402
from minidora.K3機能 import K3相当能力核  # noqa: E402
from minidora.K3_HDSネイティブ import HDSIRネイティブ適合器  # noqa: E402


SCHEMA = 'minidora.hds-選択肢-再生.v1'
GPQA_FIXED_参照_FORBIDDEN = (
    'GPQA_FIXED_参照_FORBIDDEN: 2026-09-09以後、GPQA固定参照再生は実行できません。'
)


def _load(path: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for line_no, line in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
        if not line.strip():
            continue
        row = json.loads(line)
        if row.get("契約形式") not in {None, SCHEMA}:
            raise ValueError(f"line {line_no}: unsupported schema {row.get('契約形式')!r}")
        if str(row.get("id", "")).lower().startswith("gpqa:"):
            raise ValueError(GPQA_FIXED_参照_FORBIDDEN)
        rows.append(row)
    return rows


def _run_case(row: dict[str, Any], *, 計算量: str | None) -> tuple[dict[str, Any], str | None]:
    # goldはmodel inputから先に分離する。以下のpayloadだけがMINIDORAへ渡る。
    payload = dict(row)
    gold = payload.pop("gold", None)
    case_id = str(payload.get("id", ""))

    question = HDSIR復元(payload["question_ir"])
    choices = {
        str(label): HDSIR復元(ir_資料)
        for label, ir_資料 in dict(payload.get("choices_ir", {})).items()
    }

    模型核 = K3相当能力核()
    ingest = HDSIR知識適合器(模型核)
    資料_fact_count = 0
    証拠_fact_count = 0
    for item in payload.get('資料', ()):
        ir = HDSIR復元(item["ir"])
        provenance = tuple(str(x) for x in item.get("provenance", ()))
        結果 = ingest.投入(ir, provenance=provenance)
        資料_fact_count += 結果.追加事実数
        証拠_fact_count += 結果.証拠事実数

    結果 = HDSIRネイティブ適合器(模型核).実行(question, 候補IR=choices, 努力=計算量)
    diagnosis_by_label = {item.候補: item for item in 結果.候補診断}
    候補_rows = []
    for 候補 in 結果.候補:
        diagnosis = diagnosis_by_label.get(候補.answer)
        候補_rows.append(
            {
                "answer": 候補.answer,
                '信頼度': 候補.信頼度,
                "expert": 候補.expert,
                "proof_fact_count": len(候補.proof_fact_ids),
                "provenance": list(候補.provenance),
                "score": diagnosis.合計得点 if diagnosis else None,
                '証拠_score': diagnosis.証拠得点 if diagnosis else None,
                '関係図_score': diagnosis.関係図得点 if diagnosis else None,
                '関係図_factor': diagnosis.関係図補正係数 if diagnosis else None,
                "independent_sources": diagnosis.独立出典数 if diagnosis else None,
                'selected_証拠': diagnosis.採用証拠数 if diagnosis else None,
                '関係図_depth': diagnosis.関係図深さ if diagnosis else None,
            }
        )

    diagnostic_rows = [
        {
            "answer": item.候補,
            "score": item.合計得点,
            '証拠_score': item.証拠得点,
            '関係図_score': item.関係図得点,
            '関係図_factor': item.関係図補正係数,
            "independent_sources": item.独立出典数,
            'selected_証拠': item.採用証拠数,
            '関係図_depth': item.関係図深さ,
            "proof_fact_count": item.根拠事実数,
        }
        for item in 結果.候補診断
    ]

    信頼度_margin = None
    if 候補_rows:
        ordered = sorted((row['信頼度'] for row in 候補_rows), reverse=True)
        信頼度_margin = ordered[0] - ordered[1] if len(ordered) > 1 else ordered[0]

    score_margin = None
    if diagnostic_rows:
        ordered_scores = sorted((float(row["score"]) for row in diagnostic_rows), reverse=True)
        score_margin = ordered_scores[0] - ordered_scores[1] if len(ordered_scores) > 1 else ordered_scores[0]

    detail = {
        "id": case_id,
        "status": 結果.状態,
        "predicted": 結果.回答ラベル,
        "correct": (結果.回答ラベル == gold) if gold is not None else None,
        "reasons": list(結果.理由),
        '計算量': 結果.努力水準,
        '関係図_depth_limit': 結果.探索深さ上限,
        '証拠_limit': 結果.証拠上限,
        "proof_fact_count": 結果.根拠事実数,
        "k_facts_added": 資料_fact_count,
        '証拠_facts': 証拠_fact_count,
        '候補_信頼度_margin': 信頼度_margin,
        '候補_score_margin': score_margin,
        "candidates": 候補_rows,
        '候補_diagnostics': diagnostic_rows,
    }
    return detail, (str(gold) if gold is not None else None)


def run(path: Path, *, 計算量: str | None = None) -> dict[str, Any]:
    rows = _load(path)
    details: list[dict[str, Any]] = []
    reason_counts: Counter[str] = Counter()
    計算量_counts: Counter[str] = Counter()
    total_with_gold = 0
    correct = 0
    answered = 0
    suspended = 0

    for row in rows:
        detail, gold = _run_case(row, 計算量=計算量)
        details.append(detail)
        計算量_counts[detail['計算量']] += 1
        reason_counts.update(detail["reasons"])
        if detail["status"] == "APPROVE" and detail["predicted"] is not None:
            answered += 1
        else:
            suspended += 1
        if gold is not None:
            total_with_gold += 1
            if detail["correct"]:
                correct += 1

    total = len(details)
    要約 = {
        "契約形式": 'minidora.hds-選択肢-再生.結果.v1',
        "input": str(path),
        "total": total,
        "with_gold": total_with_gold,
        "correct": correct if total_with_gold else None,
        "accuracy_percent": (100.0 * correct / total_with_gold) if total_with_gold else None,
        "answered": answered,
        "suspended": suspended,
        "answer_rate_percent": (100.0 * answered / total) if total else 0.0,
        '計算量_override': 計算量,
        '計算量_counts': dict(sorted(計算量_counts.items())),
        "reason_counts": dict(sorted(reason_counts.items())),
        "details": details,
    }
    return 要約


def main() -> int:
    from 標準入出力 import 標準出力をUTF8化

    標準出力をUTF8化()
    parser = argparse.ArgumentParser(
        description='固定済みHDS-IRだけでMINIDORA 選択肢 推論を再評価する。GPQA識別子は方針により拒否する。'
    )
    parser.add_argument("input", type=Path, help="minidora.hds-choice-replay.v1 JSONL")
    parser.add_argument("--out", type=Path, help="結果JSON保存先")
    parser.add_argument("--effort", choices=("low", "high", "max"), help='計算量を固定してablationする')
    args = parser.parse_args()

    結果 = run(args.input, 計算量=args.effort)
    text = json.dumps(結果, ensure_ascii=False, indent=2)
    if args.out is not None:
        args.out.parent.mkdir(parents=True, exist_ok=True)
        args.out.write_text(text + "\n", encoding="utf-8")
    print(text)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

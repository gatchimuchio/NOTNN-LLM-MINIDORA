from __future__ import annotations

import csv
import hashlib
import json
import os
import random
import sys
import tempfile
import urllib.request
import zipfile
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
sys.path.insert(0, str(SRC))

from minidora.hds_choice_runtime import HDS選択推論実行
from minidora.hds_compiler_v1 import 公開HDSコンパイラ
from minidora.hds_reference import HDS参照検索
from minidora.k3_functional import K3相当能力核
from minidora.standard_reference import 一般知識参照供給器


DATASET_URL = "https://raw.githubusercontent.com/idavidrein/gpqa/main/dataset.zip"
DATASET_PASSWORD = b"deserted-untie-orchid"
SEED = 0
LABELS = ("A", "B", "C", "D")

# 旧ベンチ入口との互換名。実体は公開標準HDS Compiler。
汎用意味射影Compiler = 公開HDSコンパイラ


def _sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        while True:
            chunk = f.read(1024 * 1024)
            if not chunk:
                break
            h.update(chunk)
    return h.hexdigest()


def _download_dataset(work: Path) -> tuple[Path, str, str]:
    archive = work / "dataset.zip"
    request = urllib.request.Request(DATASET_URL, headers={"User-Agent": "MINIDORA-GPQA-Measurement/1.0"})
    with urllib.request.urlopen(request, timeout=60) as response, archive.open("wb") as out:
        out.write(response.read())
    zip_hash = _sha256(archive)
    with zipfile.ZipFile(archive) as zf:
        names = zf.namelist()
        matches = [name for name in names if name.endswith("gpqa_diamond.csv")]
        if len(matches) != 1:
            raise RuntimeError(f"gpqa_diamond.csv not uniquely found: {matches}")
        zf.extract(matches[0], path=work, pwd=DATASET_PASSWORD)
        csv_path = work / matches[0]
    return csv_path, zip_hash, _sha256(csv_path)


def _load_cases(csv_path: Path) -> list[tuple[str, tuple[str, str, str, str], str]]:
    rng = random.Random(SEED)
    cases: list[tuple[str, tuple[str, str, str, str], str]] = []
    with csv_path.open("r", encoding="utf-8-sig", newline="") as f:
        for row in csv.DictReader(f):
            question = str(row["Question"])
            correct = str(row["Correct Answer"])
            choices = [
                str(row["Incorrect Answer 1"]),
                str(row["Incorrect Answer 2"]),
                str(row["Incorrect Answer 3"]),
                correct,
            ]
            rng.shuffle(choices)
            gold = LABELS[choices.index(correct)]
            cases.append((question, tuple(choices), gold))
    return cases


def main() -> int:
    with tempfile.TemporaryDirectory(prefix="minidora-gpqa-") as td:
        work = Path(td)
        csv_path, zip_hash, csv_hash = _download_dataset(work)
        cases = _load_cases(csv_path)
        if len(cases) != 198:
            raise RuntimeError(f"GPQA Diamond expected 198 rows, got {len(cases)}")

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
        base_core = K3相当能力核()

        correct_count = 0
        answered = 0
        suspended = 0
        retrieval_empty = 0
        docs_total = 0
        data_compiled = 0
        data_failed = 0
        k_facts_added = 0
        evidence_facts = 0
        blocked_evidence = 0
        reason_counts: Counter[str] = Counter()
        effort_counts: Counter[str] = Counter()
        source_counts: Counter[str] = Counter()
        details: list[dict[str, object]] = []

        for index, (question, choices, gold) in enumerate(cases):
            question_ir = compiler.問題IR(question, choices)
            references = HDS参照検索(provider, question_ir)
            if not references:
                retrieval_empty += 1
            docs_total += len(references)
            source_counts.update(r.供給器 for r in references)

            inference = HDS選択推論実行(
                question_ir,
                tuple(references),
                コンパイル=compiler.コンパイル,
                基礎能力核=base_core,
            )
            predicted = inference.回答ラベル
            is_answered = inference.状態 == "APPROVE" and predicted is not None
            is_correct = bool(is_answered and predicted == gold)
            answered += int(is_answered)
            suspended += int(not is_answered)
            correct_count += int(is_correct)
            reason_counts.update(inference.理由)
            data_compiled += inference.Dataコンパイル数
            data_failed += inference.Dataコンパイル失敗数
            k_facts_added += inference.K追加事実数
            evidence_facts += inference.K証拠事実数
            blocked_evidence += inference.K証拠阻害事実数
            if inference.K3結果 is not None:
                effort_counts[inference.K3結果.努力水準] += 1

            details.append(
                {
                    "index": index,
                    "predicted": predicted,
                    "gold": gold,
                    "correct": is_correct,
                    "status": inference.状態,
                    "reasons": list(inference.理由),
                    "retrieved": len(references),
                    "sources": [r.供給器 for r in references],
                    "data_compiled": inference.Dataコンパイル数,
                    "data_compile_failed": inference.Dataコンパイル失敗数,
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
            )
            print(
                f"CASE {index + 1:03d}/198 status={inference.状態} pred={predicted} "
                f"correct={is_correct} retrieved={len(references)}",
                flush=True,
            )

        result = {
            "schema": "minidora.gpqa.current-measurement.v1",
            "protocol": {
                "dataset": "official idavidrein/gpqa dataset.zip / gpqa_diamond.csv",
                "dataset_url": DATASET_URL,
                "dataset_zip_sha256": zip_hash,
                "dataset_csv_sha256": csv_hash,
                "n": len(cases),
                "choice_shuffle_seed": SEED,
                "compiler": "MINIDORA public standard HDS Compiler; Japanese-base role projection; benchmark-agnostic",
                "gold_boundary": "gold used only after inference for scoring",
                "openalex_enabled": api_key is not None,
                "wikipedia_languages": ["en"],
                "runtime": "current repository head; HDS choice native R->HDS->K->J",
            },
            "metrics": {
                "correct": correct_count,
                "total": len(cases),
                "accuracy_percent": 100.0 * correct_count / len(cases),
                "answered": answered,
                "answer_rate_percent": 100.0 * answered / len(cases),
                "suspended": suspended,
                "retrieval_empty": retrieval_empty,
                "documents_retrieved": docs_total,
                "data_compiled": data_compiled,
                "data_compile_failed": data_failed,
                "k_facts_added": k_facts_added,
                "evidence_facts": evidence_facts,
                "blocked_evidence_facts": blocked_evidence,
                "source_counts": dict(sorted(source_counts.items())),
                "reason_counts": dict(sorted(reason_counts.items())),
                "effort_counts": dict(sorted(effort_counts.items())),
            },
            "baseline_reference_only_not_directly_comparable": {
                "correct": 8,
                "total": 198,
                "accuracy_percent": 4.040404040404041,
                "reason": "prototype baseline used a different private HDS Compiler whose exact executable implementation is unavailable",
            },
            "details": details,
        }
        out = Path(os.environ.get("MINIDORA_GPQA_OUT", "gpqa_current_measurement.json"))
        out.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        print("MINIDORA_GPQA_RESULT=" + json.dumps(result["metrics"], ensure_ascii=False), flush=True)
        print(f"RESULT_FILE={out}", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

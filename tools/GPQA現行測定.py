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

from minidora.HDS選択実行系 import HDS選択推論実行
from minidora.HDS構文化器_v1 import 公開HDSコンパイラ
from minidora.HDS参照 import HDS参照検索
from minidora.K3機能 import K3相当能力核
from minidora.標準参照 import 一般知識参照供給器


DATASET_URL = "https://raw.githubusercontent.com/idavidrein/gpqa/main/dataset.zip"
DATASET_PASSWORD = b"deserted-untie-orchid"
SEED = 0
LABELS = ("A", "B", "C", "D")

# 旧ベンチ入口との互換名。実体は公開標準HDS Compiler。
汎用意味射影構文化器 = 公開HDSコンパイラ


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
        構文化器 = 公開HDSコンパイラ()
        base_模型核 = K3相当能力核()

        correct_count = 0
        answered = 0
        suspended = 0
        取得_empty = 0
        docs_total = 0
        資料_compiled = 0
        資料_failed = 0
        k_facts_added = 0
        証拠_facts = 0
        blocked_証拠 = 0
        reason_counts: Counter[str] = Counter()
        計算量_counts: Counter[str] = Counter()
        情報源_counts: Counter[str] = Counter()
        details: list[dict[str, object]] = []

        for index, (question, choices, gold) in enumerate(cases):
            question_ir = 構文化器.問題IR(question, choices)
            references = HDS参照検索(provider, question_ir)
            if not references:
                取得_empty += 1
            docs_total += len(references)
            情報源_counts.update(r.供給器 for r in references)

            inference = HDS選択推論実行(
                question_ir,
                tuple(references),
                コンパイル=構文化器.コンパイル,
                基礎能力核=base_模型核,
            )
            predicted = inference.回答ラベル
            is_answered = inference.状態 == "APPROVE" and predicted is not None
            is_correct = bool(is_answered and predicted == gold)
            answered += int(is_answered)
            suspended += int(not is_answered)
            correct_count += int(is_correct)
            reason_counts.update(inference.理由)
            資料_compiled += inference.資料コンパイル数
            資料_failed += inference.資料コンパイル失敗数
            k_facts_added += inference.K追加事実数
            証拠_facts += inference.K証拠事実数
            blocked_証拠 += inference.K証拠阻害事実数
            if inference.K3結果 is not None:
                計算量_counts[inference.K3結果.努力水準] += 1

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
                    '資料_compiled': inference.資料コンパイル数,
                    '資料_compile_failed': inference.資料コンパイル失敗数,
                    '計算量': inference.K3結果.努力水準 if inference.K3結果 else None,
                    '候補_diagnostics': [
                        {
                            "label": d.候補,
                            "score": d.合計得点,
                            '証拠_score': d.証拠得点,
                            '関係図_score': d.関係図得点,
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

        結果 = {
            "契約形式": "minidora.gpqa.current-measurement.v1",
            "protocol": {
                "dataset": "official idavidrein/gpqa dataset.zip / gpqa_diamond.csv",
                "dataset_url": DATASET_URL,
                "dataset_zip_sha256": zip_hash,
                "資料集合CSV_SHA256": csv_hash,
                "n": len(cases),
                "選択肢シャッフル種": SEED,
                '構文化器': "MINIDORA public standard HDS Compiler; Japanese-base role projection; benchmark-agnostic",
                'gold_境界': "gold used only after inference for scoring",
                "OpenAlex有効": api_key is not None,
                "Wikipedia言語群": ["en"],
                "実行系": "current repository head; HDS choice native R->HDS->K->J",
            },
            "metrics": {
                "correct": correct_count,
                "total": len(cases),
                "accuracy_percent": 100.0 * correct_count / len(cases),
                "answered": answered,
                "answer_rate_percent": 100.0 * answered / len(cases),
                "suspended": suspended,
                '取得_empty': 取得_empty,
                "documents_retrieved": docs_total,
                '資料_compiled': 資料_compiled,
                '資料_compile_failed': 資料_failed,
                "k_facts_added": k_facts_added,
                '証拠_facts': 証拠_facts,
                'blocked_証拠_facts': blocked_証拠,
                '情報源_counts': dict(sorted(情報源_counts.items())),
                "reason_counts": dict(sorted(reason_counts.items())),
                '計算量_counts': dict(sorted(計算量_counts.items())),
            },
            'baseline_参照_only_not_directly_comparable': {
                "correct": 8,
                "total": 198,
                "accuracy_percent": 4.040404040404041,
                "reason": "prototype baseline used a different private HDS Compiler whose exact executable implementation is unavailable",
            },
            "details": details,
        }
        out = Path(os.environ.get("MINIDORA_GPQA_OUT", "gpqa_current_measurement.json"))
        out.write_text(json.dumps(結果, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        print("MINIDORA_GPQA_RESULT=" + json.dumps(結果["metrics"], ensure_ascii=False), flush=True)
        print(f"RESULT_FILE={out}", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

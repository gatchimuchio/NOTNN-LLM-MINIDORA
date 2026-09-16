from __future__ import annotations

import argparse
import csv
import hashlib
import io
import json
import random
import sys
import tempfile
import urllib.request
import unittest
import zipfile
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from minidora.HDS構文化器_v1 import 公開HDSコンパイラ
from minidora.HDS実行系射影 import HDSK候補代入可能, HDSK候補射影, HDSK質問射影


DATASET_URL = "https://raw.githubusercontent.com/idavidrein/gpqa/main/dataset.zip"
DATASET_PASSWORD = b"deserted-untie-orchid"
選択肢_SHUFFLE_SEED = 0


def 監査入力読込(csv_path: Path) -> tuple[tuple[str, tuple[str, ...]], ...]:
    """CSVの出自ラベル・正解解説を境界で捨て、問いと匿名候補だけを渡す。"""
    rng = random.Random(選択肢_SHUFFLE_SEED)
    cases = []
    with csv_path.open("r", encoding="utf-8-sig", newline="") as f:
        for row in csv.DictReader(f):
            choices = [str(row[key]) for key in (
                "Incorrect Answer 1", "Incorrect Answer 2", "Incorrect Answer 3", "Correct Answer",
            )]
            # 正式runnerと同じ順序。正解位置の算出・保存は行わない。
            rng.shuffle(choices)
            cases.append((str(row["Question"]), tuple(choices)))
    return tuple(cases)


def 人工射影契約監査() -> dict[str, object]:
    '正解解説の代わりに、既存の人工資料・残差境界の意味契約を実行する。'
    paths = (
        ROOT / "tests/test_projection_chain_fidelity_v1.py",
        ROOT / "tests/test_hds_residual_evidence.py",
        ROOT / "tests/test_projection_audit_boundary.py",
    )
    loader = unittest.TestLoader()
    suite = unittest.TestSuite(
        loader.discover(str(path.parent), pattern=path.name) for path in paths
    )
    stream = io.StringIO()
    結果 = unittest.TextTestRunner(stream=stream, verbosity=1).run(suite)
    valid = 結果.wasSuccessful() and 結果.testsRun > 0 and not 結果.skipped
    return {
        "purpose": "人工入力による方向・極性・条件・未知関係・残差と監査入力境界の契約検証",
        "sources_sha256": {
            path.relative_to(ROOT).as_posix(): hashlib.sha256(path.read_bytes()).hexdigest()
            for path in paths
        },
        "tests_run": 結果.testsRun,
        "failures": [test.id() for test, _ in 結果.failures],
        "errors": [test.id() for test, _ in 結果.errors],
        "skipped": [test.id() for test, _ in 結果.skipped],
        "passed": valid,
    }


def _download_csv(work: Path) -> Path:
    archive = work / "dataset.zip"
    request = urllib.request.Request(DATASET_URL, headers={"User-Agent": "MINIDORA-Projection-Audit/1.0"})
    with urllib.request.urlopen(request, timeout=60) as response, archive.open("wb") as out:
        out.write(response.read())
    with zipfile.ZipFile(archive) as zf:
        matches = [name for name in zf.namelist() if name.endswith("gpqa_diamond.csv")]
        if len(matches) != 1:
            raise RuntimeError(f"gpqa_diamond.csv not uniquely found: {matches}")
        zf.extract(matches[0], path=work, pwd=DATASET_PASSWORD)
        return work / matches[0]


def _関係は質問か(関係: object) -> bool:
    conditions = tuple(str(x) for x in getattr(関係, "条件", ()))
    return any(x.startswith("不足位置=") for x in conditions)


def _意味接続質問(関係: object) -> bool:
    conditions = tuple(str(x) for x in getattr(関係, "条件", ()))
    return any(x.startswith("英日意味射影=") for x in conditions)


def _selection_query_closure(関係: object) -> bool:
    conditions = tuple(str(x) for x in getattr(関係, "条件", ()))
    return any(x == "選択問題閉包=v0.1" for x in conditions)


def _意味損失(ir: object) -> bool:
    return any(str(getattr(item, "種別", "")) == '意味_loss' for item in getattr(ir, "残差", ()))


def _topic_count(ir: object) -> int:
    return sum(str(getattr(coord, "種別", "")) == "対象.主題語" for coord in getattr(ir, "座標", ()))


def _関係種別群(ir: object) -> tuple[str, ...]:
    return tuple(str(getattr(rel, "種別", "")) for rel in getattr(ir, "関係", ()))


def 意味被覆監査(cases, 構文化器) -> dict[str, object]:
    question_total = 0
    question_any_関係 = 0
    question_open_関係 = 0
    question_bridge_関係 = 0
    question_selection_closure = 0
    question_k_関係 = 0
    question_k_topic_only = 0
    question_no_関係_no_意味_loss = 0
    question_関係_types: Counter[str] = Counter()
    question_k_関係_types: Counter[str] = Counter()

    候補_total = 0
    候補_any_関係 = 0
    候補_k_関係 = 0
    候補_substitutable = 0
    候補_関係_or_substitutable = 0
    候補_neither = 0
    候補_neither_coord_kinds: Counter[str] = Counter()
    候補_no_関係_no_意味_loss = 0
    problems_with_候補_neither = 0

    details: list[dict[str, object]] = []

    for index, (question, choices) in enumerate(cases):
        question_ir = 構文化器.問題IR(question, choices)
        k_question = HDSK質問射影(question_ir)
        q_relations = tuple(question_ir.関係)
        q_k_relations = tuple(k_question.関係)
        q_open = tuple(rel for rel in q_relations if _関係は質問か(rel))
        q_bridge = tuple(rel for rel in q_open if _意味接続質問(rel))
        q_selection_closure = tuple(rel for rel in q_open if _selection_query_closure(rel))

        question_total += 1
        question_any_関係 += int(bool(q_relations))
        question_open_関係 += int(bool(q_open))
        question_bridge_関係 += int(bool(q_bridge))
        question_selection_closure += int(bool(q_selection_closure))
        question_k_関係 += int(bool(q_k_relations))
        question_k_topic_only += int(not q_k_relations and _topic_count(k_question) > 0)
        question_no_関係_no_意味_loss += int(not q_relations and not _意味損失(question_ir))
        question_関係_types.update(_関係種別群(question_ir))
        question_k_関係_types.update(_関係種別群(k_question))

        候補_関係_count = 0
        候補_k_関係_count = 0
        候補_substitute_count = 0
        候補_neither_count = 0
        for 選択肢 in choices:
            候補_ir = 構文化器.意味コンパイル(選択肢)
            k_候補 = HDSK候補射影(候補_ir)
            候補_total += 1
            関係_present = bool(候補_ir.関係)
            k_関係_present = bool(k_候補.関係)
            候補_any_関係 += int(関係_present)
            候補_k_関係 += int(k_関係_present)
            substitutable = HDSK候補代入可能(候補_ir)
            covered = 関係_present or substitutable
            候補_substitutable += int(substitutable)
            候補_関係_or_substitutable += int(covered)
            候補_neither += int(not covered)
            候補_no_関係_no_意味_loss += int(not 関係_present and not _意味損失(候補_ir))
            候補_関係_count += int(関係_present)
            候補_k_関係_count += int(k_関係_present)
            候補_substitute_count += int(substitutable)
            候補_neither_count += int(not covered)
            if not covered:
                候補_neither_coord_kinds.update(str(coord.種別) for coord in 候補_ir.座標)
        problems_with_候補_neither += int(候補_neither_count > 0)

        details.append(
            {
                "index": index,
                'question_関係_count': len(q_relations),
                'question_open_関係_count': len(q_open),
                'question_bridge_関係_count': len(q_bridge),
                "question_selection_closure_count": len(q_selection_closure),
                'question_k_関係_count': len(q_k_relations),
                "question_k_topic_only": bool(not q_k_relations and _topic_count(k_question) > 0),
                'question_意味_loss': _意味損失(question_ir),
                '候補_関係_count': 候補_関係_count,
                '候補_k_関係_count': 候補_k_関係_count,
                '候補_substitutable_count': 候補_substitute_count,
                '候補_neither_count': 候補_neither_count,
            }
        )

    def pct(value: int, total: int) -> float:
        return 100.0 * value / total if total else 0.0

    return {
        "契約形式": 'minidora.射影-連鎖-audit.構文化器-gpqa.v2',
        "purpose": '問いと匿名4候補の意味被覆監査。正解ラベル・正解解説は構文化器へ入力しない',
        "question": {
            "total": question_total,
            'any_関係': question_any_関係,
            'any_関係_percent': pct(question_any_関係, question_total),
            'open_question_関係': question_open_関係,
            'open_question_関係_percent': pct(question_open_関係, question_total),
            '意味_bridge_question_関係': question_bridge_関係,
            '意味_bridge_question_関係_percent': pct(question_bridge_関係, question_total),
            'selection_文脈_generic_closure': question_selection_closure,
            'selection_文脈_generic_closure_percent': pct(question_selection_closure, question_total),
            'k_関係': question_k_関係,
            'k_関係_percent': pct(question_k_関係, question_total),
            "k_topic_only": question_k_topic_only,
            "k_topic_only_percent": pct(question_k_topic_only, question_total),
            'no_関係_without_意味_loss': question_no_関係_no_意味_loss,
            '関係_types': dict(sorted(question_関係_types.items())),
            'k_関係_types': dict(sorted(question_k_関係_types.items())),
        },
        '候補': {
            "total": 候補_total,
            'any_関係': 候補_any_関係,
            'any_関係_percent': pct(候補_any_関係, 候補_total),
            'k_関係': 候補_k_関係,
            'k_関係_percent': pct(候補_k_関係, 候補_total),
            "substitutable_as_entity": 候補_substitutable,
            "substitutable_as_entity_percent": pct(候補_substitutable, 候補_total),
            '関係_or_substitutable': 候補_関係_or_substitutable,
            '関係_or_substitutable_percent': pct(候補_関係_or_substitutable, 候補_total),
            'neither_関係_nor_substitutable': 候補_neither,
            'neither_関係_nor_substitutable_percent': pct(候補_neither, 候補_total),
            'problems_with_候補_neither': problems_with_候補_neither,
            "neither_coord_kinds": dict(sorted(候補_neither_coord_kinds.items())),
            'no_関係_without_意味_loss': 候補_no_関係_no_意味_loss,
        },
        "details": details,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="問い・匿名候補の意味被覆と人工射影契約を監査する")
    parser.add_argument("--csv", type=Path, help="取得済みの正式GPQA Diamond CSV")
    parser.add_argument("--out", type=Path, default=ROOT / '射影_連鎖_audit.json')
    args = parser.parse_args(argv)
    with tempfile.TemporaryDirectory(prefix='minidora-射影-audit-') as td:
        csv_path = args.csv or _download_csv(Path(td))
        csv_hash = hashlib.sha256(csv_path.read_bytes()).hexdigest()
        cases = 監査入力読込(csv_path)
    if len(cases) != 198:
        raise RuntimeError(f"GPQA Diamond expected 198 rows, got {len(cases)}")
    結果 = 意味被覆監査(cases, 公開HDSコンパイラ())
    結果.update({
        "dataset": "GPQA Diamond 198",
        "資料集合CSV_SHA256": csv_hash,
        "選択肢シャッフル種": 選択肢_SHUFFLE_SEED,
        'synthetic_射影_contracts': 人工射影契約監査(),
        "legacy_expert_explanation_comparable": False,
    })
    out = args.out
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(結果, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print("MINIDORA_PROJECTION_CHAIN_AUDIT=" + json.dumps({
        "question": 結果["question"],
        '候補': 結果['候補'],
        'synthetic_射影_contracts': 結果['synthetic_射影_contracts'],
    }, ensure_ascii=False))
    print(f"RESULT_FILE={out}")
    return 0 if 結果['synthetic_射影_contracts']["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())

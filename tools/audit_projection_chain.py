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

from minidora.hds_compiler_v1 import 公開HDSコンパイラ
from minidora.hds_runtime_projection import HDSK候補代入可能, HDSK候補射影, HDSK質問射影


DATASET_URL = "https://raw.githubusercontent.com/idavidrein/gpqa/main/dataset.zip"
DATASET_PASSWORD = b"deserted-untie-orchid"
CHOICE_SHUFFLE_SEED = 0


def 監査入力読込(csv_path: Path) -> tuple[tuple[str, tuple[str, ...]], ...]:
    """CSVの出自ラベル・正解解説を境界で捨て、問いと匿名候補だけを渡す。"""
    rng = random.Random(CHOICE_SHUFFLE_SEED)
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
    """正解解説の代わりに、既存の人工Data・残差境界の意味契約を実行する。"""
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
    result = unittest.TextTestRunner(stream=stream, verbosity=1).run(suite)
    valid = result.wasSuccessful() and result.testsRun > 0 and not result.skipped
    return {
        "purpose": "人工入力による方向・極性・条件・未知関係・残差と監査入力境界の契約検証",
        "sources_sha256": {
            path.relative_to(ROOT).as_posix(): hashlib.sha256(path.read_bytes()).hexdigest()
            for path in paths
        },
        "tests_run": result.testsRun,
        "failures": [test.id() for test, _ in result.failures],
        "errors": [test.id() for test, _ in result.errors],
        "skipped": [test.id() for test, _ in result.skipped],
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


def _relation_is_question(relation: object) -> bool:
    conditions = tuple(str(x) for x in getattr(relation, "条件", ()))
    return any(x.startswith("不足位置=") for x in conditions)


def _semantic_bridge_question(relation: object) -> bool:
    conditions = tuple(str(x) for x in getattr(relation, "条件", ()))
    return any(x.startswith("英日意味射影=") for x in conditions)


def _selection_query_closure(relation: object) -> bool:
    conditions = tuple(str(x) for x in getattr(relation, "条件", ()))
    return any(x == "選択問題閉包=v0.1" for x in conditions)


def _semantic_loss(ir: object) -> bool:
    return any(str(getattr(item, "種別", "")) == "semantic_loss" for item in getattr(ir, "残差", ()))


def _topic_count(ir: object) -> int:
    return sum(str(getattr(coord, "種別", "")) == "対象.主題語" for coord in getattr(ir, "座標", ()))


def _relation_types(ir: object) -> tuple[str, ...]:
    return tuple(str(getattr(rel, "種別", "")) for rel in getattr(ir, "関係", ()))


def 意味被覆監査(cases, compiler) -> dict[str, object]:
    question_total = 0
    question_any_relation = 0
    question_open_relation = 0
    question_bridge_relation = 0
    question_selection_closure = 0
    question_k_relation = 0
    question_k_topic_only = 0
    question_no_relation_no_semantic_loss = 0
    question_relation_types: Counter[str] = Counter()
    question_k_relation_types: Counter[str] = Counter()

    candidate_total = 0
    candidate_any_relation = 0
    candidate_k_relation = 0
    candidate_substitutable = 0
    candidate_relation_or_substitutable = 0
    candidate_neither = 0
    candidate_neither_coord_kinds: Counter[str] = Counter()
    candidate_no_relation_no_semantic_loss = 0
    problems_with_candidate_neither = 0

    details: list[dict[str, object]] = []

    for index, (question, choices) in enumerate(cases):
        question_ir = compiler.問題IR(question, choices)
        k_question = HDSK質問射影(question_ir)
        q_relations = tuple(question_ir.関係)
        q_k_relations = tuple(k_question.関係)
        q_open = tuple(rel for rel in q_relations if _relation_is_question(rel))
        q_bridge = tuple(rel for rel in q_open if _semantic_bridge_question(rel))
        q_selection_closure = tuple(rel for rel in q_open if _selection_query_closure(rel))

        question_total += 1
        question_any_relation += int(bool(q_relations))
        question_open_relation += int(bool(q_open))
        question_bridge_relation += int(bool(q_bridge))
        question_selection_closure += int(bool(q_selection_closure))
        question_k_relation += int(bool(q_k_relations))
        question_k_topic_only += int(not q_k_relations and _topic_count(k_question) > 0)
        question_no_relation_no_semantic_loss += int(not q_relations and not _semantic_loss(question_ir))
        question_relation_types.update(_relation_types(question_ir))
        question_k_relation_types.update(_relation_types(k_question))

        candidate_relation_count = 0
        candidate_k_relation_count = 0
        candidate_substitute_count = 0
        candidate_neither_count = 0
        for choice in choices:
            candidate_ir = compiler.意味コンパイル(choice)
            k_candidate = HDSK候補射影(candidate_ir)
            candidate_total += 1
            relation_present = bool(candidate_ir.関係)
            k_relation_present = bool(k_candidate.関係)
            candidate_any_relation += int(relation_present)
            candidate_k_relation += int(k_relation_present)
            substitutable = HDSK候補代入可能(candidate_ir)
            covered = relation_present or substitutable
            candidate_substitutable += int(substitutable)
            candidate_relation_or_substitutable += int(covered)
            candidate_neither += int(not covered)
            candidate_no_relation_no_semantic_loss += int(not relation_present and not _semantic_loss(candidate_ir))
            candidate_relation_count += int(relation_present)
            candidate_k_relation_count += int(k_relation_present)
            candidate_substitute_count += int(substitutable)
            candidate_neither_count += int(not covered)
            if not covered:
                candidate_neither_coord_kinds.update(str(coord.種別) for coord in candidate_ir.座標)
        problems_with_candidate_neither += int(candidate_neither_count > 0)

        details.append(
            {
                "index": index,
                "question_relation_count": len(q_relations),
                "question_open_relation_count": len(q_open),
                "question_bridge_relation_count": len(q_bridge),
                "question_selection_closure_count": len(q_selection_closure),
                "question_k_relation_count": len(q_k_relations),
                "question_k_topic_only": bool(not q_k_relations and _topic_count(k_question) > 0),
                "question_semantic_loss": _semantic_loss(question_ir),
                "candidate_relation_count": candidate_relation_count,
                "candidate_k_relation_count": candidate_k_relation_count,
                "candidate_substitutable_count": candidate_substitute_count,
                "candidate_neither_count": candidate_neither_count,
            }
        )

    def pct(value: int, total: int) -> float:
        return 100.0 * value / total if total else 0.0

    return {
        "schema": "minidora.projection-chain-audit.compiler-gpqa.v2",
        "purpose": "問いと匿名4候補の意味被覆監査。正解ラベル・正解解説はCompilerへ入力しない",
        "question": {
            "total": question_total,
            "any_relation": question_any_relation,
            "any_relation_percent": pct(question_any_relation, question_total),
            "open_question_relation": question_open_relation,
            "open_question_relation_percent": pct(question_open_relation, question_total),
            "semantic_bridge_question_relation": question_bridge_relation,
            "semantic_bridge_question_relation_percent": pct(question_bridge_relation, question_total),
            "selection_context_generic_closure": question_selection_closure,
            "selection_context_generic_closure_percent": pct(question_selection_closure, question_total),
            "k_relation": question_k_relation,
            "k_relation_percent": pct(question_k_relation, question_total),
            "k_topic_only": question_k_topic_only,
            "k_topic_only_percent": pct(question_k_topic_only, question_total),
            "no_relation_without_semantic_loss": question_no_relation_no_semantic_loss,
            "relation_types": dict(sorted(question_relation_types.items())),
            "k_relation_types": dict(sorted(question_k_relation_types.items())),
        },
        "candidate": {
            "total": candidate_total,
            "any_relation": candidate_any_relation,
            "any_relation_percent": pct(candidate_any_relation, candidate_total),
            "k_relation": candidate_k_relation,
            "k_relation_percent": pct(candidate_k_relation, candidate_total),
            "substitutable_as_entity": candidate_substitutable,
            "substitutable_as_entity_percent": pct(candidate_substitutable, candidate_total),
            "relation_or_substitutable": candidate_relation_or_substitutable,
            "relation_or_substitutable_percent": pct(candidate_relation_or_substitutable, candidate_total),
            "neither_relation_nor_substitutable": candidate_neither,
            "neither_relation_nor_substitutable_percent": pct(candidate_neither, candidate_total),
            "problems_with_candidate_neither": problems_with_candidate_neither,
            "neither_coord_kinds": dict(sorted(candidate_neither_coord_kinds.items())),
            "no_relation_without_semantic_loss": candidate_no_relation_no_semantic_loss,
        },
        "details": details,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="問い・匿名候補の意味被覆と人工射影契約を監査する")
    parser.add_argument("--csv", type=Path, help="取得済みの正式GPQA Diamond CSV")
    parser.add_argument("--out", type=Path, default=ROOT / "projection_chain_audit.json")
    args = parser.parse_args(argv)
    with tempfile.TemporaryDirectory(prefix="minidora-projection-audit-") as td:
        csv_path = args.csv or _download_csv(Path(td))
        csv_hash = hashlib.sha256(csv_path.read_bytes()).hexdigest()
        cases = 監査入力読込(csv_path)
    if len(cases) != 198:
        raise RuntimeError(f"GPQA Diamond expected 198 rows, got {len(cases)}")
    result = 意味被覆監査(cases, 公開HDSコンパイラ())
    result.update({
        "dataset": "GPQA Diamond 198",
        "dataset_csv_sha256": csv_hash,
        "choice_shuffle_seed": CHOICE_SHUFFLE_SEED,
        "synthetic_projection_contracts": 人工射影契約監査(),
        "legacy_expert_explanation_comparable": False,
    })
    out = args.out
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print("MINIDORA_PROJECTION_CHAIN_AUDIT=" + json.dumps({
        "question": result["question"],
        "candidate": result["candidate"],
        "synthetic_projection_contracts": result["synthetic_projection_contracts"],
    }, ensure_ascii=False))
    print(f"RESULT_FILE={out}")
    return 0 if result["synthetic_projection_contracts"]["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())

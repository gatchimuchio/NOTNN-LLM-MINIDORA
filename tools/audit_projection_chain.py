from __future__ import annotations

import csv
import json
import sys
import tempfile
import urllib.request
import zipfile
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from minidora.hds_compiler_v1 import 公開HDSコンパイラ
from minidora.hds_runtime_projection import HDSK候補代入可能, HDSK候補射影, HDSK質問射影, HDSKData射影


DATASET_URL = "https://raw.githubusercontent.com/idavidrein/gpqa/main/dataset.zip"
DATASET_PASSWORD = b"deserted-untie-orchid"


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


def main() -> int:
    compiler = 公開HDSコンパイラ()
    with tempfile.TemporaryDirectory(prefix="minidora-projection-audit-") as td:
        csv_path = _download_csv(Path(td))
        with csv_path.open("r", encoding="utf-8-sig", newline="") as f:
            rows = list(csv.DictReader(f))

    if len(rows) != 198:
        raise RuntimeError(f"GPQA Diamond expected 198 rows, got {len(rows)}")

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

    explanation_total = 0
    explanation_nonempty = 0
    explanation_any_relation = 0
    explanation_k_relation = 0
    explanation_topic_only = 0
    explanation_no_relation_no_semantic_loss = 0
    explanation_relation_types: Counter[str] = Counter()
    explanation_k_relation_types: Counter[str] = Counter()

    details: list[dict[str, object]] = []

    for index, row in enumerate(rows):
        question = str(row.get("Question", ""))
        choices = (
            str(row.get("Correct Answer", "")),
            str(row.get("Incorrect Answer 1", "")),
            str(row.get("Incorrect Answer 2", "")),
            str(row.get("Incorrect Answer 3", "")),
        )
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

        explanation = str(row.get("Explanation", "") or "").strip()
        explanation_present = bool(explanation)
        exp_relation_count = 0
        exp_k_relation_count = 0
        exp_topic_only = False
        exp_semantic_loss = False
        if explanation_present:
            explanation_nonempty += 1
            explanation_ir = compiler.意味コンパイル(explanation)
            k_explanation = HDSKData射影(explanation_ir)
            exp_relation_count = len(explanation_ir.関係)
            exp_k_relation_count = len(k_explanation.関係)
            exp_topic_only = exp_k_relation_count == 0 and _topic_count(k_explanation) > 0
            exp_semantic_loss = _semantic_loss(explanation_ir)
            explanation_any_relation += int(exp_relation_count > 0)
            explanation_k_relation += int(exp_k_relation_count > 0)
            explanation_topic_only += int(exp_topic_only)
            explanation_no_relation_no_semantic_loss += int(exp_relation_count == 0 and not exp_semantic_loss)
            explanation_relation_types.update(_relation_types(explanation_ir))
            explanation_k_relation_types.update(_relation_types(k_explanation))
        explanation_total += 1

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
                "explanation_present": explanation_present,
                "explanation_relation_count": exp_relation_count,
                "explanation_k_relation_count": exp_k_relation_count,
                "explanation_topic_only": exp_topic_only,
                "explanation_semantic_loss": exp_semantic_loss,
            }
        )

    def pct(value: int, total: int) -> float:
        return 100.0 * value / total if total else 0.0

    result = {
        "schema": "minidora.projection-chain-audit.compiler-gpqa.v1",
        "dataset": "GPQA Diamond 198",
        "purpose": "semantic coverage audit only; gold is never used for inference",
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
        "expert_explanation": {
            "rows": explanation_total,
            "nonempty": explanation_nonempty,
            "any_relation": explanation_any_relation,
            "any_relation_percent_of_nonempty": pct(explanation_any_relation, explanation_nonempty),
            "k_relation": explanation_k_relation,
            "k_relation_percent_of_nonempty": pct(explanation_k_relation, explanation_nonempty),
            "topic_only": explanation_topic_only,
            "topic_only_percent_of_nonempty": pct(explanation_topic_only, explanation_nonempty),
            "no_relation_without_semantic_loss": explanation_no_relation_no_semantic_loss,
            "relation_types": dict(sorted(explanation_relation_types.items())),
            "k_relation_types": dict(sorted(explanation_k_relation_types.items())),
        },
        "details": details,
    }
    out = ROOT / "projection_chain_audit.json"
    out.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print("MINIDORA_PROJECTION_CHAIN_AUDIT=" + json.dumps({
        "question": result["question"],
        "candidate": result["candidate"],
        "expert_explanation": result["expert_explanation"],
    }, ensure_ascii=False))
    print(f"RESULT_FILE={out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

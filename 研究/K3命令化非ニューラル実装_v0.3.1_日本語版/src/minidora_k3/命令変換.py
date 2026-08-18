from __future__ import annotations

import hashlib
import json
import re
from typing import Any, Mapping, Sequence

from .演算 import (
    OperatorError,
    OperatorResult,
    solve_arithmetic,
    solve_boolean,
    solve_count,
    solve_date,
    solve_ordering,
    solve_retrieval,
    solve_swaps,
)
from .型 import Instruction, Program, ReferenceRecord


def _digest(value: Any) -> str:
    return hashlib.sha256(json.dumps(value, ensure_ascii=False, sort_keys=True, default=str).encode()).hexdigest()


def classify_task(text: str) -> str:
    stripped = text.strip()
    if re.search(r"\b(?:True|False|not|and|or)\b", stripped) and "選択肢:" not in stripped:
        return "論理式"
    arithmetic = stripped.translate(str.maketrans({"×": "*", "−": "-", "–": "-", "—": "-"})).rstrip("= ")
    if arithmetic and re.fullmatch(r"[0-9+\-*()\s]+", arithmetic):
        return "算術"
    if "全部で" in stripped and re.search(r"\d+(?:本|台|個|粒|房|匹|頭|種類|点|脚|株|片|玉|冊|つ)", stripped):
        return "数量"
    if "選択肢:" in stripped and re.search(r"(?:交換|交代)", stripped) and all(name in stripped for name in ("アリス", "ボブ", "クレア")):
        return "状態遷移"
    if "選択肢:" in stripped and ("固定された順序" in stripped or re.search(r"(?:右側|左側|最も古い|最も新しい|安価|下位)", stripped)):
        return "順序"
    if "MM/DD/YYYY" in stripped and "選択肢:" in stripped:
        return "日付"
    return "参照"


_REQUIRED_REFERENCE = {
    "論理式": "op_boolean_v1",
    "算術": "op_arithmetic_v1",
    "数量": "op_count_v1",
    "状態遷移": "op_swap_v1",
    "順序": "op_order_v1",
    "日付": "op_date_v1",
    "参照": "op_retrieval_v1",
}


class InstructionCompiler:
    """自然言語＋外部参照を、明示命令Programへ変換する。"""

    def compile(self, text: str, references: Sequence[ReferenceRecord]) -> Program:
        task = classify_task(text)
        required = _REQUIRED_REFERENCE[task]
        ref_by_id = {row.record_id: row for row in references}
        if required not in ref_by_id:
            raise OperatorError(f"必須参照がありません: {required}")
        instructions = (
            Instruction("要求資料読込", {"text": text}),
            Instruction("参照資料読込", {"reference_ids": [row.record_id for row in references]}, tuple(row.record_id for row in references)),
            Instruction("問題中間表現変換", {"task_family": task}),
            Instruction({
                "論理式": "論理式実行", "算術": "算術式実行", "数量": "数量実行",
                "状態遷移": "状態遷移実行", "順序": "順序実行", "日付": "日付実行", "参照": "参照実行",
            }[task], {}),
            Instruction("独立再実行検証", {"task_family": task}),
            Instruction("全体照合", {}),
            Instruction("HDS採否", {}),
            Instruction("結果表現", {"言語": "ja"}),
        )
        return Program(
            program_id="program_" + _digest({"text": text, "task": task, "refs": sorted(ref_by_id)})[:24],
            task_family=task,
            instructions=instructions,
            input_data={"text": text},
            target_schema={"type": "choice" if "選択肢:" in text else "scalar"},
            evidence_ids=("input:" + _digest(text)[:24], *tuple(row.record_id for row in references)),
            compile_trace=(
                {"stage": "問題系統判定", "task_family": task},
                {"stage": "参照結合", "required": required, "bound": sorted(ref_by_id)},
                {"stage": "中間表現出力", "opcodes": [row.opcode for row in instructions]},
            ),
        )


class ProgramExecutor:
    def execute(self, program: Program, references: Sequence[ReferenceRecord]) -> OperatorResult:
        text = str(program.input_data["text"])
        ontology: dict[str, Sequence[str]] = {}
        for row in references:
            if row.kind == "ontology" and "category" in row.metadata:
                ontology[str(row.metadata["category"])] = tuple(row.metadata.get("items", ()))
        solver = {
            "論理式": lambda: solve_boolean(text),
            "算術": lambda: solve_arithmetic(text),
            "数量": lambda: solve_count(text, ontology),
            "状態遷移": lambda: solve_swaps(text),
            "順序": lambda: solve_ordering(text),
            "日付": lambda: solve_date(text),
            "参照": lambda: solve_retrieval(text, references),
        }.get(program.task_family)
        if solver is None:
            raise OperatorError(f"実行可能なoperatorがありません: {program.task_family}")
        return solver()

    def replay_verify(self, program: Program, references: Sequence[ReferenceRecord], expected_answer: str) -> Mapping[str, Any]:
        replay = self.execute(program, references)
        schema_ok = bool(re.fullmatch(r"\([A-F]\)", expected_answer)) if program.target_schema["type"] == "choice" else bool(expected_answer)
        return {
            "verifier": "決定的再実行",
            "passed": replay.answer == expected_answer and schema_ok,
            "replay_answer": replay.answer,
            "schema_ok": schema_ok,
            "payload_digest": _digest(replay.verifier_payload),
        }


命令変換器 = InstructionCompiler
手順実行器 = ProgramExecutor
問題系統を判定 = classify_task

"""K3の観測I/O probeを明示命令templateへ変換するbehavioral compiler。

公開weight roleだけでは回収できない学習済み作用を、black-box probeから
命令候補へ外在化するための第二経路。K3実出力を投入しない限りK3意味同等にはならない。
"""
from __future__ import annotations

import hashlib
import json
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Mapping, Sequence

from .命令変換 import InstructionCompiler, classify_task
from .型 import ReferenceRecord


@dataclass(frozen=True, slots=True)
class BehaviorProbe:
    probe_id: str
    input_text: str
    output_text: str
    status: str
    source_model: str
    source_ref: str
    metadata: Mapping[str, Any]


@dataclass(frozen=True, slots=True)
class BehaviorInstructionTemplate:
    template_id: str
    task_family: str
    opcodes: tuple[str, ...]
    output_schema: str
    source_probe_ids: tuple[str, ...]
    source_models: tuple[str, ...]
    conversion_state: str
    generalization_state: str


def _required_reference(task: str) -> ReferenceRecord:
    record_id = {
        "論理式": "op_boolean_v1",
        "算術": "op_arithmetic_v1",
        "数量": "op_count_v1",
        "状態遷移": "op_swap_v1",
        "順序": "op_order_v1",
        "日付": "op_date_v1",
        "参照": "op_retrieval_v1",
    }[task]
    return ReferenceRecord(record_id, "operator_semantics", record_id, record_id, (task,))


def compile_behavior_probes(probes: Sequence[BehaviorProbe]) -> tuple[BehaviorInstructionTemplate, ...]:
    groups: dict[tuple[str, str], list[BehaviorProbe]] = {}
    compiler = InstructionCompiler()
    for probe in probes:
        task = classify_task(probe.input_text)
        program = compiler.compile(probe.input_text, (_required_reference(task),))
        schema = str(program.target_schema["type"])
        groups.setdefault((task, schema), []).append(probe)

    templates: list[BehaviorInstructionTemplate] = []
    for (task, schema), rows in sorted(groups.items()):
        program = compiler.compile(rows[0].input_text, (_required_reference(task),))
        digest = hashlib.sha256(
            json.dumps(
                {"task": task, "schema": schema, "probes": sorted(row.probe_id for row in rows)},
                ensure_ascii=False,
                sort_keys=True,
            ).encode("utf-8")
        ).hexdigest()[:24]
        templates.append(
            BehaviorInstructionTemplate(
                template_id=f"behavior_template_{digest}",
                task_family=task,
                opcodes=tuple(item.opcode for item in program.instructions),
                output_schema=schema,
                source_probe_ids=tuple(sorted(row.probe_id for row in rows)),
                source_models=tuple(sorted({row.source_model for row in rows})),
                conversion_state="挙動命令雛形変換済",
                generalization_state="反実仮想及び保留標本検証要",
            )
        )
    return tuple(templates)


def load_probes(path: Path) -> tuple[BehaviorProbe, ...]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, list):
        raise ValueError("probe file rootはlistである必要があります")
    return tuple(BehaviorProbe(**row) for row in value)


def dump_templates(path: Path, templates: Sequence[BehaviorInstructionTemplate]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "templates": [asdict(row) for row in templates],
        "claim_boundary": {
            "behavioral_instruction_extraction": True,
            "K3_behavioral_semantics_compiled": any("Kimi K3" in row.source_models for row in templates),
            "K3_equivalence": False,
            "reason": "probe coverage and held-out generalization must be established",
        },
    }
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


挙動試験 = BehaviorProbe
挙動命令雛形 = BehaviorInstructionTemplate
挙動試験を命令化 = compile_behavior_probes
挙動試験を読む = load_probes
命令雛形を書く = dump_templates

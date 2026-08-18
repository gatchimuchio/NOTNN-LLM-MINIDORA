from __future__ import annotations

from dataclasses import dataclass, field
from enum import StrEnum
from typing import Any, Mapping


class RunStatus(StrEnum):
    合格 = "合格"
    保留 = "保留"
    失敗 = "失敗"
    非適用 = "非適用"
    PASS = 合格
    SUSPEND = 保留
    FAIL = 失敗
    NOT_APPLICABLE = 非適用


class Effort(StrEnum):
    低 = "低"
    高 = "高"
    最大 = "最大"
    LOW = 低
    HIGH = 高
    MAX = 最大

    @classmethod
    def _missing_(cls, value: object):
        return {"low": cls.低, "high": cls.高, "max": cls.最大}.get(str(value).casefold())


@dataclass(frozen=True, slots=True)
class ReferenceRecord:
    record_id: str
    kind: str
    title: str
    body: str
    tags: tuple[str, ...] = ()
    source: str = "local"
    authority: str = "参照"
    metadata: Mapping[str, Any] = field(default_factory=dict)


@dataclass(frozen=True, slots=True)
class Instruction:
    opcode: str
    args: Mapping[str, Any] = field(default_factory=dict)
    source_ids: tuple[str, ...] = ()


@dataclass(frozen=True, slots=True)
class Program:
    program_id: str
    task_family: str
    instructions: tuple[Instruction, ...]
    input_data: Mapping[str, Any]
    target_schema: Mapping[str, Any]
    evidence_ids: tuple[str, ...]
    compile_trace: tuple[Mapping[str, Any], ...] = ()


@dataclass(frozen=True, slots=True)
class Candidate:
    candidate_id: str
    answer: str
    task_family: str
    confidence: float
    evidence_ids: tuple[str, ...]
    verifier_results: tuple[Mapping[str, Any], ...]
    trace: tuple[Mapping[str, Any], ...]
    contradiction_ids: tuple[str, ...] = ()
    hazard_flags: tuple[str, ...] = ()


@dataclass(frozen=True, slots=True)
class Decision:
    status: RunStatus
    selected: Candidate | None
    reason_codes: tuple[str, ...]
    confidence: float


@dataclass(frozen=True, slots=True)
class RunResult:
    status: RunStatus
    answer: str
    task_family: str
    confidence: float
    reason_codes: tuple[str, ...]
    evidence_ids: tuple[str, ...]
    trace: tuple[Mapping[str, Any], ...]
    elapsed_ms: float


# 日本語公開名
実行状態 = RunStatus
計算量 = Effort
参照記録 = ReferenceRecord
命令 = Instruction
手順 = Program
候補 = Candidate
採否結果 = Decision
実行結果 = RunResult

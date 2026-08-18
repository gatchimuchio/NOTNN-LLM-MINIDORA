from __future__ import annotations
from dataclasses import dataclass
from typing import Any, Mapping

@dataclass(frozen=True, slots=True)
class OperatorResult:
    answer: str
    trace: tuple[Mapping[str, Any], ...]
    verifier_payload: Mapping[str, Any]
    evidence_ids: tuple[str, ...] = ()
    contradiction_ids: tuple[str, ...] = ()
    hazard_flags: tuple[str, ...] = ()

class OperatorError(ValueError):
    pass

演算誤り = OperatorError
演算結果 = OperatorResult

from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable

from .構造 import deterministic_top16
from .型 import Effort, ReferenceRecord


@dataclass(frozen=True, slots=True)
class Route:
    task_family: str
    experts: tuple[int, ...]
    shared_experts: tuple[int, int]
    effort: Effort
    budget: dict[str, int]
    reference_ids: tuple[str, ...]


class StableLatentRouter:
    BUDGETS = {
        Effort.LOW: {"max_reference": 4, "max_steps": 16, "max_stage_reads": 3, "verification_passes": 1},
        Effort.HIGH: {"max_reference": 12, "max_steps": 128, "max_stage_reads": 6, "verification_passes": 2},
        Effort.MAX: {"max_reference": 24, "max_steps": 1024, "max_stage_reads": 9, "verification_passes": 3},
    }

    def route(
        self,
        task_family: str,
        features: Iterable[str],
        references: Iterable[ReferenceRecord],
        effort: Effort,
    ) -> Route:
        refs = tuple(references)
        experts = deterministic_top16(task_family, (*features, *(tag for row in refs for tag in row.tags)))
        return Route(
            task_family=task_family,
            experts=experts,
            shared_experts=(896, 897),
            effort=effort,
            budget=dict(self.BUDGETS[effort]),
            reference_ids=tuple(row.record_id for row in refs),
        )


経路結果 = Route
安定潜在経路器 = StableLatentRouter

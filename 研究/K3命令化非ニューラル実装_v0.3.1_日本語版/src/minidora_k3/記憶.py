from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Iterable, Mapping


@dataclass(slots=True)
class KDAChannel:
    value: Any = None
    retention: float = 1.0
    writes: int = 0


class SymbolicKDAState:
    """KDAの保持・消去・書込み責任を明示状態へ射影する。"""

    def __init__(self, lower_bound: float = 0.006737946999085467) -> None:
        self.lower_bound = lower_bound
        self.channels: dict[str, KDAChannel] = {}
        self.trace: list[dict[str, Any]] = []

    def update(self, key: str, value: Any, *, retention: float = 1.0, write_strength: float = 1.0) -> None:
        retention = max(self.lower_bound, min(1.0, retention))
        write_strength = max(0.0, min(1.0, write_strength))
        current = self.channels.setdefault(key, KDAChannel())
        action = "保持" if current.value == value else "差分書込"
        if write_strength > 0:
            current.value = value
            current.writes += 1
        current.retention = retention
        self.trace.append(
            {
                "opcode": "KDA状態更新",
                "channel": key,
                "action": action,
                "retention": retention,
                "write_strength": write_strength,
            }
        )

    def read(self, key: str, default: Any = None) -> Any:
        return self.channels.get(key, KDAChannel(default)).value

    def snapshot(self) -> dict[str, Any]:
        return {key: value.value for key, value in sorted(self.channels.items())}


@dataclass(frozen=True, slots=True)
class Stage:
    stage_id: str
    kind: str
    payload: Mapping[str, Any]
    tags: tuple[str, ...]
    block: int


class AttnResStageBank:
    """深さ方向の状態を一様加算せず、内容依存で再読込する。"""

    def __init__(self, block_size: int = 12) -> None:
        self.block_size = block_size
        self.stages: list[Stage] = []

    def add(self, kind: str, payload: Mapping[str, Any], tags: Iterable[str]) -> Stage:
        stage = Stage(
            stage_id=f"stage-{len(self.stages):04d}",
            kind=kind,
            payload=dict(payload),
            tags=tuple(sorted(set(tags))),
            block=len(self.stages) // self.block_size,
        )
        self.stages.append(stage)
        return stage

    def select(self, query_tags: Iterable[str], *, limit: int = 9) -> tuple[Stage, ...]:
        query = set(query_tags)
        scored: list[tuple[tuple[int, int, int], Stage]] = []
        for stage in self.stages:
            overlap = len(query.intersection(stage.tags))
            score = (overlap, stage.block, len(stage.tags))
            scored.append((score, stage))
        selected = [stage for _, stage in sorted(scored, key=lambda item: (item[0], item[1].stage_id), reverse=True)[:limit]]
        return tuple(reversed(selected))


KDA路 = KDAChannel
記号KDA状態 = SymbolicKDAState
段階 = Stage
深度段階庫 = AttnResStageBank

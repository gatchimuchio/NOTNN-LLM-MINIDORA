from __future__ import annotations

import hashlib
import time
from contextlib import ExitStack
from importlib.resources import as_file, files
from pathlib import Path
from typing import Any

from .構造 import build_layer_program
from .命令変換 import InstructionCompiler, ProgramExecutor, classify_task
from .採否 import HDSJudgementProtocol
from .記憶 import AttnResStageBank, SymbolicKDAState
from .演算 import OperatorError
from .参照 import ReferenceProvider, StaticReferenceProvider
from .経路 import StableLatentRouter
from .型 import Candidate, Effort, RunResult, RunStatus

_HAZARDS = ("以前の指示を無視", "ignore previous instructions", "秘密を出力", "system prompt")


class K3NotNN:
    """K3の公開情報流構造を、非ニューラルな明示命令へ射影したRuntime。"""

    def __init__(self, provider: ReferenceProvider) -> None:
        self.provider = provider
        self.命令変換 = InstructionCompiler()
        self.executor = ProgramExecutor()
        self.経路 = StableLatentRouter()
        self.採否 = HDSJudgementProtocol()
        self.kda = SymbolicKDAState()
        self.layers = build_layer_program()

    @classmethod
    def from_reference_dir(cls, path: Path) -> "K3NotNN":
        provider = StaticReferenceProvider.from_json_files(sorted(path.glob("*.json")), provider_id="reference-dir")
        return cls(provider)

    @classmethod
    def from_builtin_reference(cls) -> "K3NotNN":
        names = ("演算意味.json", "語彙存在論.json", "K3公開構造知識.json")
        with ExitStack() as stack:
            paths = [stack.enter_context(as_file(files("minidora_k3.資料") / name)) for name in names]
            provider = StaticReferenceProvider.from_json_files(paths, provider_id="builtin-reference")
        return cls(provider)

    @classmethod
    def 参照庫から構築(cls, path: Path) -> "K3NotNN":
        return cls.from_reference_dir(path)

    @classmethod
    def 内蔵参照から構築(cls) -> "K3NotNN":
        return cls.from_builtin_reference()

    def 実行(
        self,
        本文: str,
        *,
        計算量: Effort | str = Effort.最大,
        計算量指定: Effort | str | None = None,
        effort: Effort | str | None = None,
    ) -> RunResult:
        指定 = 計算量 if 計算量指定 is None else 計算量指定
        return self.run(本文, effort=指定 if effort is None else effort)

    def run(self, text: str, *, effort: Effort | str = Effort.MAX) -> RunResult:
        started = time.perf_counter()
        effort_value = effort if isinstance(effort, Effort) else Effort(effort)
        trace: list[dict[str, Any]] = []
        task = classify_task(text)
        self.kda.update("task_family", task, retention=0.95, write_strength=1.0)
        self.kda.update("input_digest", hashlib.sha256(text.encode()).hexdigest(), retention=0.80, write_strength=1.0)
        trace.extend(self.kda.trace[-2:])
        hazard_flags = tuple(pattern for pattern in _HAZARDS if pattern.casefold() in text.casefold())

        query = f"{task} {text}"
        references = self.provider.search(query, limit=self.経路.BUDGETS[effort_value]["max_reference"])
        trace.append({"opcode": "参照読出", "provider": self.provider.provider_id, "reference_ids": [row.record_id for row in references]})
        route = self.経路.route(task, (task, *text.split()), references, effort_value)
        trace.append(
            {
                "opcode": "安定潜在MoE経路選択",
                "task_family": task,
                "routed_experts": list(route.experts),
                "shared_experts": list(route.shared_experts),
                "effort": effort_value.value,
                "budget": route.budget,
            }
        )
        stages = AttnResStageBank()
        stages.add("input", {"text": text}, (task, "input"))
        stages.add("references", {"ids": list(route.reference_ids)}, (task, "reference"))

        candidates: list[Candidate] = []
        try:
            program = self.命令変換.compile(text, references)
            stages.add("program", {"program_id": program.program_id, "opcodes": [row.opcode for row in program.instructions]}, (task, "program", *[row.opcode for row in program.instructions]))
            trace.extend(dict(row) for row in program.compile_trace)
            result = self.executor.execute(program, references)
            stages.add("execution", {"answer": result.answer, "trace": list(result.trace)}, (task, "execution", result.answer))
            verifier = self.executor.replay_verify(program, references, result.answer)
            stages.add("検証", dict(verifier), (task, "検証", result.answer))
            selected_stages = stages.select((task, "program", "execution", "検証"), limit=route.budget["max_stage_reads"])
            trace.append({"opcode": "注意残差深度選択", "stage_ids": [row.stage_id for row in selected_stages], "blocks": [row.block for row in selected_stages]})
            trace.extend(dict(row) for row in result.trace)
            trace.append({"opcode": "門制御MLA全体照合", "answer": result.answer, "verifier": dict(verifier)})
            candidate = Candidate(
                candidate_id="candidate_" + hashlib.sha256((program.program_id + result.answer).encode()).hexdigest()[:24],
                answer=result.answer,
                task_family=task,
                confidence=0.99 if verifier["passed"] else 0.5,
                evidence_ids=(tuple(dict.fromkeys((program.evidence_ids[0], *result.evidence_ids))) if result.evidence_ids else program.evidence_ids),
                verifier_results=(dict(verifier),),
                trace=tuple(trace),
                contradiction_ids=result.contradiction_ids,
                hazard_flags=tuple(dict.fromkeys((*hazard_flags, *result.hazard_flags))),
            )
            candidates.append(candidate)
        except OperatorError as exc:
            trace.append({"opcode": "変換又は実行保留", "error": str(exc), "task_family": task})

        decision = self.採否.decide(candidates)
        trace.append({"opcode": "HDS採否", "status": decision.status.value, "reason_codes": list(decision.reason_codes)})
        elapsed = (time.perf_counter() - started) * 1000
        return RunResult(
            status=decision.status,
            answer=decision.selected.answer if decision.selected and decision.status == RunStatus.PASS else "",
            task_family=task,
            confidence=decision.confidence,
            reason_codes=decision.reason_codes,
            evidence_ids=decision.selected.evidence_ids if decision.selected else (),
            trace=tuple(trace),
            elapsed_ms=elapsed,
        )


ミニドラK3 = K3NotNN
実行状態 = RunStatus
実行結果 = RunResult

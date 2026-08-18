"""英字資産との薄い互換層。内部正本は日本語命令・日本語履歴。"""
from .構造 import LayerInstruction, ExpertDescriptor
from .挙動変換 import BehaviorProbe, BehaviorInstructionTemplate
from .命令変換 import InstructionCompiler, ProgramExecutor
from .採否 import HDSJudgementProtocol
from .記憶 import SymbolicKDAState, AttnResStageBank
from .参照 import ReferenceProvider, StaticReferenceProvider, CompositeProvider, JSONHTTPProvider
from .経路 import StableLatentRouter
from .実行系 import K3NotNN
from .型 import RunStatus, Effort, ReferenceRecord, Instruction, Program, Candidate, Decision, RunResult

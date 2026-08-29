from __future__ import annotations

from dataclasses import dataclass
from typing import Mapping, Sequence

from .hds_choice_runtime import (
    HDS選択実行結果,
    _choices,
    _一括コンパイル,
    _参照作用差分群,
    _専門作用起動数,
    _正式模型候補群,
    _独立コンパイル入口,
    _suspend,
)
from .hds_compiler_records_v1_3 import HDS作用差分構造
from .hds_ir import HDSIR, 値状態
from .hds_model_projection import (
    HDS内部言語状態,
    HDS能力作用構造射影,
    _対象言語体系,
    _文脈条件,
)
from .hds_runtime_projection import HDSKData射影, HDSK候補射影, HDSK質問射影
from .hds判断参照境界 import HDS判断Data整列
from .k3_functional import K3相当能力核
from .模型 import MINIDORA模型核, 成立候補, 模型結果
from .能力状態差循環 import MINIDORA能力状態差模型核, 標準能力模型核
from .参照 import 参照記録
from .hds判断主体 import MINIDORA出力, MINIDORA出力化


_BLOCKING = {値状態.未確定, 値状態.未観測, 値状態.矛盾, 値状態.留保}


@dataclass(frozen=True, slots=True)
class MINIDORA候補提案結果:
    """計算主体C_execがJ_hdsへ返す候補提案。

    `PROPOSE` は採用ではない。候補生成系にはCOMMIT権限を与えない。
    """

    模型結果: 模型結果
    状態: str
    回答ラベル: str | None
    MINIDORA出力: MINIDORA出力
    理由: tuple[str, ...]


def MINIDORA候補提案評価(
    question_ir: HDSIR,
    candidate_irs: Mapping[str, HDSIR],
    data_irs: Sequence[HDSIR],
    *,
    模型核: MINIDORA模型核 | None = None,
    参照識別子: Sequence[str] | None = None,
    作用差分構造群: Sequence[HDS作用差分構造] = (),
) -> MINIDORA候補提案結果:
    """HDS判断を行わず、MINIDORA能力核の候補提案だけを形成する。"""

    core = 模型核 or 標準能力模型核()
    target = _対象言語体系(question_ir)
    question = HDS内部言語状態(question_ir, 識別子="question", 言語体系=target)
    candidate_internal = {
        str(label): HDS内部言語状態(
            ir,
            識別子="candidate:" + str(label),
            言語体系=target,
        )
        for label, ir in sorted(candidate_irs.items())
    }
    candidates = tuple(成立候補(label, state) for label, state in candidate_internal.items())
    ids = tuple(参照識別子 or tuple(f"reference:{i}" for i in range(len(data_irs))))
    if len(ids) != len(data_irs):
        raise ValueError("参照識別子はData IRと同数である必要がある")
    ref_internal = tuple(
        HDS内部言語状態(
            ir,
            識別子=ids[i],
            言語体系=target,
            証拠境界=True,
        )
        for i, ir in enumerate(data_irs)
    )

    ability_structures = tuple(HDS能力作用構造射影(item) for item in 作用差分構造群)
    if isinstance(core, MINIDORA能力状態差模型核):
        result = core.評価言語状態(
            question,
            candidates,
            条件=_文脈条件(question_ir),
            参照状態=ref_internal,
            作用構造群=ability_structures,
        )
    else:
        result = core.評価言語状態(
            question,
            candidates,
            条件=_文脈条件(question_ir),
            参照状態=ref_internal,
        )

    model_output = MINIDORA出力化(result)
    answer = model_output.候補ID if model_output.状態 == "OUTPUT" else None
    state = "PROPOSE" if answer is not None else "SUSPEND"
    reasons: list[str] = [
        "MINIDORA_CANDIDATE_PROPOSAL_BOUNDARY",
        "CANDIDATE_GENERATION_HAS_NO_COMMIT_AUTHORITY",
        "CAPABILITY_PROJECTION_V1",
        "CAPABILITY_STATE_DELTA_V1",
    ]
    if answer is None:
        reasons.append("MINIDORA_OUTPUT_ABSENT")
    if ability_structures:
        reasons.append("HDS_ACTION_DELTA_ATTACHED")
    if any(
        contribution.関係名.startswith("候補共同参照:状態差連結")
        for row in result.候補差
        for contribution in row.寄与
    ):
        reasons.append("HDS_ACTION_DELTA_CONSUMED")
    if result.統計.checkpoint再活性数:
        reasons.append("STATE_DELTA_REACTION")
    if result.統計.候補横断更新数:
        reasons.append("STATE_DELTA_CROSS_UPDATE")

    return MINIDORA候補提案結果(
        result,
        state,
        answer,
        model_output,
        tuple(dict.fromkeys(reasons)),
    )


def HDS候補提案実行(
    question_ir: HDSIR,
    references: tuple[参照記録, ...],
    *,
    コンパイル,
    基礎能力核: K3相当能力核,
    最大コンパイル並列: int = 4,
    模型核: MINIDORA模型核 | None = None,
) -> HDS選択実行結果:
    """既存HDS Compiler/能力核をworkerとして使い、候補をPROPOSEまで形成する。"""

    choices = _choices(question_ir)
    if len(choices) < 2:
        return _suspend("HDS_CHOICE_SET_INCOMPLETE")
    labels = [label for label, _, _ in choices]
    if len(set(labels)) != len(labels):
        return _suspend("HDS_CHOICE_LABEL_DUPLICATE")
    if any(state in _BLOCKING for _, _, state in choices):
        return _suspend("HDS_CHOICE_UNRESOLVED")
    if any(residual.種別 == "semantic_loss" for residual in question_ir.残差):
        return _suspend("HDS_QUESTION_SEMANTIC_LOSS")

    compile_isolated, parallel_safe = _独立コンパイル入口(コンパイル)
    worker_count = (
        min(max(1, int(最大コンパイル並列)), max(1, len(choices), len(references)))
        if parallel_safe
        else 1
    )

    choice_payloads = _一括コンパイル(
        compile_isolated,
        [content for _, content, _ in choices],
        parallel=parallel_safe,
        max_workers=worker_count,
    )
    candidate_irs: dict[str, HDSIR] = {}
    for (label, _, _), compiled in zip(choices, choice_payloads):
        if isinstance(compiled, Exception):
            return _suspend(
                "HDS_CHOICE_COMPILE_FAILED",
                candidate_count=len(candidate_irs),
                parallel=parallel_safe,
                workers=worker_count,
            )
        if any(residual.種別 == "semantic_loss" for residual in compiled.残差):
            return _suspend(
                "HDS_CHOICE_SEMANTIC_LOSS",
                candidate_count=len(candidate_irs) + 1,
                parallel=parallel_safe,
                workers=worker_count,
            )
        candidate_irs[label] = compiled

    k_question_ir = HDSK質問射影(question_ir)
    if any(residual.種別 == "semantic_loss" for residual in k_question_ir.残差):
        return _suspend(
            "HDS_K_QUESTION_SEMANTIC_LOSS",
            candidate_count=len(candidate_irs),
            parallel=parallel_safe,
            workers=worker_count,
        )

    k_candidate_irs = {label: HDSK候補射影(candidate_ir) for label, candidate_ir in candidate_irs.items()}
    formal_candidate_irs = _正式模型候補群(k_question_ir, candidate_irs, k_candidate_irs)

    data_payloads = _一括コンパイル(
        compile_isolated,
        [record.内容 for record in references],
        parallel=parallel_safe,
        max_workers=worker_count,
    )
    data_bundle = HDS判断Data整列(references, data_payloads, HDSKData射影)
    data_irs = list(data_bundle.IR群)
    data_compiled = len(data_bundle.IR群)
    data_failed = data_bundle.失敗数

    action_structures, action_failed = _参照作用差分群(
        コンパイル,
        data_bundle.成功記録群,
        parallel=parallel_safe,
        max_workers=worker_count,
    )
    attached_model_core = 模型核 or getattr(基礎能力核, "_minidora_model_core", None)
    proposal = MINIDORA候補提案評価(
        k_question_ir,
        formal_candidate_irs,
        tuple(data_irs),
        模型核=attached_model_core,
        参照識別子=data_bundle.出典ID群,
        作用差分構造群=action_structures,
    )
    choice_map = {label: content for label, content, _ in choices}
    content = choice_map.get(proposal.回答ラベル) if proposal.回答ラベル is not None else None
    reasons = list(proposal.理由)
    reasons.append("FORMAL_MODEL_CORE_PROPOSAL_ONLY")
    if data_failed:
        reasons.append(f"DATA_COMPILE_PARTIAL:{data_failed}")
    if action_failed:
        reasons.append(f"ACTION_DELTA_COMPILE_PARTIAL:{action_failed}")
    stats = proposal.模型結果.統計
    specialist_count = _専門作用起動数(proposal.模型結果)

    return HDS選択実行結果(
        proposal.状態,
        proposal.回答ラベル,
        content,
        tuple(dict.fromkeys(reasons)),
        None,
        len(candidate_irs),
        data_compiled,
        data_failed,
        0,
        0,
        0,
        parallel_safe,
        worker_count,
        0,
        0,
        0,
        0,
        len(proposal.模型結果.checkpoint),
        int(stats.checkpoint再活性数),
        int(stats.大域再照合数),
        int(stats.候補横断更新数),
        specialist_count,
        int(proposal.状態 != "PROPOSE"),
        0,
        0,
        0,
        0,
        0,
        0,
        proposal.模型結果,
    )


__all__ = [
    "MINIDORA候補提案結果",
    "MINIDORA候補提案評価",
    "HDS候補提案実行",
]

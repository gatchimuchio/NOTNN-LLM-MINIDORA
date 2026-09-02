from __future__ import annotations

from collections.abc import Callable, Sequence
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass

from .choice_intent import HDS選択意図判定
from .hds_adapter import HDS独立コンパイル
from .hds_choice_hypothesis import HDS候補代入仮説群
from .hds_data_k import HDSIR知識Adapter, HDS証拠状態複製
from .hds_direct_relation_verifier import HDS直接関係検証
from .hds_ir import HDSIR, 値状態
from .hds_model_projection import HDSMINIDORA模型評価
from .hds判断参照境界 import HDS判断Data整列
from .hds_runtime_projection import (
    HDSKData射影, HDSK候補代入可能, HDSK候補射影, HDSK質問射影, HDS模型候補代入可能,
)
from .hds作業状態 import (
    HDS一時証拠統合,
    HDS作業状態構築,
    HDS候補共同状態更新,
    HDS寄与Gate再照合,
)
from .hds局所再照合 import HDS局所Window候補
from .k3_functional import K3相当能力核, SemanticFrame
from .k3_hds_native import HDSK3結果, HDSIRネイティブAdapter
from .参照 import 参照記録
from .模型 import MINIDORA模型核, 模型結果


HDSコンパイル関数 = Callable[[str], HDSIR]
_BLOCKING = {値状態.未確定, 値状態.未観測, 値状態.矛盾, 値状態.留保}
_QUERY_PROVENANCE_KEYS = {"hds_query_choice", "hds_query_kind"}


@dataclass(frozen=True, slots=True)
class HDS選択実行結果:
    状態: str
    回答ラベル: str | None
    回答内容: str | None
    理由: tuple[str, ...]
    K3結果: HDSK3結果 | None
    候補コンパイル数: int
    Dataコンパイル数: int
    Dataコンパイル失敗数: int
    K追加事実数: int
    K証拠事実数: int
    K証拠阻害事実数: int
    コンパイル並列: bool = False
    コンパイル最大並列: int = 1
    作業関係生成数: int = 0
    作業関係再利用数: int = 0
    作業関係K昇格数: int = 0
    作業関係再検証後破棄数: int = 0
    checkpoint数: int = 0
    checkpoint再活性数: int = 0
    大域再照合数: int = 0
    候補横断更新数: int = 0
    専門作用起動数: int = 0
    遍歴後SUSPEND数: int = 0
    一時証拠数: int = 0
    局所Window数: int = 0
    局所Windowコンパイル数: int = 0
    局所Windowコンパイル失敗数: int = 0
    局所Window追加事実数: int = 0
    局所再照合数: int = 0
    MINIDORA模型結果: 模型結果 | None = None


def HDS選択問題(ir: HDSIR) -> bool:
    if ir.手順 is not None:
        return False
    return sum(1 for coord in ir.座標 if coord.座標ID.startswith("choice:")) >= 2


def _choices(ir: HDSIR) -> tuple[tuple[str, str, 値状態], ...]:
    rows: list[tuple[str, str, 値状態]] = []
    for coord in ir.座標:
        if not coord.座標ID.startswith("choice:"):
            continue
        rows.append((coord.座標ID.split(":", 1)[1], str(coord.内容), coord.値状態))
    return tuple(sorted(rows, key=lambda item: item[0]))


def _suspend(
    reason: str,
    *,
    candidate_count: int = 0,
    data_fail: int = 0,
    parallel: bool = False,
    workers: int = 1,
) -> HDS選択実行結果:
    return HDS選択実行結果(
        "SUSPEND", None, None, (reason,), None,
        candidate_count, 0, data_fail, 0, 0, 0,
        parallel, workers,
    )


def _コンパイラ実体(compile_fn: HDSコンパイル関数):
    """bound methodから公開HDS Compiler実体を取り出す。推測で生成しない。"""
    owner = getattr(compile_fn, "__self__", None)
    if owner is None:
        return None
    compiler = getattr(owner, "HDSコンパイラ", None)
    if compiler is not None:
        return compiler
    if callable(getattr(owner, "詳細コンパイル", None)):
        return owner
    return None


def _独立コンパイル入口(compile_fn: HDSコンパイル関数) -> tuple[HDSコンパイル関数, bool]:
    owner = getattr(compile_fn, "__self__", None)
    compiler = getattr(owner, "HDSコンパイラ", None)
    if compiler is None:
        return compile_fn, bool(getattr(compile_fn, "並列安全", False))
    return (
        lambda text: HDS独立コンパイル(compiler, text),
        bool(getattr(compiler, "並列安全", False)),
    )


def _一括コンパイル(
    compile_fn,
    texts: Sequence[str],
    *,
    parallel: bool,
    max_workers: int,
) -> tuple[object | Exception, ...]:
    if not texts:
        return ()
    if not parallel or len(texts) <= 1 or max_workers <= 1:
        out: list[object | Exception] = []
        for text in texts:
            try:
                out.append(compile_fn(text))
            except Exception as exc:
                out.append(exc)
        return tuple(out)

    workers = min(max(1, int(max_workers)), len(texts))
    with ThreadPoolExecutor(max_workers=workers, thread_name_prefix="minidora-hds") as executor:
        futures = [executor.submit(compile_fn, text) for text in texts]
        out: list[object | Exception] = []
        for future in futures:
            try:
                out.append(future.result())
            except Exception as exc:
                out.append(exc)
        return tuple(out)


def _参照作用差分群(
    compile_fn: HDSコンパイル関数,
    references: Sequence[参照記録],
    *,
    parallel: bool,
    max_workers: int,
) -> tuple[tuple[object, ...], int]:
    """通常Data意味コンパイル成功済みの参照だけを詳細コンパイルし、作用差分構造を回収する。"""
    compiler = _コンパイラ実体(compile_fn)
    detailed = getattr(compiler, "詳細コンパイル", None)
    if not callable(detailed) or not references:
        return (), 0

    payloads = _一括コンパイル(
        lambda text: detailed(text).作用差分構造,
        [record.内容 for record in references],
        parallel=parallel,
        max_workers=max_workers,
    )
    structures: list[object] = []
    failed = 0
    for payload in payloads:
        if isinstance(payload, Exception):
            failed += 1
            continue
        if getattr(payload, "状態差", ()) or getattr(payload, "後続利用", ()):
            structures.append(payload)
    return tuple(structures), failed


def _専門作用起動数(result: 模型結果) -> int:
    """Compiler作用差分を実際に消費した証拠件数だけを数える。"""
    total = 0
    for row in result.候補差:
        for contribution in row.寄与:
            if contribution.関係名.startswith("候補共同参照:状態差連結"):
                total += len(tuple(contribution.根拠))
    return total


def _参照provenance(record: 参照記録) -> tuple[str, ...]:
    markers: list[str] = []
    for key, value in record.条件:
        k = str(key)
        if k not in _QUERY_PROVENANCE_KEYS:
            continue
        if k == "hds_query_choice":
            markers.append("query_choice:" + str(value))
        elif k == "hds_query_kind":
            markers.append("query_kind:" + str(value))
    return tuple((record.供給器, record.由来, record.識別子, *dict.fromkeys(markers)))


def _直接関係で再判定(
    judgment_ir: HDSIR,
    verification_candidate_irs: dict[str, HDSIR],
    working: K3相当能力核,
    k3: HDSK3結果,
) -> HDSK3結果:
    """旧v0.3 K3 helper診断だけに使う。正式回答を上書きしない。"""
    if HDS選択意図判定(judgment_ir.原文).種別 == "EXCEPTION":
        return k3
    direct, _diagnostics = HDS直接関係検証(working, verification_candidate_irs)
    if direct is None:
        return k3

    frame = SemanticFrame(
        kind="question",
        intent="knowledge_query",
        raw=judgment_ir.原文,
        predicate="HDS_choice_selection",
        args=(None,),
        tags=("HDS-IR", "choice", "directed_relation_verification"),
        language=getattr(judgment_ir, "入力言語", "en") or "en",
    )
    decision = working.J.decide(frame, (direct,))
    if decision.status != "APPROVE" or decision.selected_candidate is None:
        return k3

    selected = decision.selected_candidate.answer
    candidates = (direct, *tuple(candidate for candidate in k3.候補 if candidate.answer != selected))
    reasons = tuple((*decision.reason_codes, "DIRECTED_RELATION_VERIFIED"))
    return HDSK3結果(
        decision.status, selected, decision, candidates, len(set(direct.proof_fact_ids)), reasons,
        k3.努力水準, k3.探索深さ上限, k3.証拠上限, k3.候補診断,
    )


def _検証候補群(
    k_question_ir: HDSIR,
    full_candidates: dict[str, HDSIR],
    k_candidates: dict[str, HDSIR],
) -> dict[str, HDSIR]:
    substitutable = {
        label: k_candidates[label]
        for label, full_ir in full_candidates.items()
        if label in k_candidates and HDSK候補代入可能(full_ir)
    }
    substituted = HDS候補代入仮説群(k_question_ir, substitutable)
    return {label: substituted.get(label, candidate_ir) for label, candidate_ir in k_candidates.items()}


def _正式模型候補群(
    k_question_ir: HDSIR,
    full_candidates: dict[str, HDSIR],
    k_candidates: dict[str, HDSIR],
) -> dict[str, HDSIR]:
    """正式模型だけで使う質問型aware候補代入。旧helper経路へは流さない。"""
    substitutable = {
        label: k_candidates[label]
        for label, full_ir in full_candidates.items()
        if label in k_candidates and HDS模型候補代入可能(k_question_ir, full_ir)
    }
    substituted = HDS候補代入仮説群(k_question_ir, substitutable)
    return {label: substituted.get(label, candidate_ir) for label, candidate_ir in k_candidates.items()}


def _候補強度(result: HDSK3結果) -> tuple[int, int, float, int, float]:
    diagnostics = tuple(result.候補診断)
    if not diagnostics:
        return (0, 0, 0.0, 0, 0.0)
    ordered = sorted(diagnostics, key=lambda item: (-item.合計得点, item.候補))
    top = next((item for item in diagnostics if item.候補 == result.回答ラベル), ordered[0])
    second = max((item.合計得点 for item in diagnostics if item.候補 != top.候補), default=0.0)
    margin = top.合計得点 - second
    return (top.独立出典数, top.識別一致出典数, margin, top.根拠事実数, top.合計得点)


def _再作用結果選択(initial: HDSK3結果, rechecked: HDSK3結果) -> HDSK3結果:
    """旧helper内の診断比較。正式MINIDORA模型結果の採否には使わない。"""
    if "DIRECTED_RELATION_VERIFIED" in initial.理由:
        return initial
    if rechecked.状態 != "APPROVE" or rechecked.回答ラベル is None:
        return initial
    if initial.状態 != "APPROVE" or initial.回答ラベル is None:
        return rechecked
    if rechecked.回答ラベル == initial.回答ラベル:
        return rechecked
    if "DIRECTED_RELATION_VERIFIED" in rechecked.理由:
        return rechecked
    return rechecked if _候補強度(rechecked) > _候補強度(initial) else initial


def HDS選択推論実行(
    question_ir: HDSIR,
    references: tuple[参照記録, ...],
    *,
    コンパイル: HDSコンパイル関数,
    基礎能力核: K3相当能力核,
    努力: str | None = None,
    最大コンパイル並列: int = 4,
    作業再作用: bool = True,
    局所再照合: bool = True,
    最大局所Window数: int = 12,
    模型核: MINIDORA模型核 | None = None,
    正式模型評価: bool = False,
) -> HDS選択実行結果:
    """選択問題をR→HDS→MINIDORA C→HDS J、または旧互換経路で評価する。"""
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
    worker_count = min(max(1, int(最大コンパイル並列)), max(1, len(choices), len(references))) if parallel_safe else 1

    choice_payloads = _一括コンパイル(
        compile_isolated, [content for _, content, _ in choices], parallel=parallel_safe, max_workers=worker_count,
    )
    candidate_irs: dict[str, HDSIR] = {}
    for (label, _, _), compiled in zip(choices, choice_payloads):
        if isinstance(compiled, Exception):
            return _suspend("HDS_CHOICE_COMPILE_FAILED", candidate_count=len(candidate_irs), parallel=parallel_safe, workers=worker_count)
        if any(residual.種別 == "semantic_loss" for residual in compiled.残差):
            return _suspend("HDS_CHOICE_SEMANTIC_LOSS", candidate_count=len(candidate_irs) + 1, parallel=parallel_safe, workers=worker_count)
        candidate_irs[label] = compiled

    k_question_ir = HDSK質問射影(question_ir)
    if any(residual.種別 == "semantic_loss" for residual in k_question_ir.残差):
        return _suspend("HDS_K_QUESTION_SEMANTIC_LOSS", candidate_count=len(candidate_irs), parallel=parallel_safe, workers=worker_count)

    k_candidate_irs = {label: HDSK候補射影(candidate_ir) for label, candidate_ir in candidate_irs.items()}
    verification_candidate_irs = _検証候補群(k_question_ir, candidate_irs, k_candidate_irs)
    attached_model_core = 模型核 or getattr(基礎能力核, "_minidora_model_core", None)
    use_formal_model = bool(正式模型評価 or attached_model_core is not None)
    formal_candidate_irs = (
        _正式模型候補群(k_question_ir, candidate_irs, k_candidate_irs)
        if use_formal_model
        else verification_candidate_irs
    )

    data_payloads = _一括コンパイル(
        compile_isolated, [record.内容 for record in references], parallel=parallel_safe, max_workers=worker_count,
    )
    data_bundle = HDS判断Data整列(references, data_payloads, HDSKData射影)
    data_irs = list(data_bundle.IR群)
    data_compiled = len(data_bundle.IR群)
    data_failed = data_bundle.失敗数

    choice_map = {label: content for label, content, _ in choices}

    if use_formal_model:
        action_structures, action_failed = _参照作用差分群(
            コンパイル,
            data_bundle.成功記録群,
            parallel=parallel_safe,
            max_workers=worker_count,
        )
        formal = HDSMINIDORA模型評価(
            k_question_ir,
            formal_candidate_irs,
            tuple(data_irs),
            模型核=attached_model_core,
            参照識別子=data_bundle.出典ID群,
            参照信頼=data_bundle.信頼群,
            作用差分構造群=action_structures,
        )
        content = choice_map.get(formal.回答ラベル) if formal.回答ラベル is not None else None
        reasons = list(formal.理由)
        reasons.append("FORMAL_MODEL_CORE_WITH_HDS_J")
        if data_failed:
            reasons.append(f"DATA_COMPILE_PARTIAL:{data_failed}")
        if action_failed:
            reasons.append(f"ACTION_DELTA_COMPILE_PARTIAL:{action_failed}")
        stats = formal.模型結果.統計
        specialist_count = _専門作用起動数(formal.模型結果)
        return HDS選択実行結果(
            formal.状態, formal.回答ラベル, content, tuple(dict.fromkeys(reasons)), None,
            len(candidate_irs), data_compiled, data_failed, 0, 0, 0, parallel_safe, worker_count,
            0, 0, 0, 0,
            len(formal.模型結果.checkpoint),
            int(stats.checkpoint再活性数),
            int(stats.大域再照合数),
            int(stats.候補横断更新数),
            specialist_count,
            int(formal.状態 != "APPROVE"),
            0, 0, 0, 0, 0, 0,
            formal.模型結果,
        )

    working = 基礎能力核.clone()
    HDS証拠状態複製(基礎能力核, working)
    ingest = HDSIR知識Adapter(working)
    added = 0
    evidence = 0
    blocked = 0
    for record, compiled in zip(references, data_payloads):
        if isinstance(compiled, Exception):
            continue
        result = ingest.投入(HDSKData射影(compiled), provenance=_参照provenance(record), 信頼係数=record.信頼)
        added += result.追加事実数
        evidence += result.証拠事実数
        blocked += result.証拠阻害事実数

    作業 = HDS作業状態構築(working)
    initial = HDSIRネイティブAdapter(working).実行(k_question_ir, 候補IR=verification_candidate_irs, 努力=努力)
    initial = _直接関係で再判定(question_ir, verification_candidate_irs, working, initial)
    HDS候補共同状態更新(作業, initial.候補診断, 段階="CANDIDATE_INITIAL")

    temporary = HDS寄与Gate再照合(作業) if 作業再作用 else ()
    local_windows = ()
    if 局所再照合 and "DIRECTED_RELATION_VERIFIED" not in initial.理由:
        local_windows = HDS局所Window候補(question_ir, references, 上限=max(0, int(最大局所Window数)))

    local_compiled = 0
    local_failed = 0
    local_added = 0
    local_reconciliations = 0
    legacy_k3 = initial
    legacy_rechecked_selected = False
    legacy_rechecked_override = False

    if temporary or local_windows:
        rechecked_core = working.clone()
        HDS証拠状態複製(working, rechecked_core)
        changed = 0
        if temporary:
            changed += HDS一時証拠統合(rechecked_core, temporary)
        if local_windows:
            local_payloads = _一括コンパイル(
                compile_isolated, [row.内容 for row in local_windows], parallel=parallel_safe, max_workers=worker_count,
            )
            local_ingest = HDSIR知識Adapter(rechecked_core)
            for row, compiled in zip(local_windows, local_payloads):
                if isinstance(compiled, Exception):
                    local_failed += 1
                    continue
                result = local_ingest.投入(HDSKData射影(compiled), provenance=_参照provenance(row.参照), 信頼係数=row.参照.信頼)
                local_compiled += 1
                local_added += result.追加事実数
                changed += result.証拠事実数

        if changed > 0:
            作業.統計.checkpoint再活性数 += 1
            作業.統計.大域再照合数 += 1
            local_reconciliations = 1 if local_compiled > 0 else 0
            rechecked = HDSIRネイティブAdapter(rechecked_core).実行(k_question_ir, 候補IR=verification_candidate_irs, 努力=努力)
            rechecked = _直接関係で再判定(question_ir, verification_candidate_irs, rechecked_core, rechecked)
            HDS候補共同状態更新(作業, rechecked.候補診断, 段階="CANDIDATE_RECHECK")
            selected = _再作用結果選択(initial, rechecked)
            legacy_rechecked_selected = selected is rechecked
            legacy_rechecked_override = bool(
                legacy_rechecked_selected and initial.回答ラベル is not None and rechecked.回答ラベル is not None
                and initial.回答ラベル != rechecked.回答ラベル
            )
            if not legacy_rechecked_selected and rechecked.回答ラベル != initial.回答ラベル:
                作業.統計.作業関係再検証後破棄数 += len(temporary)
            legacy_k3 = selected

    if legacy_k3.状態 != "APPROVE":
        作業.統計.遍歴後SUSPEND数 = 1
    content = choice_map.get(legacy_k3.回答ラベル) if legacy_k3.回答ラベル is not None else None
    reasons = list(legacy_k3.理由)
    reasons.append("LEGACY_V03_SELECTION_PATH")
    if temporary:
        reasons.append("LEGACY_WORKING_RECHECK")
    if local_compiled:
        reasons.append("LEGACY_LOCAL_WINDOW_RECHECK")
    if legacy_rechecked_selected:
        reasons.append("LEGACY_RECHECK_SELECTED")
    if legacy_rechecked_override:
        reasons.append("LEGACY_RECHECK_OVERRIDE")
    if data_failed:
        reasons.append(f"DATA_COMPILE_PARTIAL:{data_failed}")
    if local_failed:
        reasons.append(f"LOCAL_WINDOW_COMPILE_PARTIAL:{local_failed}")

    stats = 作業.統計
    return HDS選択実行結果(
        legacy_k3.状態, legacy_k3.回答ラベル, content, tuple(dict.fromkeys(reasons)), legacy_k3,
        len(candidate_irs), data_compiled, data_failed, added, evidence, blocked, parallel_safe, worker_count,
        stats.作業関係生成数, stats.作業関係再利用数, stats.作業関係K昇格数, stats.作業関係再検証後破棄数,
        stats.checkpoint数, stats.checkpoint再活性数, stats.大域再照合数, stats.候補横断更新数,
        stats.専門作用起動数, stats.遍歴後SUSPEND数, stats.一時証拠数, len(local_windows), local_compiled,
        local_failed, local_added, local_reconciliations, None,
    )


__all__ = ["HDS選択実行結果", "HDS選択問題", "HDS選択推論実行"]

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass

from .hds_adapter import HDS独立コンパイル
from .hds_data_k import HDSIR知識Adapter, HDS証拠状態複製
from .hds_ir import HDSIR, 値状態
from .k3_functional import K3相当能力核
from .k3_hds_native import HDSK3結果, HDSIRネイティブAdapter
from .参照 import 参照記録


HDSコンパイル関数 = Callable[[str], HDSIR]
_BLOCKING = {値状態.未確定, 値状態.未観測, 値状態.矛盾, 値状態.留保}


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


def HDS選択問題(ir: HDSIR) -> bool:
    """Native choice reasoningへ入る構造IRか判定する。

    Compilerが明示的なLayer-0手順を返した場合は、その既存契約を最優先する。
    Native pathは「choice集合は確定したが手順を持たない」構造IRだけを補完する。
    """
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


def _suspend(reason: str, *, candidate_count: int = 0, data_fail: int = 0) -> HDS選択実行結果:
    return HDS選択実行結果(
        "SUSPEND", None, None, (reason,), None,
        candidate_count, 0, data_fail, 0, 0, 0,
    )


def _独立コンパイル入口(compile_fn: HDSコンパイル関数) -> HDSコンパイル関数:
    owner = getattr(compile_fn, "__self__", None)
    compiler = getattr(owner, "HDSコンパイラ", None)
    if compiler is None:
        return compile_fn
    return lambda text: HDS独立コンパイル(compiler, text)


def HDS選択推論実行(
    question_ir: HDSIR,
    references: tuple[参照記録, ...],
    *,
    コンパイル: HDSコンパイル関数,
    基礎能力核: K3相当能力核,
    努力: str | None = None,
) -> HDS選択実行結果:
    """HDS choice問題を `候補/Data→HDS-IR→K→J` の正規経路で実行する。"""
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

    compile_isolated = _独立コンパイル入口(コンパイル)
    candidate_irs: dict[str, HDSIR] = {}
    for label, content, _ in choices:
        try:
            candidate_ir = compile_isolated(content)
        except Exception:
            return _suspend("HDS_CHOICE_COMPILE_FAILED", candidate_count=len(candidate_irs))
        if any(residual.種別 == "semantic_loss" for residual in candidate_ir.残差):
            return _suspend("HDS_CHOICE_SEMANTIC_LOSS", candidate_count=len(candidate_irs) + 1)
        candidate_irs[label] = candidate_ir

    working = 基礎能力核.clone()
    HDS証拠状態複製(基礎能力核, working)
    ingest = HDSIR知識Adapter(working)
    data_compiled = 0
    data_failed = 0
    added = 0
    evidence = 0
    blocked = 0
    for record in references:
        try:
            data_ir = compile_isolated(record.内容)
        except Exception:
            data_failed += 1
            continue
        result = ingest.投入(
            data_ir,
            provenance=(record.供給器, record.由来, record.識別子),
        )
        data_compiled += 1
        added += result.追加事実数
        evidence += result.証拠事実数
        blocked += result.証拠阻害事実数

    k3 = HDSIRネイティブAdapter(working).実行(
        question_ir,
        候補IR=candidate_irs,
        努力=努力,
    )
    choice_map = {label: content for label, content, _ in choices}
    content = choice_map.get(k3.回答ラベル) if k3.回答ラベル is not None else None
    reasons = list(k3.理由)
    if data_failed:
        reasons.append(f"DATA_COMPILE_PARTIAL:{data_failed}")
    return HDS選択実行結果(
        k3.状態,
        k3.回答ラベル,
        content,
        tuple(reasons),
        k3,
        len(candidate_irs),
        data_compiled,
        data_failed,
        added,
        evidence,
        blocked,
    )


__all__ = ["HDS選択実行結果", "HDS選択問題", "HDS選択推論実行"]

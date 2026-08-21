from __future__ import annotations

from collections.abc import Callable, Sequence
from concurrent.futures import ThreadPoolExecutor
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
    コンパイル並列: bool = False
    コンパイル最大並列: int = 1


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
    compile_fn: HDSコンパイル関数,
    texts: Sequence[str],
    *,
    parallel: bool,
    max_workers: int,
) -> tuple[HDSIR | Exception, ...]:
    if not texts:
        return ()
    if not parallel or len(texts) <= 1 or max_workers <= 1:
        out: list[HDSIR | Exception] = []
        for text in texts:
            try:
                out.append(compile_fn(text))
            except Exception as exc:
                out.append(exc)
        return tuple(out)

    workers = min(max(1, int(max_workers)), len(texts))
    with ThreadPoolExecutor(max_workers=workers, thread_name_prefix="minidora-hds") as executor:
        futures = [executor.submit(compile_fn, text) for text in texts]
        out: list[HDSIR | Exception] = []
        # 完了順ではなく入力順で回収し、choice label/Data順の決定性を維持する。
        for future in futures:
            try:
                out.append(future.result())
            except Exception as exc:
                out.append(exc)
        return tuple(out)


def HDS選択推論実行(
    question_ir: HDSIR,
    references: tuple[参照記録, ...],
    *,
    コンパイル: HDSコンパイル関数,
    基礎能力核: K3相当能力核,
    努力: str | None = None,
    最大コンパイル並列: int = 4,
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

    compile_isolated, parallel_safe = _独立コンパイル入口(コンパイル)
    worker_count = min(max(1, int(最大コンパイル並列)), max(1, len(choices), len(references))) if parallel_safe else 1

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

    working = 基礎能力核.clone()
    HDS証拠状態複製(基礎能力核, working)
    ingest = HDSIR知識Adapter(working)
    data_compiled = 0
    data_failed = 0
    added = 0
    evidence = 0
    blocked = 0

    data_payloads = _一括コンパイル(
        compile_isolated,
        [record.内容 for record in references],
        parallel=parallel_safe,
        max_workers=worker_count,
    )
    for record, compiled in zip(references, data_payloads):
        if isinstance(compiled, Exception):
            data_failed += 1
            continue
        result = ingest.投入(
            compiled,
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
        parallel_safe,
        worker_count,
    )


__all__ = ["HDS選択実行結果", "HDS選択問題", "HDS選択推論実行"]

from __future__ import annotations

from collections import Counter
from collections.abc import Callable, Sequence
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass

from .hds_adapter import HDS独立コンパイル
from .hds_data_k import HDSIR知識Adapter, HDS証拠状態複製
from .hds_ir import HDSIR, HDS実行核, HDS座標, 値状態
from .k3_functional import K3相当能力核
from .k3_hds_native import HDSK3結果, HDSIRネイティブAdapter
from .参照 import 参照記録


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
        for future in futures:
            try:
                out.append(future.result())
            except Exception as exc:
                out.append(exc)
        return tuple(out)


def _参照候補群(record: 参照記録) -> tuple[str, ...]:
    return tuple(dict.fromkeys(
        str(value)
        for key, value in record.条件
        if str(key) == "hds_query_choice" and str(value)
    ))


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


def _検索経路証拠(
    question_ir: HDSIR,
    choices: tuple[tuple[str, str, 値状態], ...],
    references: tuple[参照記録, ...],
) -> tuple[tuple[参照記録, HDSIR], ...]:
    """一候補だけのqueryで得た独立文書が複数ある時だけ、弱い検索経路証拠を作る。

    Data本文の真偽を捏造するものではない。検索queryと取得結果の対応を、推定・低信頼の
    HDS文脈として保持する。複数候補queryで同じ文書が取得された場合は固有支持から除外する。
    """
    choice_map = {label: content for label, content, _ in choices}
    exclusive: list[tuple[str, 参照記録]] = []
    for record in references:
        labels = _参照候補群(record)
        if len(labels) != 1 or labels[0] not in choice_map:
            continue
        exclusive.append((labels[0], record))

    counts = Counter(label for label, _ in exclusive)
    if not counts:
        return ()
    ranking = counts.most_common()
    top_label, top_count = ranking[0]
    second_count = ranking[1][1] if len(ranking) > 1 else 0
    # 単発hitや同数hitは採用しない。検索分岐に実差がある場合だけ弱い補助証拠へ昇格。
    if top_count < 2 or top_count <= second_count:
        return ()

    focus = " ".join(str(question_ir.正規化文 or question_ir.原文).split())[:1200]
    candidate = choice_map[top_label]
    out: list[tuple[参照記録, HDSIR]] = []
    for label, record in exclusive:
        if label != top_label:
            continue
        ir = HDSIR(
            原文=f"retrieval-route:{label}",
            正規化文=f"retrieval-route:{label}",
            認知世界ID="hds:r-query-route",
            座標=(
                HDS座標("q", "対象.検索焦点", focus, 値状態.推定, 由来="HDS参照検索経路"),
                HDS座標("c", "文脈.検索候補", candidate, 値状態.推定, 由来="HDS参照検索経路"),
            ),
            関係=(),
            残差=(),
            意味作用履歴=(),
            実行核=HDS実行核(),
            初期状態={},
            参照必須=False,
            種別="retrieval_route_evidence",
            閉包状態="PROVISIONAL",
            入力言語=question_ir.入力言語,
        )
        out.append((record, ir))
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
            return _suspend("HDS_CHOICE_COMPILE_FAILED", candidate_count=len(candidate_irs), parallel=parallel_safe, workers=worker_count)
        if any(residual.種別 == "semantic_loss" for residual in compiled.残差):
            return _suspend("HDS_CHOICE_SEMANTIC_LOSS", candidate_count=len(candidate_irs) + 1, parallel=parallel_safe, workers=worker_count)
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
            provenance=_参照provenance(record),
            信頼係数=record.信頼,
        )
        data_compiled += 1
        added += result.追加事実数
        evidence += result.証拠事実数
        blocked += result.証拠阻害事実数

    # Rの候補別検索分岐は、同一sourceへ低信頼で重ねる。本文Factと二重source加点されない。
    for record, route_ir in _検索経路証拠(question_ir, choices, references):
        route = ingest.投入(
            route_ir,
            provenance=_参照provenance(record),
            信頼係数=min(0.18, max(0.0, float(record.信頼)) * 0.18),
        )
        added += route.追加事実数
        evidence += route.証拠事実数
        blocked += route.証拠阻害事実数

    k3 = HDSIRネイティブAdapter(working).実行(question_ir, 候補IR=candidate_irs, 努力=努力)
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

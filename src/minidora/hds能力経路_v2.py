from __future__ import annotations

from dataclasses import replace
import unicodedata
from typing import Iterable

from .hds_choice_runtime import HDS選択実行結果
from .hds_ir import HDSIR
from .hds_reference import (
    HDS参照予算選択,
    HDS参照検索,
    _候補被覆,
    _query_pools,
    _round_robin,
    _役割語群,
    _縮退仕様,
    _記録統合,
)
from .hds候補提案runtime import HDS候補提案実行
from .hds局所再照合 import HDS局所Window候補
from .k3_functional import K3相当能力核
from .模型 import MINIDORA模型核, 模型結果
from .能力状態差循環 import MINIDORA能力状態差模型核, 標準能力模型核
from .参照 import 参照供給器, 参照記録


def _正規化(text: object) -> str:
    return " ".join(unicodedata.normalize("NFKC", str(text)).split()).strip()


def _候補ラベル群(record: 参照記録) -> frozenset[str]:
    return frozenset(
        str(value)
        for key, value in record.条件
        if str(key) == "hds_query_choice" and str(value)
    )


def HDS候補被覆優先統合(
    primary: Iterable[参照記録],
    extra: Iterable[参照記録],
    expected_labels: Iterable[str],
    limit: int,
) -> tuple[参照記録, ...]:
    """候補別queryで観測できたsourceを対称に残してから、残枠へ通常順を戻す。

    `hds_query_choice` は検索経路情報であり、候補真偽の票としては使わない。
    同一sourceは1件へ統合し、query provenanceだけを併合する。
    """

    total_limit = max(0, int(limit))
    if total_limit <= 0:
        return ()

    combined: list[参照記録] = []
    index_by_id: dict[str, int] = {}
    for record in (*tuple(primary), *tuple(extra)):
        source_id = str(record.識別子)
        existing = index_by_id.get(source_id)
        if existing is not None:
            combined[existing] = _記録統合(combined[existing], record)
            continue
        index_by_id[source_id] = len(combined)
        combined.append(record)

    selected: list[参照記録] = []
    selected_ids: set[str] = set()
    for label in sorted({str(item) for item in expected_labels if str(item)}):
        if any(label in _候補ラベル群(record) for record in selected):
            continue
        candidate = next(
            (
                record
                for record in combined
                if str(record.識別子) not in selected_ids and label in _候補ラベル群(record)
            ),
            None,
        )
        if candidate is None:
            continue
        selected.append(candidate)
        selected_ids.add(str(candidate.識別子))
        if len(selected) >= total_limit:
            return tuple(selected)

    for record in combined:
        source_id = str(record.識別子)
        if source_id in selected_ids:
            continue
        selected.append(record)
        selected_ids.add(source_id)
        if len(selected) >= total_limit:
            break
    return tuple(selected)


def HDS参照検索V2(
    provider: 参照供給器,
    ir: HDSIR,
    *,
    上限: int | None = None,
    一問合せ上限: int | None = None,
    最大問合せ並列: int | None = None,
    最大候補補完回数: int = 1,
) -> tuple[参照記録, ...]:
    """一回のREFERENCE作用内で候補被覆不足だけを追加観測するR閉包。

    既存Rのprimary/fallback規則は保持し、その出力に候補別query被覆が不足した場合だけ、
    未被覆候補の縮退queryを追加する。generic検索量を無条件には増やさない。
    """

    budget = HDS参照予算選択(ir)
    total_limit = budget.取得上限 if 上限 is None else max(0, int(上限))
    per_query = budget.一問合せ上限 if 一問合せ上限 is None else max(1, int(一問合せ上限))
    parallel = budget.最大問合せ並列 if 最大問合せ並列 is None else max(1, int(最大問合せ並列))
    if total_limit <= 0:
        return ()

    references = HDS参照検索(
        provider,
        ir,
        上限=total_limit,
        一問合せ上限=per_query,
        最大問合せ並列=parallel,
    )
    _, choices = _役割語群(ir)
    expected = {label for label, _ in choices}
    if not expected:
        return references

    for _ in range(max(0, int(最大候補補完回数))):
        coverage = set(_候補被覆(references))
        missing = expected - coverage
        if not missing:
            break
        fallback_specs = tuple(
            spec
            for spec in _縮退仕様(ir)
            if spec.候補 is not None and spec.候補 in missing
        )
        if not fallback_specs:
            break
        extra = _round_robin(
            _query_pools(provider, fallback_specs, per_query, max_parallel=parallel),
            total_limit,
        )
        if not extra:
            break
        merged = HDS候補被覆優先統合(references, extra, expected, total_limit)
        before = tuple((record.識別子, record.条件) for record in references)
        after = tuple((record.識別子, record.条件) for record in merged)
        references = merged
        if after == before:
            break
    return references


def HDS能力模型核V2(core: MINIDORA模型核 | None = None) -> MINIDORA模型核:
    """同Dataの候補縮小再投票を無効化した能力模型核を返す。

    外界観測が変わらない内部再作用は行わず、観測viewが変化した場合の再評価は
    `HDS能力経路V2候補提案実行` が全候補で新しい評価Runとして行う。
    """

    base = core or 標準能力模型核()
    if not isinstance(base, MINIDORA能力状態差模型核):
        return base
    return MINIDORA能力状態差模型核(
        base.関係群,
        言語対応_=base.言語対応,
        能力作用群=base.能力作用群,
        形成済み関係群=base.形成済み関係群,
        最大再作用回数=0,
    )


def HDS局所観測view(
    question_ir: HDSIR,
    references: tuple[参照記録, ...],
    *,
    上限: int = 12,
) -> tuple[tuple[参照記録, ...], int]:
    """同一sourceの全文viewを最上位local windowへ置換する。

    source ID・provider・origin・confidence・query provenanceは保持し、独立source数を増やさない。
    """

    windows = HDS局所Window候補(question_ir, references, 上限=max(0, int(上限)))
    best_by_source = {}
    for row in windows:
        source_id = str(row.参照.識別子)
        if source_id not in best_by_source:
            best_by_source[source_id] = row

    changed = 0
    projected: list[参照記録] = []
    for record in references:
        row = best_by_source.get(str(record.識別子))
        if row is None or _正規化(row.内容).casefold() == _正規化(record.内容).casefold():
            projected.append(record)
            continue
        conditions = list(record.条件)
        marker = ("hds_observation_view", "local")
        if marker not in conditions:
            conditions.append(marker)
        projected.append(replace(record, 内容=row.内容, 条件=tuple(conditions)))
        changed += 1
    return tuple(projected), changed


def _寄与参照ID群(result: HDS選択実行結果) -> frozenset[str]:
    model = result.MINIDORA模型結果
    label = result.回答ラベル
    if model is None or label is None:
        return frozenset()
    row = next((item for item in model.候補差 if item.候補ID == label), None)
    if row is None:
        return frozenset()

    source_ids: set[str] = set()
    for contribution in row.寄与:
        for raw in contribution.根拠:
            text = str(raw)
            if text.startswith("参照:"):
                payload = text[len("参照:"):]
                source_id = payload.rsplit(":", 1)[0] if ":" in payload else payload
                if source_id:
                    source_ids.add(source_id)
            elif text.startswith("再照合:"):
                payload = text[len("再照合:"):]
                parts = payload.rsplit(":", 2)
                source_id = parts[0] if parts else payload
                if source_id:
                    source_ids.add(source_id)
    return frozenset(source_ids)


def _提案強度(result: HDS選択実行結果) -> tuple[int, int, int]:
    if result.状態 != "PROPOSE" or result.回答ラベル is None or result.MINIDORA模型結果 is None:
        return (-1, -10**9, -10**9)
    scores = result.MINIDORA模型結果.候補辞書()
    if result.回答ラベル not in scores:
        return (-1, -10**9, -10**9)
    top = int(scores[result.回答ラベル])
    second = max((int(value) for key, value in scores.items() if key != result.回答ラベル), default=0)
    return (len(_寄与参照ID群(result)), top - second, top)


def _局所再評価採用可能(initial: HDS選択実行結果, rechecked: HDS選択実行結果) -> bool:
    if rechecked.状態 != "PROPOSE" or rechecked.回答ラベル is None or rechecked.回答内容 is None:
        return False
    if initial.状態 != "PROPOSE" or initial.回答ラベル is None or initial.回答内容 is None:
        return True
    return _提案強度(rechecked) > _提案強度(initial)


def HDS能力経路V2候補提案実行(
    question_ir: HDSIR,
    references: tuple[参照記録, ...],
    *,
    コンパイル,
    基礎能力核: K3相当能力核,
    最大コンパイル並列: int = 4,
    模型核: MINIDORA模型核 | None = None,
    最大局所Window数: int = 12,
) -> HDS選択実行結果:
    """Rで閉じたDataをCが全候補評価し、実観測view変化時だけ再評価する。

    C_execはPROPOSEまで。COMMIT/SUSPEND権限は持たない。
    """

    initial = HDS候補提案実行(
        question_ir,
        references,
        コンパイル=コンパイル,
        基礎能力核=基礎能力核,
        最大コンパイル並列=最大コンパイル並列,
        模型核=HDS能力模型核V2(模型核),
    )
    initial = replace(
        initial,
        理由=tuple(dict.fromkeys(tuple(initial.理由) + (
            "C_SAME_DATA_CANDIDATE_NARROWING_DISABLED",
        ))),
    )

    local_references, changed = HDS局所観測view(
        question_ir,
        references,
        上限=最大局所Window数,
    )
    if changed <= 0:
        return initial

    rechecked = HDS候補提案実行(
        question_ir,
        local_references,
        コンパイル=コンパイル,
        基礎能力核=基礎能力核,
        最大コンパイル並列=最大コンパイル並列,
        模型核=HDS能力模型核V2(模型核),
    )
    common_reasons = (
        "C_OBSERVATION_VIEW_CHANGED",
        f"C_LOCAL_VIEW_SOURCE_COUNT:{changed}",
    )
    if _局所再評価採用可能(initial, rechecked):
        return replace(
            rechecked,
            理由=tuple(dict.fromkeys(tuple(rechecked.理由) + common_reasons + (
                "C_LOCAL_VIEW_RECHECK_SELECTED",
            ))),
            局所Window数=changed,
            局所再照合数=1,
        )
    return replace(
        initial,
        理由=tuple(dict.fromkeys(tuple(initial.理由) + common_reasons + (
            "C_LOCAL_VIEW_RECHECK_REJECTED",
        ))),
        局所Window数=changed,
        局所再照合数=1,
    )


__all__ = [
    "HDS候補被覆優先統合",
    "HDS参照検索V2",
    "HDS能力模型核V2",
    "HDS局所観測view",
    "HDS能力経路V2候補提案実行",
]

from __future__ import annotations

from dataclasses import replace

from .hds_ir import HDSIR
from .hds多時間尺度 import HDS多時間尺度政策, HDS阻害回復方針
from .hds参照計画 import (
    HDS参照索引圧縮,
    HDS参照計画作成,
    HDS参照計画消費,
    HDS参照計画適用,
    HDS参照計画無効化,
)
from .hds能力経路_v2 import HDS能力経路V2候補提案実行
from .k3_functional import K3相当能力核
from .模型 import MINIDORA模型核
from .参照 import 参照記録


def HDS能力経路V3候補提案実行(
    question_ir: HDSIR,
    references: tuple[参照記録, ...],
    *,
    コンパイル,
    基礎能力核: K3相当能力核,
    最大コンパイル並列: int = 4,
    模型核: MINIDORA模型核 | None = None,
    最大局所Window数: int = 12,
    政策: HDS多時間尺度政策 | None = None,
):
    """V2の安全境界を保ったまま、GLM構文化由来の参照計画層を通す。

    - 正本参照は変更しない。
    - 検索索引だけを4件単位で圧縮する。
    - 参照選択結果に有限leaseを与える。
    - 証拠/観測/矛盾由来の失敗では計画を無効化し、次の外界観測で再構築可能にする。
    - J/HDSのCOMMIT/SUSPEND権限は変更しない。
    """

    policy = 政策 or HDS多時間尺度政策()
    query = question_ir.正規化文 or question_ir.原文
    index = HDS参照索引圧縮(references, bucket幅=4)
    plan = HDS参照計画作成(
        query,
        references,
        索引=index,
        利用上限=policy.参照計画利用上限,
    )

    # 計画は対象ID集合を固定するが、既存V2のsource順序は変えない。
    planned = HDS参照計画適用(plan, references)
    selected_ids = {str(record.識別子) for record in planned}
    runtime_references = tuple(record for record in references if str(record.識別子) in selected_ids)
    plan = HDS参照計画消費(plan)

    result = HDS能力経路V2候補提案実行(
        question_ir,
        runtime_references,
        コンパイル=コンパイル,
        基礎能力核=基礎能力核,
        最大コンパイル並列=最大コンパイル並列,
        模型核=模型核,
        最大局所Window数=最大局所Window数,
    )

    reasons = list(result.理由)
    reasons.extend(
        (
            "RETRIEVAL_INDEX_SEPARATED_FROM_EVIDENCE",
            f"RETRIEVAL_INDEX_BUCKETS:{len(index.bucket群)}",
            f"RETRIEVAL_PLAN_ID:{plan.計画ID}",
            f"RETRIEVAL_PLAN_LEASE_REMAINING:{plan.残存利用回数}",
            f"LOCAL_GLOBAL_TIMESCALE:{policy.局所更新回数}:{policy.大域周期}",
        )
    )

    if result.状態 != "PROPOSE":
        recovery = HDS阻害回復方針(result.理由)
        reasons.append("BLOCKER_RECOVERY_POLICY:" + recovery.作用)
        if recovery.参照計画無効化:
            plan = HDS参照計画無効化(plan, recovery.作用)
            reasons.append("RETRIEVAL_PLAN_INVALIDATED_ON_EVIDENCE_STATE")
        if recovery.effort引上げ:
            reasons.append("EFFORT_ESCALATION_AVAILABLE")
        if recovery.Jへ留保:
            reasons.append("BLOCKER_DEFERRED_TO_J")

    return replace(result, 理由=tuple(dict.fromkeys(reasons)))


__all__ = ["HDS能力経路V3候補提案実行"]

from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable

from .HDS中間表現 import HDSIR
from .HDS観測計画 import HDS参照観測要求
from .参照 import 参照記録


@dataclass(frozen=True, slots=True)
class HDS候補検証関係:
    関係ID: str | None
    関係種別: str | None
    未知位置: str | None
    既知端点: tuple[str, ...] = ()
    条件範囲: tuple[tuple[str, str], ...] = ()


@dataclass(frozen=True, slots=True)
class HDS候補検証観測:
    観測ID: str
    段階: str
    外部検索表層: str
    必須被覆: bool
    優先度: int
    由来: tuple[str, ...] = ()


@dataclass(frozen=True, slots=True)
class HDS候補検証契約:
    候補ラベル: str
    候補表層: str
    関係: tuple[HDS候補検証関係, ...] = ()
    観測: tuple[HDS候補検証観測, ...] = ()

    @property
    def 観測ID群(self) -> tuple[str, ...]:
        return tuple(dict.fromkeys(項目.観測ID for 項目 in self.観測))


def _選択肢(ir: HDSIR) -> tuple[tuple[str, str], ...]:
    結果: list[tuple[str, str]] = []
    for 座標 in ir.座標:
        座標ID = str(getattr(座標, "座標ID", ""))
        if not 座標ID.startswith("選択肢:"):
            continue
        ラベル = 座標ID.split(":", 1)[1].strip()
        表層 = " ".join(str(getattr(座標, "内容", "")).split()).strip()
        if ラベル and 表層:
            結果.append((ラベル, 表層))
    return tuple(sorted(結果))



@dataclass(frozen=True, slots=True)
class HDS候補検証被覆:
    候補ラベル: str
    観測ID群: tuple[str, ...] = ()
    独立資料ID群: tuple[str, ...] = ()

    @property
    def 被覆数(self) -> int:
        return len(self.独立資料ID群)


def _参照条件値群(記録: 参照記録, 鍵: str) -> tuple[str, ...]:
    return tuple(str(値) for 条件鍵, 値 in 記録.条件 if str(条件鍵) == 鍵 and str(値))


def HDS候補検証被覆を測定(
    契約群: Iterable[HDS候補検証契約],
    参照群: Iterable[参照記録],
) -> tuple[HDS候補検証被覆, ...]:
    """Kernel候補契約と実観測provenanceを照合し、候補別の独立資料被覆を返す。"""
    参照 = tuple(参照群)
    結果: list[HDS候補検証被覆] = []
    for 契約 in tuple(契約群):
        観測ID群 = frozenset(契約.観測ID群)
        資料ID群: list[str] = []
        if 観測ID群:
            for 記録 in 参照:
                if 契約.候補ラベル not in _参照条件値群(記録, "hds_query_選択肢"):
                    continue
                if not 観測ID群.intersection(_参照条件値群(記録, "hds_observation_id")):
                    continue
                識別子 = str(記録.識別子)
                if 識別子 not in 資料ID群:
                    資料ID群.append(識別子)
        結果.append(HDS候補検証被覆(
            契約.候補ラベル,
            tuple(sorted(観測ID群)),
            tuple(資料ID群),
        ))
    return tuple(結果)


def HDS候補検証成立(
    契約群: Iterable[HDS候補検証契約],
    候補ラベル: str,
    参照群: Iterable[参照記録],
    *,
    最小独立資料数: int = 1,
) -> bool:
    if type(最小独立資料数) is not int or 最小独立資料数 < 0:
        raise ValueError("最小独立資料数は0以上の整数")
    対象 = next((x for x in tuple(契約群) if x.候補ラベル == str(候補ラベル)), None)
    if 対象 is None or not 対象.観測ID群:
        return True
    被覆 = next(
        (x for x in HDS候補検証被覆を測定((対象,), 参照群) if x.候補ラベル == str(候補ラベル)),
        None,
    )
    return bool(被覆 is not None and 被覆.被覆数 >= 最小独立資料数)


def HDS候補検証契約群(
    ir: HDSIR,
    観測要求: Iterable[HDS参照観測要求],
) -> tuple[HDS候補検証契約, ...]:
    """Compiler形成済み正本だけから、候補ごとの検証契約を束ねる。

    原文や候補表層を再解析せず、候補座標と参照観測要求に既に形成された
    関係・端点・条件範囲・観測経路だけを保持する。勝者選択や得点化は行わない。
    """

    選択肢 = _選択肢(ir)
    要求群 = tuple(観測要求)
    候補別要求: dict[str, list[HDS参照観測要求]] = {ラベル: [] for ラベル, _ in 選択肢}
    候補表層辞書 = {ラベル: 表層 for ラベル, 表層 in 選択肢}

    for 要求 in 要求群:
        ラベル = 要求.候補ラベル
        if ラベル is None or str(ラベル) not in 候補別要求:
            continue
        正本表層 = 候補表層辞書[str(ラベル)]
        要求表層 = " ".join(str(要求.候補表層 or "").split()).strip()
        if 要求表層 and 要求表層 != 正本表層:
            raise ValueError("候補観測要求の表層がKernel候補正本と一致しない:" + str(ラベル))
        候補別要求[str(ラベル)].append(要求)

    契約群: list[HDS候補検証契約] = []
    for ラベル, 表層 in 選択肢:
        関係群: list[HDS候補検証関係] = []
        観測群: list[HDS候補検証観測] = []
        既出関係: set[tuple[object, ...]] = set()
        既出観測: set[tuple[str, str, str]] = set()

        for 要求 in sorted(
            候補別要求[ラベル],
            key=lambda 項目: (
                int(項目.優先度), str(項目.ID), str(項目.段階),
                str(項目.外部検索表層).casefold(),
            ),
        ):
            関係署名 = (
                要求.関係ID,
                要求.関係種別,
                要求.未知位置,
                tuple(要求.既知端点),
                tuple(要求.条件範囲),
            )
            if 関係署名 not in 既出関係:
                既出関係.add(関係署名)
                関係群.append(HDS候補検証関係(*関係署名))

            観測署名 = (str(要求.ID), str(要求.段階), str(要求.外部検索表層).casefold())
            if 観測署名 in 既出観測:
                continue
            既出観測.add(観測署名)
            観測群.append(HDS候補検証観測(
                観測ID=str(要求.ID),
                段階=str(要求.段階),
                外部検索表層=str(要求.外部検索表層),
                必須被覆=bool(要求.必須被覆),
                優先度=int(要求.優先度),
                由来=tuple(str(x) for x in 要求.provenance),
            ))

        契約群.append(HDS候補検証契約(ラベル, 表層, tuple(関係群), tuple(観測群)))
    return tuple(契約群)


__all__ = [
    "HDS候補検証関係",
    "HDS候補検証観測",
    "HDS候補検証契約",
    "HDS候補検証被覆",
    "HDS候補検証被覆を測定",
    "HDS候補検証成立",
    "HDS候補検証契約群",
]

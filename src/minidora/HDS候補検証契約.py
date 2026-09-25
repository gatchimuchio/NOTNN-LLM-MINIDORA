from __future__ import annotations

from dataclasses import dataclass
from typing import Callable, Iterable

from .HDS中間表現 import HDSIR
from .HDS観測計画 import HDS参照観測要求
from .hds入力参照境界 import HDS入力資料本文
from .意味字句 import 意味語
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



_汎用検証関係 = frozenset({"問い適合", "命題適合", "説明適合", "未解決関係"})


def _意味集合(values: Iterable[str]) -> frozenset[str]:
    out: set[str] = set()
    for value in values:
        out.update(str(x).casefold() for x in 意味語(value) if str(x))
    return frozenset(out)


def _被覆率(期待: frozenset[str], 観測: frozenset[str]) -> float:
    if not 期待:
        return 1.0
    return len(期待.intersection(観測)) / len(期待)


def _関係条件辞書(関係) -> dict[str, tuple[str, ...]]:
    out: dict[str, list[str]] = {}
    for raw in tuple(getattr(関係, "条件", ())):
        key, sep, value = str(raw).partition("=")
        key, value = key.strip(), value.strip()
        if not sep or not key or not value:
            continue
        out.setdefault(key, []).append(value)
    return {key: tuple(values) for key, values in out.items()}


def _条件範囲一致(期待: tuple[tuple[str, str], ...], 関係) -> bool:
    if not 期待:
        return True
    実条件 = _関係条件辞書(関係)
    for key, value in 期待:
        値群 = 実条件.get(str(key), ())
        期待語 = _意味集合((str(value),))
        if not 値群:
            return False
        if not any(_被覆率(期待語, _意味集合((候補値,))) >= 1.0 for 候補値 in 値群):
            return False
    return True


def _IR全意味(ir: HDSIR) -> frozenset[str]:
    values = [
        str(coord.内容)
        for coord in ir.座標
        if str(coord.内容).strip()
        and not str(coord.種別).startswith(("監査.", "保持.", "暫定性.", "帰還."))
    ]
    return _意味集合(values)


def _関係意味一致(契約: HDS候補検証契約, 関係契約: HDS候補検証関係, ir: HDSIR) -> bool:
    候補語 = _意味集合((契約.候補表層,))
    既知語 = _意味集合(関係契約.既知端点)
    if not 候補語:
        return False

    if str(関係契約.関係種別 or "") in _汎用検証関係:
        全意味 = _IR全意味(ir)
        return _被覆率(候補語, 全意味) >= 1.0 and _被覆率(既知語, 全意味) >= 1.0

    座標辞書 = ir.座標辞書()
    for 関係 in ir.関係:
        if 関係契約.関係種別 and str(関係.種別) != str(関係契約.関係種別):
            continue
        if not _条件範囲一致(関係契約.条件範囲, 関係):
            continue
        始点語 = _意味集合(
            str(座標辞書[cid].内容) for cid in 関係.始点 if cid in 座標辞書
        )
        終点語 = _意味集合(
            str(座標辞書[cid].内容) for cid in 関係.終点 if cid in 座標辞書
        )
        if 関係契約.未知位置 == "始点":
            候補側, 既知側 = 始点語, 終点語
        elif 関係契約.未知位置 == "終点":
            候補側, 既知側 = 終点語, 始点語
        else:
            候補側, 既知側 = 始点語.union(終点語), 始点語.union(終点語)
        if _被覆率(候補語, 候補側) < 1.0:
            continue
        if _被覆率(既知語, 既知側) < 1.0:
            continue
        return True
    return False


def HDS候補意味検証資料ID群(
    契約: HDS候補検証契約,
    参照群: Iterable[参照記録],
    *,
    コンパイル: Callable[[str], HDSIR],
) -> tuple[str, ...]:
    """query provenanceではなく、資料をHDS-IRへ戻した意味内容で候補契約を検証する。"""
    if not callable(コンパイル):
        raise TypeError("候補意味検証にはコンパイル可能なHDS構文化器が必要")
    if not 契約.関係:
        return ()
    out: list[str] = []
    for 記録 in tuple(参照群):
        try:
            ir = コンパイル(HDS入力資料本文(記録))
        except (TypeError, ValueError):
            continue
        if not isinstance(ir, HDSIR):
            continue
        if any(_関係意味一致(契約, 関係項目, ir) for 関係項目 in 契約.関係):
            資料ID = str(記録.識別子)
            if 資料ID and 資料ID not in out:
                out.append(資料ID)
    return tuple(out)


def HDS候補検証成立(
    契約群: Iterable[HDS候補検証契約],
    候補ラベル: str,
    参照群: Iterable[参照記録],
    *,
    最小独立資料数: int = 1,
    コンパイル: Callable[[str], HDSIR] | None = None,
) -> bool:
    if type(最小独立資料数) is not int or 最小独立資料数 < 0:
        raise ValueError("最小独立資料数は0以上の整数")
    参照 = tuple(参照群)
    対象 = next((x for x in tuple(契約群) if x.候補ラベル == str(候補ラベル)), None)
    if 対象 is None:
        return True

    # まず観測経路の被覆を確認する。queryを投げただけでは意味成立とはみなさない。
    if 対象.観測ID群:
        被覆 = next(
            (x for x in HDS候補検証被覆を測定((対象,), 参照) if x.候補ラベル == str(候補ラベル)),
            None,
        )
        if 被覆 is None or 被覆.被覆数 < 最小独立資料数:
            return False

    if not 対象.関係 or コンパイル is None:
        return True
    意味資料 = HDS候補意味検証資料ID群(対象, 参照, コンパイル=コンパイル)
    return len(意味資料) >= 最小独立資料数


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
    "HDS候補意味検証資料ID群",
    "HDS候補検証成立",
    "HDS候補検証契約群",
]

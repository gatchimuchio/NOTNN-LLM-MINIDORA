"""選択問題の観測経路学習キー。

問題固有の候補ラベル・回答・gold・検索語本文を保持せず、Compilerが既に形成した
観測経路の構造だけを経験キーへ射影する。これは検索順の適応用であり、世界知識や
回答根拠そのものへ昇格しない。
"""
from __future__ import annotations

from dataclasses import dataclass
import json


@dataclass(frozen=True, slots=True, order=True)
class HDS観測経路鍵:
    関係種別: str
    未知位置: str
    経路種別: str
    必須被覆: bool
    外部言語: str


def 観測経路種別(要求) -> str:
    provenance = {str(x) for x in tuple(getattr(要求, "provenance", ()))}
    ID = str(getattr(要求, "ID", ""))
    if "局所検証" in provenance:
        return "局所検証"
    if "縮退" in provenance:
        return "縮退"
    if "監査.R_query" in provenance or ID.startswith("監査表層:"):
        return "監査"
    if "検索.外部表層" in provenance or ID.startswith("検索表層:"):
        return "外部表層"
    if "未解決関係" in provenance or ID.startswith("generic:"):
        return "未解決関係"
    if str(getattr(要求, "段階", "")) == "primary":
        return "主観測"
    return "代替観測"


def HDS観測経路鍵を構成(要求) -> HDS観測経路鍵:
    return HDS観測経路鍵(
        str(getattr(要求, "関係種別", None) or "未指定"),
        str(getattr(要求, "未知位置", None) or "未指定"),
        観測経路種別(要求),
        bool(getattr(要求, "必須被覆", False)),
        str(getattr(要求, "外部言語", "") or "未指定").casefold(),
    )


def HDS観測経路鍵を文字列(鍵: HDS観測経路鍵) -> str:
    if not isinstance(鍵, HDS観測経路鍵):
        raise TypeError("HDS観測経路鍵型が必要")
    return json.dumps(
        [鍵.関係種別, 鍵.未知位置, 鍵.経路種別, 鍵.必須被覆, 鍵.外部言語],
        ensure_ascii=False, separators=(",", ":"),
    )


def HDS観測経路鍵を復元(値: str) -> HDS観測経路鍵:
    try:
        row = json.loads(str(値))
    except (TypeError, ValueError, json.JSONDecodeError) as exc:
        raise ValueError("観測経路鍵形式不正") from exc
    if (
        not isinstance(row, list) or len(row) != 5
        or any(not isinstance(x, str) for x in row[:3])
        or type(row[3]) is not bool or not isinstance(row[4], str)
    ):
        raise ValueError("観測経路鍵形式不正")
    return HDS観測経路鍵(row[0], row[1], row[2], row[3], row[4])


def 参照観測経路鍵群(参照) -> tuple[HDS観測経路鍵, ...]:
    out = set()
    for key, value in tuple(getattr(参照, "条件", ())):
        if str(key) != "hds_query_学習経路":
            continue
        try:
            out.add(HDS観測経路鍵を復元(str(value)))
        except ValueError:
            continue
    return tuple(sorted(out))


__all__ = [
    "HDS観測経路鍵", "観測経路種別", "HDS観測経路鍵を構成",
    "HDS観測経路鍵を文字列", "HDS観測経路鍵を復元", "参照観測経路鍵群",
]

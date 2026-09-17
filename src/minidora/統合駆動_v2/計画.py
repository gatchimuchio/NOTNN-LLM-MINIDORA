"""有限な作用仕様から未登録の作用列を構成する。探索中は部品を実行しない。"""
from __future__ import annotations
from dataclasses import dataclass
import heapq
from .値 import 文字, 文字列組, 整数


@dataclass(frozen=True, slots=True)
class HDS作用仕様:
    作用ID: str
    入力状態: frozenset[str] = frozenset()
    追加状態: frozenset[str] = frozenset()
    削除状態: frozenset[str] = frozenset()
    解消残差: frozenset[str] = frozenset()
    追加残差: frozenset[str] = frozenset()
    読取認識: tuple[str, ...] = ()
    必要権限: tuple[str, ...] = ()
    資源負荷: int = 1
    版: str = "v1"
    純粋: bool = False

    def __post_init__(self):
        if type(self.純粋) is not bool: raise TypeError("純粋作用宣言はbool")
        文字(self.作用ID);文字(self.版)
        for n in ("入力状態","追加状態","削除状態","解消残差","追加残差"):
            v=getattr(self,n)
            if not isinstance(v,frozenset):raise TypeError(f"{n}はfrozenset")
            for x in v:文字(x)
        if self.追加状態 & self.削除状態 or self.解消残差 & self.追加残差:raise ValueError("相反する作用効果")
        文字列組(self.読取認識);文字列組(self.必要権限);整数(self.資源負荷,"計画資源負荷")


@dataclass(frozen=True, slots=True)
class HDS構成計画:
    作用列: tuple[str, ...]
    探索状態数: int
    打切り: bool = False
    予定資源: int = 0
    @property
    def 成立(self): return bool(self.作用列)


def 作用列を構成(成立状態,残差,要求状態,仕様群,*,最大深さ=12,最大状態数=2048,最大資源=4096,制約群=()):
    整数(最大深さ,"探索深さ",1);整数(最大状態数,"最大探索状態",1);整数(最大資源,"最大探索資源");文字列組(tuple(x.作用ID for x in 仕様群),"計画作用ID")
    仕様群=tuple(sorted(仕様群,key=lambda x:x.作用ID));関連状態,関連残差=set(要求状態),set(残差);関連ID=set();変化=True
    while 変化:
        変化=False
        for a in 仕様群:
            if a.作用ID not in 関連ID and (a.追加状態 & 関連状態 or a.解消残差 & 関連残差):
                関連ID.add(a.作用ID);関連状態.update(a.入力状態);関連残差.update(a.追加残差);変化=True
    仕様群=tuple(a for a in 仕様群 if a.作用ID in 関連ID);待ち=[(0,0,(),tuple(sorted(成立状態)),tuple(sorted(残差)))];最小費用={(成立状態,残差,0):0};数=0;深度打切り=False
    while 待ち and 数<最大状態数:
        費用,深さ,列,s,r=heapq.heappop(待ち);数+=1;s,r=frozenset(s),frozenset(r)
        if 要求状態<=s and not r:return HDS構成計画(列,数,False,費用)
        if 深さ>=最大深さ:深度打切り=True;continue
        for a in 仕様群:
            if not a.入力状態<=s:continue
            ns=(s-a.削除状態)|a.追加状態;nr=(r-a.解消残差)|a.追加残差
            if any(c.違反(ns) for c in 制約群):continue
            if (ns,nr)==(s,r):continue
            nf=費用+a.資源負荷
            if nf>最大資源:深度打切り=True;continue
            鍵=(ns,nr,深さ+1)
            if nf>=最小費用.get(鍵,float("inf")):continue
            最小費用[鍵]=nf;heapq.heappush(待ち,(nf,深さ+1,列+(a.作用ID,),tuple(sorted(ns)),tuple(sorted(nr))))
    return HDS構成計画((),数,bool(待ち) or 深度打切り)

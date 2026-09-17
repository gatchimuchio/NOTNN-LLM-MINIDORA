"""通常の成功履歴から経験を形成し、純粋作用に限り自動再実行で検証する。

副作用を持つ作用・署名不一致・再現不成立を成功則へ昇格しない。
単一トレースの暗記を汎用知識の獲得とは呼ばない。
"""
from __future__ import annotations
from copy import deepcopy
from dataclasses import replace
from .値 import 署名
from .形成 import HDS経験, 経験から形成, 再実行で検証
from .状態更新 import 状態更新, 閉包可能, 有効認識
from .政策 import HDS阻害, 停止理由


def 自動形成文脈(状態, 作用群):
    specs = tuple(sorted((a.作用ID, a.計画仕様.版) for a in 作用群 if getattr(a, "計画仕様", None) is not None))
    return 状態.主体辞書().get("形成文脈署名") or 署名((状態.目的, 状態.要求状態, 状態.要求認識, specs))


class 自動経験形成作用:
    作用ID = "内的/経験形成"
    def __init__(self, 初期, 履歴, 作用群, 最終検証器=()):
        self.初期,self.履歴=deepcopy(初期),tuple(履歴); self.作用={a.作用ID:a for a in 作用群}; self.検証=tuple(最終検証器); self.再現回数=0; self.再現成功=False
    def _経験(self,状態):
        from ..HDS実行主体 import HDS作用状態
        trace=tuple(x for x in self.履歴 if x.作用ID!="内的/目的検証")
        if not trace or any(x.作用ID not in self.作用 or x.作用状態!=HDS作用状態.成立 or x.阻害 for x in trace): return None
        specs=[getattr(self.作用[x.作用ID],"計画仕様",None) for x in trace]
        if any(s is None or not s.純粋 for s in specs): return None
        context=自動形成文脈(self.初期,tuple(self.作用.values())); evidence=署名((self.初期.状態署名,状態.状態署名,trace))
        return HDS経験("実経験:"+evidence[:24],self.初期.成立状態,self.初期.要求状態,tuple(x.作用ID for x in trace),True,evidence,context,作用契約=tuple(sorted({(s.作用ID,s.版) for s in specs})))
    def 機会(self,状態):
        from ..HDS実行主体 import HDS作用機会
        e=self._経験(状態)
        if e is None:return None
        formed=経験から形成(e)
        if any(x.ID==formed.ID and e.根拠署名 in x.由来 for x in 状態.形成関係):return None
        pure=all(self.作用[k].計画仕様.純粋 for k in e.作用列); cost=1+(sum(self.作用[k].計画仕様.資源負荷 for k in e.作用列)+len(self.検証) if pure else 0)
        return HDS作用機会(self.作用ID,署名(e),資源負荷=cost,種別="経験形成")
    def 実行(self,状態):
        from ..HDS実行主体 import HDS作用結果,HDS作用状態
        e=self._経験(状態)
        if e is None:raise ValueError("形成対象の完全な実経験がない")
        relation=経験から形成(e); old=next((x for x in 状態.形成関係 if x.ID==relation.ID),None)
        if old: relation=replace(relation,由来=tuple(sorted(set(old.由来)|set(relation.由来))),反例=old.反例,版=old.版+1)
        pure=all(self.作用[k].計画仕様.純粋 for k in e.作用列); notes=["実履歴から条件付き手順を形成"]
        if pure:
            current,failure=deepcopy(self.初期),""
            try:
                for k in e.作用列:
                    a=self.作用[k]; source=deepcopy(current); sig=source.状態署名; offer=a.機会(source)
                    if offer is None or not offer.入力状態<=current.成立状態 or any(not 有効認識(current,n) for n in offer.読取認識):raise ValueError("再実行前提が不成立")
                    out=a.実行(source); self.再現回数+=1
                    if source.状態署名!=sig or out.状態!=HDS作用状態.成立 or out.阻害 or out.停止要求:raise ValueError("再実行が成立しないか入力を変更した")
                    from .依存 import HDS依存辺
                    read={"状態:"+n for n in offer.入力状態}|{"認識:"+n for n in (*offer.読取認識,*offer.未確定読取)}|{"成果:"+n for n in offer.読取成果}; produced={"認識:"+x.ID for x in out.認識更新}|{"成果:"+n for n,_ in out.成果}|{"状態:"+n for n in out.追加状態}
                    edges=set(out.依存追加)|{HDS依存辺(x,y) for x in read for y in produced if x!=y}; out=replace(out,依存追加=tuple(sorted(edges)),検証依存=tuple(sorted({**dict(out.検証依存),**{n:current.ノード署名(n) for n in read}}.items())))
                    current,_=状態更新(current,out)
                if not 閉包可能(current):raise ValueError("再実行で目的未達")
                def 結果署名(s):return 署名((s.成果,s.主体状態,s.成立状態,s.残差,tuple((x.ID,x.意味署名) for x in s.認識),s.草案,s.記憶.正本署名))
                if 結果署名(current)!=結果署名(状態):raise ValueError("再実行結果が元実測と不一致")
                for v in self.検証:
                    candidate=deepcopy(current); before=candidate.状態署名; valid=v.検証(candidate,None)
                    if valid is not True or candidate.状態署名!=before:raise ValueError("再実行の最終検証が不成立")
                self.再現成功=True
            except Exception as exc:failure=f"{type(exc).__name__}: {exc}"
            measured=replace(e,ID=e.ID+"/再現",成功=not failure,根拠署名=署名(("再実行",current.状態署名,self.再現回数,failure)),失敗署名=署名(failure) if failure else "")
            relation=再実行で検証(relation,measured,"純粋作用の実再現-v3"); notes.append("再実行検証成立" if not failure else "再実行検証不成立: "+failure)
        else:notes.append("副作用安全性の宣言がないため再実行しない。未検証形成として保持")
        return HDS作用結果(HDS作用状態.成立,形成更新=(relation,),理由=tuple(notes))

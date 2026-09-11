"""複数の入力役割を持つ作用契約の後方計画。成果型は予定であり実行成功ではない。"""
from __future__ import annotations
from copy import deepcopy
from dataclasses import dataclass
from typing import Callable
from .会話意味 import 意味目的, 意味指紋
from .能力合成 import 合成工程, 合成計画, 素材参照
from .製品版.型 import 能力結果

役割計画版 = 'MINIDORA-役割計画-v0.1'


@dataclass(frozen=True, slots=True)
class 役割作用:
    識別子: str
    能力: str
    成果種別: str
    必要役割: Callable[[dict], tuple[tuple[str, 意味目的], ...]]
    設定: Callable[[dict], dict]
    適用: Callable[[dict], bool]
    費用: int = 1
    外部読取: bool = False
    不成立条件: tuple[str, ...] = ()
    保持事項: tuple[str, ...] = ('対象', '単位', '条件', '由来')


@dataclass(frozen=True, slots=True)
class 役割計画結果:
    計画: 合成計画
    Data: dict[str, 能力結果]
    工程作用: tuple[tuple[str, str, str], ...]  # 工程ID・目的鍵・作用ID
    目的印: str
    費用: int
    展開数: int
    外部作用: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class _経路:
    目的: 意味目的
    作用: 役割作用 | None
    子: tuple[tuple[str, '_経路'], ...]
    費用: int

    def 署名(self):
        return (self.目的.鍵(), self.作用.識別子 if self.作用 else '素材',
                tuple((name,p.署名()) for name,p in self.子))


class 役割計画器:
    def __init__(self, 作用: tuple[役割作用, ...], 登録一覧, *, 最大深さ=12, 最大展開数=512):
        if type(作用) is not tuple or not 1 <= len(作用) <= 128:
            raise ValueError('作用契約の数・型')
        for n,limit in ((最大深さ,16),(最大展開数,4096)):
            if type(n) is not int or not 1 <= n <= limit: raise ValueError('探索上限不正')
        actual={r['名前']:r for r in 登録一覧}
        if len(actual)!=len(登録一覧): raise ValueError('登録能力の重複')
        seen=set()
        for r in 作用:
            if type(r) is not 役割作用 or r.識別子 in seen or r.能力 not in actual:
                raise ValueError('作用契約の重複・未登録能力')
            if type(r.費用) is not int or not 1 <= r.費用 <= 100:
                raise ValueError('作用費用は正の有界整数')
            if type(r.外部読取) is not bool or actual[r.能力]['外部読取'] != r.外部読取:
                raise ValueError('外部作用の契約不一致')
            seen.add(r.識別子)
        self.作用, self._上限 = 作用, (最大深さ, 最大展開数)
        self.登録印 = 意味指紋(list(登録一覧))

    def 計画する(self, 目的: 意味目的, 素材: dict[str, 能力結果], *, 禁止=(), 外部許可=False):
        if type(目的) is not 意味目的 or type(素材) is not dict or type(外部許可) is not bool:
            raise ValueError('計画要求型不正')
        if type(禁止) is not tuple or len(禁止)>64 or any(type(x) is not tuple or len(x)!=2 for x in 禁止):
            raise ValueError('禁止は目的鍵と作用IDの対')
        root=deepcopy(目的); root.鍵()
        banned=set(禁止); expanded=0; memo={}
        def solve(goal, stack):
            nonlocal expanded
            key=goal.鍵()
            if key in stack: raise ValueError('目的依存の循環')
            if len(stack)>=self._上限[0]: raise ValueError('役割計画の深さ上限')
            if key in memo: return memo[key]
            expanded+=1
            if expanded>self._上限[1]: raise ValueError('役割計画の展開上限')
            if goal.種別=='原資料':
                if set(goal.引数)!={'資料'} or goal.引数['資料'] not in 素材:
                    raise ValueError('必要資料がない')
                if not 素材[goal.引数['資料']].成立: raise ValueError('入力素材が未成立')
                return _経路(goal,None,(),0)
            paths=[]
            for rule in self.作用:
                if rule.成果種別!=goal.種別 or (key,rule.識別子) in banned: continue
                if rule.外部読取 and not 外部許可: continue
                applicable=rule.適用(deepcopy(goal.引数))
                if type(applicable) is not bool: raise ValueError('適用条件はbool')
                if not applicable: continue
                roles=rule.必要役割(deepcopy(goal.引数))
                if type(roles) is not tuple or len(roles)>8 or len({n for n,_ in roles})!=len(roles):
                    raise ValueError('入力役割の型・重複・上限')
                try:
                    children=tuple((name,solve(child,stack+(key,))) for name,child in roles)
                except _経路なし:
                    continue
                cost=rule.費用+sum(c.費用 for _,c in children)
                paths.append(_経路(goal,rule,children,cost))
            if not paths: raise _経路なし('目的に適合する作用経路がない:'+goal.種別)
            bestcost=min(p.費用 for p in paths)
            best={p.署名():p for p in paths if p.費用==bestcost}
            if len(best)!=1: raise ValueError('同順位の意味経路が複数ある')
            memo[key]=next(iter(best.values())); return memo[key]
        chosen=solve(root,())
        data={}; steps=[]; trace=[]; external=[]; refs={}
        def emit(path):
            signature=path.署名()
            if signature in refs: return refs[signature]
            if path.作用 is None:
                name=path.目的.引数['資料']; ident='素材:'+name
                data[ident]=deepcopy(素材[name]); out=素材参照('入力',ident)
            else:
                children=tuple((name,emit(p)) for name,p in path.子)
                if len(steps)>=64: raise ValueError('合成工程数上限')
                sid=f'役割工程:{len(steps)+1:04d}'; inst='指示:'+sid; config='設定:'+sid
                # 対象や実値は設定Dataと参照に置く。工程の命令本文へ埋め込まない。
                data[inst]=能力結果(True,'要求された成果を得る')
                settings=path.作用.設定(deepcopy(path.目的.引数))
                if type(settings) is not dict: raise ValueError('作用設定はData辞書')
                data[config]=能力結果(True,'',データ=settings)
                steps.append(合成工程(sid,(path.作用.能力,),inst,tuple(r for _,r in children),config))
                trace.append((sid,path.目的.鍵(),path.作用.識別子))
                if path.作用.外部読取: external.append(sid)
                out=素材参照('工程',sid)
            refs[signature]=out; return out
        final=emit(chosen)
        if final.領域!='工程': raise ValueError('素材を実行成果として採用しない')
        return 役割計画結果(合成計画(tuple(steps),(final.識別子,)),data,tuple(trace),
                               root.鍵(),chosen.費用,expanded,tuple(external))


class _経路なし(ValueError):
    pass

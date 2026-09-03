from __future__ import annotations

from dataclasses import dataclass, field
from typing import Protocol, Sequence

from .semantic_tokens import 意味語
from .言語構造 import 言語関係構造, 意味列, 言語関係抽出
from .能力作用則 import 証拠状態合計寄与

LLM成立規定リポジトリ = "https://github.com/gatchimuchio/LLM-Constitutive-Specification"
LLM成立規定参照コミット = "306ff834e5ac7e7e958b513db723a24619c8895a"
LLM成立規定版 = "2026-08-27-成立規定-3"
LLM成立意味区別 = ("独立対象","文脈依存関係","関係再利用","言語対応","局所対応")
LLM構成再現区別 = (
    "状態分離・保持・更新",
    "意味・関係同一性追跡",
    "未確定差の共存",
    "寄与調整と確定分離",
    "構成連鎖・再作用・再結合",
    "再作用閉包・終端成立差",
    "形成済み関係の保持と作用機構との分離",
)

@dataclass(frozen=True, slots=True)
class 言語状態:
    内容: str
    言語体系: str = "自然言語:ja"
    識別子: str = ""
    関係構造: tuple[言語関係構造,...] = ()
    def __post_init__(self):
        if not self.言語体系.strip(): raise ValueError("言語体系は空にできない")
        if not isinstance(self.内容,str): raise TypeError("言語状態.内容は文字列である必要がある")

@dataclass(frozen=True, slots=True)
class 内部言語状態:
    表層: str
    言語体系: str
    意味語集合: frozenset[str]
    識別子: str = ""
    意味語列: tuple[str,...] = ()
    関係構造: tuple[言語関係構造,...] = ()
    @property
    def 構造署名(self):
        return (self.言語体系,self.意味語列,tuple(x.署名 for x in self.関係構造))

@dataclass(frozen=True, slots=True)
class 文脈付き言語状態:
    現在: 内部言語状態
    履歴: tuple[内部言語状態,...] = ()
    条件: tuple[str,...] = ()
    参照状態: tuple[内部言語状態,...] = ()
    @property
    def 意味語集合(self):
        out=set(self.現在.意味語集合)
        for s in self.履歴: out.update(s.意味語集合)
        for c in self.条件: out.update(意味語(c))
        return frozenset(out)

@dataclass(frozen=True, slots=True)
class 成立候補:
    候補ID: str
    状態: 言語状態
    def __post_init__(self):
        if not self.候補ID.strip(): raise ValueError("候補IDは空にできない")

@dataclass(frozen=True, slots=True)
class 関係寄与:
    関係名: str
    差: int
    根拠: tuple[str,...] = ()

@dataclass(frozen=True, slots=True)
class 成立差:
    候補ID: str
    差: int
    寄与: tuple[関係寄与,...] = ()

@dataclass(frozen=True, slots=True)
class 模型Checkpoint:
    段階: str
    候補差: tuple[tuple[str,int],...]
    未確定候補ID: tuple[str,...] = ()
    再利用元: tuple[str,...] = ()

@dataclass(frozen=True, slots=True)
class 模型統計:
    寄与状態生成数: int = 0
    寄与状態再利用数: int = 0
    checkpoint再活性数: int = 0
    大域再照合数: int = 0
    候補横断更新数: int = 0
    再作用回数: int = 0
    終端遍歴数: int = 0

@dataclass(frozen=True, slots=True)
class 模型結果:
    文脈: 文脈付き言語状態
    候補差: tuple[成立差,...]
    最有力候補ID: str|None
    同率候補ID: tuple[str,...] = ()
    checkpoint: tuple[模型Checkpoint,...] = ()
    統計: 模型統計 = 模型統計()
    参照最有力候補ID: str|None = None
    参照同率候補ID: tuple[str,...] = ()
    def 候補辞書(self): return {x.候補ID:x.差 for x in self.候補差}
    def 参照候補辞書(self):
        out={x.候補ID:0 for x in self.候補差}
        for row in self.候補差:
            out[row.候補ID]=sum(c.差 for c in row.寄与 if c.関係名.startswith(("参照関係寄与","候補共同参照","候補共同再照合")))
        return out

class 言語対応:
    def 内部化(self, 状態:言語状態)->内部言語状態:
        parsed=言語関係抽出(状態.内容,状態.言語体系)
        rels=[]; seen=set()
        for item in (*parsed,*状態.関係構造):
            if item.署名 not in seen:
                seen.add(item.署名); rels.append(item)
        return 内部言語状態(状態.内容,状態.言語体系,意味語(状態.内容),状態.識別子,意味列(状態.内容),tuple(rels))
    def 文脈化(self,現在,履歴:Sequence[言語状態]=(),条件:Sequence[str]=(),参照状態:Sequence[言語状態]=()):
        for state in (*履歴,*参照状態):
            if state.言語体系!=現在.言語体系: raise ValueError("同一の文脈評価内で言語体系を無言混在させない")
        # 同一の意味・関係構造を持つDataを、出典IDが違うだけで複数票へ増幅しない。
        references=[]; seen_reference=set()
        for state in 参照状態:
            internal=self.内部化(state)
            signature=internal.構造署名
            if signature in seen_reference: continue
            seen_reference.add(signature); references.append(internal)
        return 文脈付き言語状態(self.内部化(現在),tuple(self.内部化(x) for x in 履歴),tuple(str(x) for x in 条件),tuple(references))

class 模型関係(Protocol):
    名称:str
    def 評価(self,文脈:文脈付き言語状態,候補:内部言語状態)->関係寄与|None:...

@dataclass(frozen=True, slots=True)
class 関係規則:
    名称:str
    文脈必須:frozenset[str]=field(default_factory=frozenset)
    候補必須:frozenset[str]=field(default_factory=frozenset)
    文脈禁止:frozenset[str]=field(default_factory=frozenset)
    候補禁止:frozenset[str]=field(default_factory=frozenset)
    差:int=1
    根拠:tuple[str,...]=()
    def 評価(self,文脈,候補):
        context=文脈.意味語集合; cand=候補.意味語集合
        if not self.文脈必須.issubset(context) or not self.候補必須.issubset(cand): return None
        if self.文脈禁止.intersection(context) or self.候補禁止.intersection(cand): return None
        if not (self.文脈必須 or self.候補必須 or self.文脈禁止 or self.候補禁止): return None
        return 関係寄与(self.名称,int(self.差),self.根拠)

@dataclass(frozen=True, slots=True)
class 意味連続関係:
    名称:str="意味連続"; 関係語重み:int=2
    def 評価(self,文脈,候補):
        shared=文脈.意味語集合.intersection(候補.意味語集合)
        if not shared:return None
        r=sum(1 for t in shared if t.startswith("rel:")); d=(len(shared)-r)+r*self.関係語重み
        return 関係寄与(self.名称,d,tuple(f"共有:{t}" for t in sorted(shared))) if d>0 else None

@dataclass(frozen=True, slots=True)
class 順序連続関係:
    名称:str="順序連続"
    @staticmethod
    def _二連(seq): return frozenset(zip(seq,seq[1:]))
    def 評価(self,文脈,候補):
        shared=self._二連(文脈.現在.意味語列).intersection(self._二連(候補.意味語列))
        return 関係寄与(self.名称,len(shared),tuple(f"順序:{a}>{b}" for a,b in sorted(shared))) if shared else None

def _端点一致(a,b): return bool(a and b and a.intersection(b))
def _関係同型(a,b,*,肯否無視=False,条件無視=True):
    if a.種別!=b.種別:return False
    if not _端点一致(a.始点,b.始点) or not _端点一致(a.終点,b.終点):return False
    if not 肯否無視 and a.肯定!=b.肯定:return False
    if not 条件無視 and a.条件!=b.条件:return False
    return True

@dataclass(frozen=True, slots=True)
class 有向関係整合:
    名称:str="有向関係整合"; 一致差:int=4; 逆向差:int=-2
    def 評価(self,文脈,候補):
        score=0; ev=[]
        for base in 文脈.現在.関係構造:
            for item in 候補.関係構造:
                if base.種別!=item.種別: continue
                if _端点一致(base.始点,item.始点) and _端点一致(base.終点,item.終点):score+=self.一致差;ev.append(f"有向一致:{base.種別}")
                elif _端点一致(base.始点,item.終点) and _端点一致(base.終点,item.始点):score+=self.逆向差;ev.append(f"逆向:{base.種別}")
        return 関係寄与(self.名称,score,tuple(ev)) if score else None

@dataclass(frozen=True, slots=True)
class 肯否整合関係:
    名称:str="肯否整合"; 一致差:int=2; 不一致差:int=-3
    def 評価(self,文脈,候補):
        score=0;ev=[]
        for base in 文脈.現在.関係構造:
            for item in 候補.関係構造:
                if not _関係同型(base,item,肯否無視=True):continue
                if base.肯定==item.肯定:score+=self.一致差;ev.append(f"肯否一致:{base.種別}")
                else:score+=self.不一致差;ev.append(f"肯否不一致:{base.種別}")
        return 関係寄与(self.名称,score,tuple(ev)) if score else None

@dataclass(frozen=True, slots=True)
class 履歴近接関係:
    名称:str="履歴近接"; 最大参照履歴:int=8
    def 評価(self,文脈,候補):
        score=0;ev=[]
        for distance,state in enumerate(reversed(文脈.履歴[-self.最大参照履歴:]),1):
            shared=state.意味語集合.intersection(候補.意味語集合)
            if shared:
                w=max(1,4-distance);score+=len(shared)*w;ev.append(f"履歴距離{distance}:{len(shared)}")
        return 関係寄与(self.名称,score,tuple(ev)) if score else None

@dataclass(frozen=True, slots=True)
class 条件結合関係:
    名称:str="条件結合"; 一致差:int=3; 不一致差:int=-1
    def 評価(self,文脈,候補):
        score=0;ev=[]
        for base in 文脈.現在.関係構造:
            if not base.条件:continue
            for item in 候補.関係構造:
                if not _関係同型(base,item,条件無視=True):continue
                if base.条件==item.条件:score+=self.一致差;ev.append(f"条件一致:{base.種別}")
                else:score+=self.不一致差;ev.append(f"条件不一致:{base.種別}")
        return 関係寄与(self.名称,score,tuple(ev)) if score else None

@dataclass(frozen=True, slots=True)
class 参照関係寄与作用:
    名称:str="参照関係寄与"
    def 評価(self,文脈,候補):
        score=0; used=0; detail=[]
        reverse=any(str(x).casefold()=="選択意図=反転" for x in 文脈.条件)
        for state in 文脈.参照状態:
            delta=証拠状態合計寄与(候補.関係構造,state.関係構造)
            if delta:
                score+=delta;used+=1;detail.append(f"参照:{state.識別子 or 'anonymous'}:{delta}")
        if reverse:score=-score
        return 関係寄与(self.名称,score,(f"参照状態:{used}",*detail)) if score else None

@dataclass(frozen=True, slots=True)
class 候補共同参照作用:
    名称:str="候補共同参照"
    def _evaluate(self,文脈,候補群,*,name):
        sigs={cid:s.意味語集合 for cid,s in 候補群}
        distinctive={}
        for cid,vals in sigs.items():
            others=set()
            for oid,ov in sigs.items():
                if oid!=cid:others.update(ov)
            distinctive[cid]=frozenset(set(vals)-others)
        reverse=any(str(x).casefold()=="選択意図=反転" for x in 文脈.条件)
        scores={cid:0 for cid,_ in 候補群}; evidence={cid:[] for cid,_ in 候補群}
        aggregate_relation={cid:0 for cid,_ in 候補群}
        aggregate_token={cid:0 for cid,_ in 候補群}
        for ref in 文脈.参照状態:
            token_hits={cid:len(distinctive[cid].intersection(ref.意味語集合)) for cid,_ in 候補群}
            relation_hits={cid:証拠状態合計寄与(state.関係構造,ref.関係構造) for cid,state in 候補群}
            for cid,_ in 候補群:
                aggregate_relation[cid]+=relation_hits[cid]
                aggregate_token[cid]+=token_hits[cid]
            if reverse:
                continue
            # 関係差を第一軸、語の固有差を第二軸として序数比較する。加重和にしない。
            rank={cid:(relation_hits[cid],token_hits[cid]) for cid,_ in 候補群}
            maximum=max(rank.values(),default=(0,0))
            if maximum<=(0,0): continue
            top=[cid for cid,v in rank.items() if v==maximum]
            if len(top)!=1: continue
            cid=top[0]
            scores[cid]+=1;evidence[cid].append(f"再照合:{ref.識別子 or 'anonymous'}:{maximum[0]}:{maximum[1]}")
        if reverse and 候補群:
            # 反転問題では支持を単に負へするのでなく、候補集合全体の相対差として例外を読む。
            # 少なくとも候補間に参照差がある場合だけ、最小支持の一候補へ正の差を与える。
            aggregate={cid:(aggregate_relation[cid],aggregate_token[cid]) for cid,_ in 候補群}
            minimum=min(aggregate.values())
            maximum=max(aggregate.values())
            bottom=[cid for cid,v in aggregate.items() if v==minimum]
            if minimum!=maximum and len(bottom)==1:
                cid=bottom[0]
                scores[cid]+=1
                evidence[cid].append(f"反転例外:{minimum[0]}:{minimum[1]}->{maximum[0]}:{maximum[1]}")
        return {cid:関係寄与(name,score,tuple(evidence[cid])) for cid,score in scores.items() if score}
    def 評価群(self,文脈,候補群): return self._evaluate(文脈,候補群,name=self.名称)
    def 再評価群(self,文脈,候補群,round_index:int): return self._evaluate(文脈,候補群,name=f"候補共同再照合:{round_index}")

@dataclass
class _作業状態:
    contributions:dict[str,list[関係寄与]]
    checkpoints:list[模型Checkpoint]
    seen_active:set[tuple[str,...]]
    created:int=0; reused:int=0; reactivated:int=0; global_reconcile:int=0; cross_updates:int=0; rounds:int=0
    def add(self,cid,item):
        key=(item.関係名,item.差,item.根拠)
        if any((x.関係名,x.差,x.根拠)==key for x in self.contributions[cid]):
            return False
        self.contributions[cid].append(item);self.created+=1;return True
    def scores(self):return {cid:sum(x.差 for x in rows) for cid,rows in self.contributions.items()}
    def checkpoint(self,stage,active=(),reuse=()):
        scores=self.scores(); self.checkpoints.append(模型Checkpoint(stage,tuple(sorted(scores.items())),tuple(active),tuple(reuse)))

class MINIDORA模型核:
    def __init__(self,関係群:Sequence[模型関係]=(),*,言語対応_:言語対応|None=None,能力作用群:Sequence[object]=(),形成済み関係群:Sequence[模型関係]=(),最大再作用回数:int=2):
        self.言語対応=言語対応_ or 言語対応();self._関係群=list(関係群);self._能力作用群=list(能力作用群);self._形成済み関係群=list(形成済み関係群);self.最大再作用回数=max(0,int(最大再作用回数))
    @property
    def 関係群(self):return tuple(self._関係群)
    @property
    def 能力作用群(self):return tuple(self._能力作用群)
    @property
    def 形成済み関係群(self):return tuple(self._形成済み関係群)
    def 関係登録(self,関係):
        if not getattr(関係,"名称",""):raise ValueError("模型関係には名称が必要")
        self._関係群.append(関係)
    def 形成済み関係登録(self,関係):
        if not getattr(関係,"名称",""):raise ValueError("形成済み関係には名称が必要")
        self._形成済み関係群.append(関係)
    def 文脈化(self,現在,履歴=(),条件=(),参照状態=()):return self.言語対応.文脈化(現在,履歴,条件,参照状態)

    def 評価(self,文脈:文脈付き言語状態,候補群:Sequence[成立候補])->模型結果:
        if not 候補群:raise ValueError("成立差の評価には1候補以上が必要")
        ids=[x.候補ID for x in 候補群]
        if len(ids)!=len(set(ids)):raise ValueError("候補IDは評価内で一意である必要がある")
        internal=[]
        for c in 候補群:
            if c.状態.言語体系!=文脈.現在.言語体系:raise ValueError("候補と言語文脈の言語体系が一致しない")
            internal.append((c.候補ID,self.言語対応.内部化(c.状態)))
        work=_作業状態({cid:[] for cid in ids},[],set())

        # 1) 一般作用。ここでは確定せず寄与状態だけ作る。
        for cid,state in internal:
            for rel in self._関係群:
                item=rel.評価(文脈,state)
                if item:work.add(cid,item)
        work.checkpoint("STANDARD_RELATIONS",ids)

        # 2) 形成済み関係は作用機構と分離した別段で再利用する。
        for cid,state in internal:
            for rel in self._形成済み関係群:
                item=rel.評価(文脈,state)
                if item:work.add(cid,item)
        work.checkpoint("FORMED_RELATIONS",ids)

        # 3) 参照/共同作用の初回作用。
        for action in self._能力作用群:
            if hasattr(action,"評価群"):
                result=action.評価群(文脈,tuple(internal))
                for cid,item in result.items():work.add(cid,item)
            else:
                for cid,state in internal:
                    item=action.評価(文脈,state)
                    if item:work.add(cid,item)
        work.checkpoint("PRIMARY_CAPABILITY_ACTIONS",ids)

        # 4) 候補共同状態を変えながら、過去状態へ再作用する。active集合が同じなら重複反復しない。
        for round_index in range(1,self.最大再作用回数+1):
            scores=work.scores()
            ordered=sorted(ids,key=lambda cid:(-scores[cid],cid))
            active=tuple(ordered[:min(2,len(ordered))])
            if active in work.seen_active:break
            work.seen_active.add(active);work.reactivated+=1;work.global_reconcile+=1;work.rounds+=1
            active_rows=tuple(row for row in internal if row[0] in active)
            changed=0
            for action in self._能力作用群:
                if not hasattr(action,"再評価群"):continue
                result=action.再評価群(文脈,active_rows,round_index)
                for cid,item in result.items():
                    if work.add(cid,item):changed+=1;work.reused+=1
            work.cross_updates+=changed
            work.checkpoint(f"RECONCILE_{round_index}",active,reuse=("PRIMARY_CAPABILITY_ACTIONS",))
            if not changed:break

        differences=tuple(成立差(cid,sum(x.差 for x in work.contributions[cid]),tuple(work.contributions[cid])) for cid in ids)
        maximum=max(x.差 for x in differences);top=tuple(x.候補ID for x in differences if x.差==maximum)
        # 正の成立差が一意に形成された場合だけ一般模型結果を確定する。
        winner=top[0] if maximum>0 and len(top)==1 else None

        ref_scores={row.候補ID:sum(c.差 for c in row.寄与 if c.関係名.startswith(("参照関係寄与","候補共同参照","候補共同再照合"))) for row in differences}
        ref_max=max(ref_scores.values(),default=0);ref_top=tuple(cid for cid,v in ref_scores.items() if v==ref_max)
        ref_winner=ref_top[0] if ref_max>0 and len(ref_top)==1 else None
        stats=模型統計(work.created,work.reused,work.reactivated,work.global_reconcile,work.cross_updates,work.rounds,len(work.checkpoints))
        return 模型結果(文脈,differences,winner,top if len(top)>1 else (),tuple(work.checkpoints),stats,ref_winner,ref_top if len(ref_top)>1 else ())

    def 評価言語状態(self,現在,候補群,*,履歴=(),条件=(),参照状態=()):
        return self.評価(self.文脈化(現在,履歴,条件,参照状態),候補群)

def 標準模型核()->MINIDORA模型核:
    return MINIDORA模型核((意味連続関係(),順序連続関係(),有向関係整合(),肯否整合関係(),履歴近接関係(),条件結合関係()),能力作用群=(参照関係寄与作用(),候補共同参照作用()))

__all__=["LLM成立規定リポジトリ","LLM成立規定参照コミット","LLM成立規定版","LLM成立意味区別","LLM構成再現区別","言語状態","内部言語状態","文脈付き言語状態","成立候補","関係寄与","成立差","模型Checkpoint","模型統計","模型結果","言語対応","模型関係","関係規則","意味連続関係","順序連続関係","有向関係整合","肯否整合関係","履歴近接関係","条件結合関係","参照関係寄与作用","候補共同参照作用","MINIDORA模型核","標準模型核"]

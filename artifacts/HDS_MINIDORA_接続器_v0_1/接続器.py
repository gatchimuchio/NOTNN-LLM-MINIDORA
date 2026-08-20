from __future__ import annotations
from dataclasses import dataclass
from pathlib import Path
from collections import Counter
import json,math,re,unicodedata

try:
    from minidora import 参照記録
except Exception:
    @dataclass(frozen=True, slots=True)
    class 参照記録:
        識別子:str; 対象:str; 内容:str; 由来:str; 供給器:str; 信頼:float=1.0

英日同義={
    'revenue':'売上高','revenues':'売上高','operating':'営業','income':'利益','profit':'利益',
    'headcount':'従業員数','employees':'従業員数','employee':'従業員数',
    'equity':'株主資本','stockholders':'株主資本','debt':'負債','margin':'利益率',
    'guidance':'ガイダンス','expenditure':'設備投資','expenditures':'設備投資','capex':'設備投資',
    'projects':'プロジェクト','project':'プロジェクト','adjusted':'adjusted','ebitda':'ebitda',
}
停止語={'the','a','an','of','for','to','in','on','as','and','or','was','were','is','are','be','their','they','this','that','what','which','who','how','has','have','had','with','from','at','by','it','if','no','yes','return','calculate','then','otherwise','your','using','use','between','compare','same','other','company','quarter','reported','value','values','nearest','round','rounded','answer','give','consider','following','description','where'}

def 正規語群(s:str)->list[str]:
    s=unicodedata.normalize('NFKC',str(s)).casefold().replace('adjusted ebitda','adjusted_ebitda')
    raw=re.findall(r'[a-z0-9_]+|[一-龥ぁ-んァ-ンー]+',s)
    out=[]
    for t in raw:
        if len(t)<=1 or t in 停止語: continue
        out.append(t); out.append(英日同義.get(t,t)) if t in 英日同義 else None
    return out

class 意味適合参照供給器:
    """HDS Rの存在ではなく、要求との意味適合が成立した記録だけ返す。"""
    名称='HDS意味適合参照供給器_v0.1'
    def __init__(self, 記録群, 最低得点:float=3.0, 最低被覆:float=0.18):
        self._記録群=tuple(記録群); self.最低得点=最低得点; self.最低被覆=最低被覆
        token_sets=[set(正規語群(f'{r.対象} {r.内容}')) for r in self._記録群]
        df=Counter(t for s in token_sets for t in s); n=max(1,len(token_sets))
        self._tokens=token_sets; self._idf={t:math.log((n+1)/(c+1))+1 for t,c in df.items()}
    @classmethod
    def JSONL読込(cls,経路,**kw):
        records=[]
        for line in Path(経路).read_text(encoding='utf-8').splitlines():
            if not line.strip(): continue
            d=json.loads(line)
            records.append(参照記録(str(d['識別子']),str(d['対象']),str(d['内容']),str(d['由来']),str(d['供給器']),float(d.get('信頼',1.0))))
        return cls(records,**kw)
    def 検索(self,問合せ:str,上限:int=8):
        q=set(正規語群(問合せ))
        if not q: return ()
        scored=[]
        # 企業名・固有略語は見つかる場合は強い拘束として扱う。
        proper={t for t in q if t in {'equinix','digital','realty','xscale','ffo','affo','adjusted_ebitda','nasdaq','nyse'}}
        for toks,r in zip(self._tokens,self._記録群):
            hit=q & toks
            if not hit: continue
            if proper and not (proper & toks): continue
            score=sum(self._idf.get(t,1.0) for t in hit)
            coverage=len(hit)/max(1,len(q))
            # 単一の一般語一致だけでは根拠扱いしない。
            if score < self.最低得点 or coverage < self.最低被覆: continue
            scored.append((score,coverage,r))
        scored.sort(key=lambda x:(-x[0],-x[1],x[2].識別子))
        return tuple(r for _,_,r in scored[:上限])

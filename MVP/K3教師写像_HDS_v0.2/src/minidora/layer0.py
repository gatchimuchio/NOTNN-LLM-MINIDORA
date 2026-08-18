from __future__ import annotations
from copy import deepcopy
from typing import Any
from .arithmetic import 計算

class Layer0:
    """日本語命令Pを解釈する最小実行器。K3固有機構を持たない。"""
    def 実行(self, 規則: dict | None, 要求, R, 予算: int = 32):
        if 規則 is None:
            return {"値":None,"参照":[],"履歴":[],"未解":["適用可能な命令Pなし"],"矛盾":[]}
        状態: dict[str, Any] = {"要求":要求,"予算":予算}
        参照=[]; 履歴=[]; 未解=[]; 矛盾=[]
        def resolve(v):
            if not isinstance(v,str) or not v.startswith("$"): return deepcopy(v)
            path=v[1:].split("."); cur: Any=状態
            for p in path:
                if p=="非空": return bool(cur)
                if hasattr(cur,p): cur=getattr(cur,p)
                elif isinstance(cur,dict): cur=cur.get(p)
                else: return None
            return deepcopy(cur)
        def apply(inst):
            nonlocal 状態,参照,履歴,未解,矛盾
            if len(inst)!=1: raise ValueError("命令は一作用")
            op,spec=next(iter(inst.items()))
            if op=="設定":
                value=resolve(spec["値"]); 状態[spec["先"]]=value; 履歴.append({"作用":op,"先":spec["先"],"結果":value}); return True
            if op=="先頭取得":
                seq=resolve(spec["源"])
                if not seq: 未解.append("先頭取得対象なし"); return False
                状態[spec["先"]]=seq[0]; 履歴.append({"作用":op,"先":spec["先"],"結果":seq[0]}); return True
            if op=="先頭削除":
                key=spec["源"].lstrip("$"); seq=list(状態.get(key,()))
                if seq: seq.pop(0)
                状態[key]=tuple(seq); 履歴.append({"作用":op,"先":key,"結果":tuple(seq)}); return True
            if op=="参照":
                主語=resolve(spec["主語"]); 関係=resolve(spec["関係"]); hits=R.問う(str(主語),str(関係)) if R is not None else ()
                状態[spec["先"]]=hits; 参照.extend(hits); 履歴.append({"作用":op,"主語":主語,"関係":関係,"件数":len(hits)})
                if not hits: 未解.append(f"{主語} -[{関係}]-> ?"); return False
                return True
            if op=="単値化":
                hits=resolve(spec["源"]) or (); values=tuple(dict.fromkeys(x["値"] for x in hits))
                if len(values)==0: 未解.append("参照値なし"); return False
                if len(values)>1: 矛盾.append(str(values)); return False
                状態[spec["先"]]=values[0]; 履歴.append({"作用":op,"先":spec["先"],"結果":values[0]}); return True
            if op=="計算":
                expr=resolve(spec["式"]); value=計算(str(expr)); 状態[spec["先"]]=value; 履歴.append({"作用":op,"先":spec["先"],"結果":value}); return True
            raise ValueError(f"未対応命令: {op}")
        for inst in 規則.get("初期",[]):
            if not apply(inst): break
        if not 未解 and not 矛盾 and "反復" in 規則:
            loop=規則["反復"]; count=0
            while resolve(loop["条件"]):
                count+=1
                if count>予算: 未解.append("計算予算超過"); break
                for inst in loop["手順"]:
                    if not apply(inst): break
                if 未解 or 矛盾: break
        if not 未解 and not 矛盾:
            for inst in 規則.get("手順",[]):
                if not apply(inst): break
        result=None if 未解 or 矛盾 else resolve(規則.get("結果"))
        return {"値":result,"参照":参照,"履歴":履歴,"未解":未解,"矛盾":矛盾}

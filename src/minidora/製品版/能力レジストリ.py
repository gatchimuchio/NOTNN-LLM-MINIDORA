from __future__ import annotations
from dataclasses import dataclass
from threading import RLock
from .能力契約 import 能力Module, 能力文脈

レジストリ版 = "capability-registry-v1"

@dataclass(frozen=True, slots=True)
class 能力選択:
    Module: 能力Module
    信頼: float
    候補: tuple[tuple[str, float], ...]

class 能力レジストリ:
    def __init__(self, modules: tuple[能力Module, ...] = ()) -> None:
        self._lock = RLock(); self._modules: dict[str, 能力Module] = {}
        for m in modules: self.登録(m)

    def 登録(self, module: 能力Module) -> None:
        name = str(module.名前).strip()
        if not name: raise ValueError("Module名が空")
        with self._lock:
            self._modules[name] = module

    def 解除(self, name: str) -> None:
        with self._lock: self._modules.pop(name, None)

    def 一覧(self) -> tuple[能力Module, ...]:
        with self._lock: return tuple(sorted(self._modules.values(), key=lambda m:(-int(m.優先度), m.名前)))

    def 選択(self, context: 能力文脈, min_score: float = 0.01) -> 能力選択 | None:
        scored: list[tuple[float,int,str,能力Module]]=[]
        for m in self.一覧():
            try: score=max(0.0,min(1.0,float(m.判定(context))))
            except Exception: score=0.0
            if score>=min_score: scored.append((score,int(m.優先度),m.名前,m))
        if not scored: return None
        scored.sort(key=lambda x:(x[0],x[1],x[2]), reverse=True)
        top=scored[0]
        return 能力選択(top[3],top[0],tuple((name,score) for score,_,name,_ in scored))

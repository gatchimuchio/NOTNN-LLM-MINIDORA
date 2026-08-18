from __future__ import annotations
from .schema import 意味要求, 応答

class ミニドラ:
    def __init__(self, layer0, P, R=None, surface=None):
        self.layer0=layer0; self.P=P; self.R=R; self.surface=surface
    def 意味で問う(self, 要求: 意味要求, 予算: int = 32) -> 応答:
        rule=self.P.選ぶ(要求.要求種); raw=self.layer0.実行(rule,要求,self.R,予算=予算)
        if raw["矛盾"]: 状態,理由="保留",("未解消矛盾",)
        elif raw["未解"]: 状態,理由="保留",("未解",)
        else: 状態,理由="合格",("計算成立",)
        rendered=self.surface.表出(raw["値"],要求.表出言語) if self.surface is not None else (None if raw["値"] is None else str(raw["値"]))
        return 応答(raw["値"],rendered,状態,理由,tuple(raw["参照"]),tuple(raw["履歴"]),tuple(raw["未解"]),tuple(raw["矛盾"]))
    def 問う(self,text:str,予算:int=32)->応答:
        if self.surface is None: return 応答(None,None,"保留",("表層Adapterなし",))
        try: req=self.surface.解析(text)
        except ValueError as e: return 応答(None,None,"保留",("表層意味写像不能",),未解=(str(e),))
        return self.意味で問う(req,予算=予算)

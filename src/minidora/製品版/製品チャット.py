from __future__ import annotations
from typing import Any
from .型 import 製品応答, 能力結果
from .監査 import 監査台帳
from .会話状態 import 会話状態庫
from .能力契約 import 能力文脈
from .能力レジストリ import 能力レジストリ, レジストリ版
from .ニュース import ニュースModule, RSSニュース供給器
from .要約 import 汎用要約Module
from .変換 import 文脈変換Module
from .抽出 import 情報抽出Module
from .計算 import 計算Module
from .基本会話 import 基本会話Module
from .知識 import 知識参照Module本体, Wikipedia知識供給器
from .組込モジュール import ニュース能力,要約能力,変換能力,抽出能力,計算能力,基本会話能力,知識参照能力,Core能力

製品チャット版="MINIDORA-PRODUCT-CHAT-v2"

class 製品ミニドラ:
    def __init__(self,*,基礎ミニドラ:Any=None,ニュース供給器=None,知識供給器=None,監査台帳_:監査台帳|None=None,状態庫:会話状態庫|None=None,追加Module:tuple=()) -> None:
        self.基礎ミニドラ=基礎ミニドラ; self.監査台帳=監査台帳_ or 監査台帳(); self.状態庫=状態庫 or 会話状態庫()
        news=ニュースModule(ニュース供給器 or RSSニュース供給器()); summary=汎用要約Module(); transform=文脈変換Module(); extract=情報抽出Module(); calc=計算Module(); basic=基本会話Module(); knowledge=知識参照Module本体(知識供給器 or Wikipedia知識供給器())
        builtin=(ニュース能力(news),要約能力(summary),変換能力(transform),抽出能力(extract),計算能力(calc),基本会話能力(basic),知識参照能力(knowledge),Core能力(self._core))
        self.能力レジストリ=能力レジストリ((*builtin,*追加Module))

    def 能力一覧(self)->tuple[str,...]: return tuple(m.名前 for m in self.能力レジストリ.一覧())+("完全経路監査",)
    def Module登録(self,module)->None: self.能力レジストリ.登録(module)
    def Module解除(self,name:str)->None: self.能力レジストリ.解除(name)

    def _core(self,text:str)->tuple[能力結果,dict[str,Any]]:
        if self.基礎ミニドラ is None: return 能力結果(False,"",保留理由="基礎MINIDORA Core未接続"),{}
        try:
            if hasattr(self.基礎ミニドラ,"実行"):
                try:
                    from minidora.runtime import 要求
                    r=self.基礎ミニドラ.実行(要求(text)); value=getattr(r,"値",None); refs=getattr(r,"参照",()) or (); hist=getattr(r,"履歴",()) or (); state=getattr(getattr(r,"採否",None),"状態",None); status=getattr(state,"value",str(state or "")); trace={"値":value,"採否":status,"参照数":len(refs),"履歴":hist,"言語計画":getattr(r,"言語計画",None),"HDS_IR":repr(getattr(r,"HDS_IR",None))}
                    if value is not None: return 能力結果(True,str(value),根拠=("MINIDORA Core実行結果",),データ=trace),trace
                except Exception: pass
            response=str(self.基礎ミニドラ.応答(text)); trace={"追跡範囲":"公開応答境界"}; return 能力結果(True,response,根拠=("MINIDORA Core応答",),データ=trace),trace
        except Exception as exc: return 能力結果(False,"",保留理由=f"Core実行失敗:{type(exc).__name__}"),{"例外":type(exc).__name__}

    def 応答(self,入力文:str,*,セッションID:str="default")->製品応答:
        with self.状態庫.排他(セッションID) as st:
            return self._応答_locked(str(入力文 or "").strip(), st)

    def _応答_locked(self,text,st)->製品応答:
        audit=self.監査台帳.開始(text,st.セッションID,st.直前監査ハッシュ)
        audit.記録("入力受理","製品チャット",製品チャット版,{"入力":text,"session":st.セッションID},{"履歴件数":len(st.履歴),"直前経路":st.直前経路})
        context=能力文脈(text,st.セッションID,st.直前応答,st.直前参照,tuple(st.履歴),{})
        selected=self.能力レジストリ.選択(context)
        if selected is None:
            route="保留"; result=能力結果(False,"",保留理由="利用可能Moduleなし"); candidates=()
        else:
            route=selected.Module.名前; candidates=selected.候補
            audit.経路設定(route); audit.記録("能力選択","能力レジストリ",レジストリ版,text,{"選択":route,"信頼":selected.信頼,"候補":candidates})
            try: result=selected.Module.実行(context)
            except Exception as exc: result=能力結果(False,"",保留理由=f"Module実行失敗:{type(exc).__name__}")
            audit.記録("能力実行",selected.Module.名前,selected.Module.版,text,{"成立":result.成立,"本文":result.本文,"保留理由":result.保留理由,"データ":result.データ},tuple(result.根拠))
            if not result.成立 and route!="基礎Core" and self.基礎ミニドラ is not None:
                audit.記録("Module透過","能力レジストリ",レジストリ版,{"不成立Module":route,"理由":result.保留理由},{"次経路":"基礎Core"})
                route=f"{route}→基礎Core"; result,_=self._core(text)
                audit.記録("能力実行","基礎Core","repository-current",text,{"成立":result.成立,"本文":result.本文,"保留理由":result.保留理由,"データ":result.データ},tuple(result.根拠))
        audit.経路設定(route)
        status="合格" if result.成立 else "保留"; body=result.本文 if result.成立 else f"回答を確定できませんでした。{result.保留理由}"
        audit.記録("応答構成","製品チャット",製品チャット版,{"能力結果":result.成立},{"本文":body,"状態":status})
        st.追加("user",text); st.追加("assistant",body); st.直前応答=body; st.直前参照=result.参照 if result.成立 else (); st.直前経路=route
        audit.記録("会話状態更新","会話状態庫","conversation-state-v1",{"履歴追加":2},{"履歴件数":len(st.履歴),"参照件数":len(st.直前参照)})
        record=audit.確定(body,status); st.直前追跡ID=record.追跡ID; st.直前監査ハッシュ=record.ルートハッシュ
        return 製品応答(st.セッションID,body,status,route,record.追跡ID,record.ルートハッシュ,result.参照,(route,),{"capability_candidates":candidates})

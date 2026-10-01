from __future__ import annotations
import unittest
from minidora.HDS実行主体 import HDS実行主体, HDS実行状態, HDS作用供給器, HDS関数作用, HDS作用結果, HDS作用状態, HDS終端

class 汎用評価取得循環試験(unittest.TestCase):
    def test_現在材料で閉じるなら取得を起動しない(self):
        履歴=[]
        def 供給(状態):
            成果=状態.成果辞書(); actions=[]
            if not 成果.get("評価済み"):
                actions.append(HDS関数作用("評価",lambda _s:(履歴.append("評価") or HDS作用結果(HDS作用状態.成立,追加状態=frozenset({"回答完了"}),解消残差=frozenset({"未評価"}),成果=(("評価済み",True),))),出力状態=("回答完了",),解消対象=("未評価",),優先度=1))
            actions.append(HDS関数作用("取得",lambda _s:(履歴.append("取得") or HDS作用結果(HDS作用状態.成立,成果=(("資料","追加"),))),優先度=100,目的依存=("残差:観測不足",)))
            return tuple(actions)
        r=HDS実行主体((),作用供給器=(HDS作用供給器("汎用供給",供給),),最大作用回数=8).実行(HDS実行状態(目的=("回答する",),要求状態=frozenset({"回答完了"}),残差=frozenset({"未評価"})))
        self.assertEqual(r.終端,HDS終端.採用,r.理由); self.assertEqual(履歴,["評価"])

    def test_不足した時だけ取得して再評価する(self):
        履歴=[]
        def 供給(状態):
            成果=状態.成果辞書(); actions=[]; signature=str(成果.get("資料","なし"))
            if 成果.get("評価署名")!=signature:
                def 評価(_s,signature=signature):
                    履歴.append("評価")
                    if signature=="なし": return HDS作用結果(HDS作用状態.成立,解消残差=frozenset({"未評価"}),追加残差=frozenset({"観測不足"}),成果=(("評価署名",signature),))
                    return HDS作用結果(HDS作用状態.成立,追加状態=frozenset({"回答完了"}),解消残差=frozenset({"観測不足"}),成果=(("評価署名",signature),))
                actions.append(HDS関数作用("評価",評価,出力状態=("回答完了",),解消対象=("未評価","観測不足"),優先度=1,入力署名=lambda _s,signature=signature:signature))
            if "観測不足" in 状態.残差 and "資料" not in 成果:
                actions.append(HDS関数作用("取得",lambda _s:(履歴.append("取得") or HDS作用結果(HDS作用状態.成立,成果=(("資料","取得済み"),))),目的依存=("残差:観測不足",),優先度=100))
            return tuple(actions)
        r=HDS実行主体((),作用供給器=(HDS作用供給器("汎用供給",供給),),最大作用回数=8).実行(HDS実行状態(目的=("回答する",),要求状態=frozenset({"回答完了"}),残差=frozenset({"未評価"})))
        self.assertEqual(r.終端,HDS終端.採用,r.理由); self.assertEqual(履歴,["評価","取得","評価"])

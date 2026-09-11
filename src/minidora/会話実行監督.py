"""目的を維持し、観測した失敗に関係する作用だけを再計画する同期監督。"""
from __future__ import annotations
from dataclasses import asdict,dataclass
from copy import deepcopy
from .能力合成 import _結果辞書
from .実行回復 import 失敗を分類
from .会話意味 import 意味指紋


@dataclass(frozen=True, slots=True)
class 失敗署名:
    種別: str
    目的印: str
    工程: str
    作用: str
    入力印: str
    理由: str
    再開放: tuple[str,str] | None = None
    分類: str = '未分類'
    発生目的: str = ''
    回復契約: str = ''


@dataclass(frozen=True, slots=True)
class 監督結果:
    応答: object
    失敗: tuple[失敗署名,...]
    試行: tuple[dict,...]


class 会話実行監督:
    def __init__(self, 計画器, 統合, *, 最大試行=12):
        if type(最大試行) is not int or not 1<=最大試行<=16: raise ValueError('監督試行上限')
        self.計画器,self.統合,self.最大試行=計画器,統合,最大試行

    def _署名(self, plan, response):
        run=response.実行
        if run is None or not run.履歴:
            return 失敗署名('停止' if response.状態=='中止' else '実行環境',plan.目的印,'','','',response.理由,
                            分類='停止' if response.状態=='中止' else '実行環境')
        last=run.履歴[-1]
        kinds=last.理由.split(':',2)
        kind=('停止' if response.状態=='中止' else
              '実行環境' if last.状態=='失敗' else
              kinds[1] if len(kinds)==3 and kinds[0]=='会話失敗' else '能力不成立')
        info={sid:(key,action) for sid,key,action in plan.工程作用}
        if last.工程 not in info:
            return 失敗署名('実行環境',plan.目的印,last.工程,'',last.入力ハッシュ,
                            '実行履歴と計画の対応欠落',分類='実行環境')
        key,action=info[last.工程]; reopen=None; policy=''
        rule=next(r for r in self.計画器.作用 if r.識別子==action)
        for recovery in rule.回復:
            if kind!=recovery.失敗種別: continue
            if recovery.対象=='自己':
                reopen=(key,action)
            else:
                roles=dict(dict(plan.入力役割).get(last.工程,()))
                parent=roles.get(recovery.入力役割)
                if parent is not None and parent.領域=='工程' and parent.識別子 in info:
                    pair=info[parent.識別子]
                    if pair[1] in recovery.対象作用: reopen=pair
            if reopen is not None: policy=action+':'+recovery.失敗種別+':'+recovery.対象
        return 失敗署名(kind,plan.目的印,last.工程,action,last.入力ハッシュ,last.理由,
                        reopen,失敗を分類(kind),key,policy)

    def 実行(self, goal, materials, *, 原文, 外部許可=False, 停止要求=None, 要求起点=None):
        # 呼出元が可変Dataを後から変更しても、目的・資料・契約を途中で差し替えない。
        fixed_goal=deepcopy(goal); fixed_materials=deepcopy(materials)
        goal_seal=fixed_goal.鍵()
        material_seal=意味指紋({k:_結果辞書(v) for k,v in fixed_materials.items()})
        rules=self.計画器.作用
        start=self.統合.起点()
        if 要求起点 is not None and start!=要求起点: raise ValueError("解釈中に会話状態が変わった")
        failures=[]; attempts=[]; banned=[]; seen=set(); response=None
        for _ in range(self.最大試行):
            self.統合._停止(停止要求)
            if start!=self.統合.起点(): raise ValueError('再計画中に採用状態が変わった')
            if 意味指紋(list(self.統合.能力一覧()))!=self.計画器.登録印:
                raise ValueError('作用能力の版・登録が変わった')
            if self.計画器.作用!=rules: raise ValueError('回復中に作用契約が変わった')
            if (fixed_goal.鍵()!=goal_seal or
                    意味指紋({k:_結果辞書(v) for k,v in fixed_materials.items()})!=material_seal):
                raise ValueError('回復中に目的又は資料が変わった')
            try:
                plan=self.計画器.計画する(fixed_goal,fixed_materials,禁止=tuple(banned),外部許可=外部許可)
            except ValueError as exc:
                if response is None: raise
                attempts.append({'状態':'計画保留','理由':str(exc),'目的印':goal_seal,
                                 '素材印':material_seal,'外部工程':()})
                break
            if plan.目的印!=goal_seal: raise ValueError('再計画が目的を変更した')
            packed=self.統合.準備(plan.計画,plan.Data,依頼文=原文)
            if packed.起点!=start: raise ValueError('計画準備中に起点が変わった')
            response=self.統合.実行(packed,外部読取許可=外部許可,停止要求=停止要求)
            attempts.append({'計画印':packed.ハッシュ,'素材印':material_seal,'目的印':plan.目的印,'工程作用':plan.工程作用,
                '状態':response.状態,'外部工程':plan.外部作用,
                '実行印':response.実行.ルートハッシュ if response.実行 else '',
                # 失敗した取得も診断記録として残す。採用した資料とは別。
                '取得報告':[v.データ for _,v in response.実行.中間結果
                    if v.データ.get('種別')=='取得報告'] if response.実行 else []})
            if response.成立: return 監督結果(response,tuple(failures),tuple(attempts))
            if self.統合.起点()!=start: raise ValueError('失敗した試行が採用状態を変更した')
            signature=self._署名(plan,response);failures.append(signature)
            seal=意味指紋({'目的':signature.発生目的,'作用':signature.作用,
                          '入力':signature.入力印,'種別':signature.種別})
            if seal in seen or signature.再開放 is None: break
            seen.add(seal)
            if signature.再開放 in banned: break
            banned.append(signature.再開放)
        return 監督結果(response,tuple(failures),tuple(attempts))

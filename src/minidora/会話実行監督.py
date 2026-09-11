"""目的を維持し、観測した失敗に関係する作用だけを再計画する同期監督。"""
from __future__ import annotations
from dataclasses import asdict,dataclass
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


@dataclass(frozen=True, slots=True)
class 監督結果:
    応答: object
    失敗: tuple[失敗署名,...]
    試行: tuple[dict,...]


class 会話実行監督:
    def __init__(self, 計画器, 統合, *, 最大試行=4):
        if type(最大試行) is not int or not 1<=最大試行<=8: raise ValueError('監督試行上限')
        self.計画器,self.統合,self.最大試行=計画器,統合,最大試行

    def _署名(self, plan, response):
        run=response.実行
        if run is None or not run.履歴:
            return 失敗署名('実行環境',plan.目的印,'','','',response.理由)
        last=run.履歴[-1]
        kinds=last.理由.split(':',2)
        kind=kinds[1] if len(kinds)==3 and kinds[0]=='会話失敗' else ('停止' if response.状態=='中止' else '能力不成立')
        info={sid:(key,action) for sid,key,action in plan.工程作用}
        key,action=info[last.工程]; reopen=None
        if kind=='構造未到達' and action=='直下数量選択':
            reopen=(key,action)
        elif kind=='取得不足' and action=='取得成立採用':
            step=next(s for s in plan.計画.工程 if s.識別子==last.工程)
            parents=[info[x.識別子] for x in step.入力 if x.領域=='工程']
            if len(parents)==1 and parents[0][1]=='主題取得': reopen=parents[0]
        return 失敗署名(kind,plan.目的印,last.工程,action,last.入力ハッシュ,last.理由,reopen)

    def 実行(self, goal, materials, *, 原文, 外部許可=False, 停止要求=None, 要求起点=None):
        start=self.統合.起点()
        if 要求起点 is not None and start!=要求起点: raise ValueError("解釈中に会話状態が変わった")
        failures=[]; attempts=[]; banned=[]; seen=set(); response=None
        for _ in range(self.最大試行):
            self.統合._停止(停止要求)
            if start!=self.統合.起点(): raise ValueError('再計画中に採用状態が変わった')
            if 意味指紋(list(self.統合.能力一覧()))!=self.計画器.登録印:
                raise ValueError('作用能力の版・登録が変わった')
            plan=self.計画器.計画する(goal,materials,禁止=tuple(banned),外部許可=外部許可)
            if plan.目的印!=goal.鍵(): raise ValueError('再計画が目的を変更した')
            packed=self.統合.準備(plan.計画,plan.Data,依頼文=原文)
            if packed.起点!=start: raise ValueError('計画準備中に起点が変わった')
            response=self.統合.実行(packed,外部読取許可=外部許可,停止要求=停止要求)
            attempts.append({'計画印':packed.ハッシュ,'目的印':plan.目的印,'工程作用':plan.工程作用,
                '状態':response.状態,'外部工程':plan.外部作用,
                '実行印':response.実行.ルートハッシュ if response.実行 else '',
                # 失敗した取得も診断記録として残す。採用した資料とは別。
                '取得報告':[v.データ for _,v in response.実行.中間結果
                    if v.データ.get('種別')=='取得報告'] if response.実行 else []})
            if response.成立: return 監督結果(response,tuple(failures),tuple(attempts))
            if self.統合.起点()!=start: raise ValueError('失敗した試行が採用状態を変更した')
            signature=self._署名(plan,response);failures.append(signature)
            seal=意味指紋(asdict(signature))
            if seal in seen or signature.再開放 is None: break
            seen.add(seal)
            if signature.再開放 in banned: break
            banned.append(signature.再開放)
        return 監督結果(response,tuple(failures),tuple(attempts))

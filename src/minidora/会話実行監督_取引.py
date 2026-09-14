"""Core実行Transaction v1を既存会話監督v0.2へ重ねる派生監督。"""
from __future__ import annotations
from copy import deepcopy

from .能力合成 import _結果辞書
from .実行トランザクション import (
    実行トランザクション台帳, 台帳を更新, 台帳を失効, 再開投影を作る,
)
from .会話意味 import 意味指紋
from .会話実行監督_基底 import (
    会話実行監督 as _基底監督, 監督結果, _被覆地図, _被覆子孫,
)

def _被覆祖先(plan, target: str) -> set[str]:
    """targetの結果に依存する上位目的を含め、再実行が必要な経路を返す。"""
    by_key = _被覆地図(plan)
    if target not in by_key:
        raise ValueError('回復対象目的が要求被覆にない')
    parents = {key: set() for key in by_key}
    for key, row in by_key.items():
        if getattr(row, '解決', '') != '作用':
            continue
        for pair in getattr(row, '入力役割', ()):
            if type(pair) is not tuple or len(pair) != 2 or pair[1] not in by_key:
                raise ValueError('作用被覆の子目的が閉じていない')
            parents[pair[1]].add(key)
    seen = set()
    stack = [target]
    while stack:
        key = stack.pop()
        if key in seen:
            continue
        seen.add(key)
        stack.extend(parents[key])
    return seen


class 会話実行監督(_基底監督):
    def 実行(self, goal, materials, *, 原文, 外部許可=False, 停止要求=None, 要求起点=None):
        fixed_goal=deepcopy(goal); fixed_materials=deepcopy(materials)
        goal_seal=fixed_goal.鍵()
        material_seal=意味指紋({k:_結果辞書(v) for k,v in fixed_materials.items()})
        rules=self.計画器.作用
        static_contract=getattr(self.計画器,'契約印','')
        if type(static_contract) is not str or not static_contract:
            raise ValueError('作用契約印がない')
        recovery_contract=self._回復契約印()
        if type(recovery_contract) is not str or not recovery_contract:
            raise ValueError('回復方針契約印がない')
        start=self.統合.起点()
        if 要求起点 is not None and start!=要求起点: raise ValueError("解釈中に会話状態が変わった")
        transaction_seal=意味指紋({
            '目的印':goal_seal,'素材印':material_seal,'起点':start,
            '作用契約印':static_contract,'回復方針契約印':recovery_contract,
            '登録印':self.計画器.登録印,'外部許可':外部許可,
        })
        ledger=実行トランザクション台帳(transaction_seal)
        failures=[]; attempts=[]; banned=[]; seen=set(); observed_contracts={}; response=None
        retries={}; pending=None; previous_plan=None
        for _ in range(self.最大試行):
            self.統合._停止(停止要求)
            if start!=self.統合.起点(): raise ValueError('再計画中に採用状態が変わった')
            if 意味指紋(list(self.統合.能力一覧()))!=self.計画器.登録印:
                raise ValueError('作用能力の版・登録が変わった')
            if self.計画器.作用!=rules or getattr(self.計画器,'契約印','')!=static_contract:
                raise ValueError('回復中に作用契約が変わった')
            if self._回復契約印()!=recovery_contract:
                raise ValueError('回復中に回復方針契約が変わった')
            if (fixed_goal.鍵()!=goal_seal or
                    意味指紋({k:_結果辞書(v) for k,v in fixed_materials.items()})!=material_seal):
                raise ValueError('回復中に目的又は資料が変わった')
            try:
                if pending is not None and pending.動作=='同一作用再試行':
                    plan=deepcopy(previous_plan)
                else:
                    plan=self.計画器.計画する(fixed_goal,fixed_materials,禁止=tuple(banned),外部許可=外部許可)
            except ValueError as exc:
                if response is None: raise
                attempts.append({'状態':'計画保留','理由':str(exc),'目的印':goal_seal,
                                 '素材印':material_seal,'外部工程':(),'作用契約印':'','回復方針契約印':recovery_contract,'要求被覆印':'',
                                 '回復方針':pending.動作 if pending else '初回','再開放':()})
                break
            if plan.目的印!=goal_seal: raise ValueError('再計画が目的を変更した')
            if (type(plan.要求被覆) is not tuple or not plan.要求被覆
                    or goal_seal not in {x.目的鍵 for x in plan.要求被覆}
                    or type(plan.作用契約印) is not str or not plan.作用契約印):
                raise ValueError('再計画の要求被覆又は作用契約が閉じていない')
            coverage_seal=意味指紋(tuple((x.目的鍵,x.種別,x.解決,x.作用,x.素材,x.入力役割,x.契約印)
                                        for x in plan.要求被覆))
            # 同じ目的・同じ作用の役割/設定契約を横滑りさせない。
            # 既存v2の監査を先に維持し、その後で作用選択まで含む局所範囲を締める。
            for item in plan.要求被覆:
                if item.解決!='作用': continue
                pair=(item.目的鍵,item.作用)
                previous=observed_contracts.get(pair)
                if previous is not None and previous!=item.契約印:
                    raise ValueError('再計画で既存作用契約が変わった')
                observed_contracts[pair]=item.契約印
            fixed_coverage=0
            rerun_goals=set()
            if pending is not None and previous_plan is not None:
                fixed_coverage=self._局所再計画監査(previous_plan,plan,pending)
                if pending.対象目的:
                    rerun_goals.update(_被覆祖先(plan,pending.対象目的))
                    if pending.動作!='同一作用再試行':
                        rerun_goals.update(_被覆子孫(plan,pending.対象目的))
            if rerun_goals:
                ledger=台帳を失効(ledger,rerun_goals)
            projection=再開投影を作る(ledger,plan,再実行目的=rerun_goals)
            packed=self.統合.準備(projection.計画,projection.Data,依頼文=原文)
            if packed.起点!=start: raise ValueError('計画準備中に起点が変わった')
            response=self.統合.実行(packed,外部読取許可=外部許可,停止要求=停止要求)
            actual_ids={step.識別子 for step in projection.計画.工程}
            actual_external=tuple(x for x in plan.外部作用 if x in actual_ids)
            attempts.append({'計画印':packed.ハッシュ,'素材印':material_seal,'目的印':plan.目的印,'工程作用':plan.工程作用,
                '状態':response.状態,'外部工程':actual_external,'作用契約印':plan.作用契約印,
                '回復方針契約印':recovery_contract,'要求被覆印':coverage_seal,'要求被覆数':len(plan.要求被覆),
                '回復方針':pending.動作 if pending else '初回',
                '再開放':(pending.対象目的,pending.対象作用) if pending else (),
                '固定被覆数':fixed_coverage,'トランザクション印':transaction_seal,
                '再実行目的':tuple(sorted(rerun_goals)),
                '再開印':projection.再開印,'再開固定工程':projection.固定工程,
                '再開固定目的':projection.固定目的,'外部固定工程':projection.外部固定工程,
                '実行印':response.実行.ルートハッシュ if response.実行 else '',
                '取得報告':[v.データ for _,v in response.実行.中間結果
                    if v.データ.get('種別')=='取得報告'] if response.実行 else []})
            if response.成立: return 監督結果(response,tuple(failures),tuple(attempts))
            if self.統合.起点()!=start: raise ValueError('失敗した試行が採用状態を変更した')
            ledger=台帳を更新(ledger,plan,response)
            signature,policy=self._署名(plan,response,retries);failures.append(signature)
            if not policy.自動実行:
                break
            if policy.動作=='同一作用再試行':
                retry_key=(signature.発生目的,signature.作用,signature.種別)
                retries[retry_key]=policy.再試行番号
            else:
                seal=意味指紋({'目的':signature.発生目的,'作用':signature.作用,
                              '入力':signature.入力印,'種別':signature.種別,'方針':policy.動作,
                              '対象':(policy.対象目的,policy.対象作用)})
                if seal in seen or any(pair in banned for pair in policy.禁止): break
                seen.add(seal)
                banned.extend(policy.禁止)
            previous_plan=plan; pending=policy
        return 監督結果(response,tuple(failures),tuple(attempts))

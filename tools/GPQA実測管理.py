"""全数・部分測定を同じ期限で管理する。得点のために推論器は変更しない。

正解は親プロセスだけに保持し、推論ワーカーへ渡さない。
直列では同一ワーカー・同一Coreを維持する。独立測定は一問ごとに新プロセス。
"""
from __future__ import annotations
import argparse
from dataclasses import asdict,is_dataclass
from enum import Enum
import importlib
import json
import math
import multiprocessing as mp
import os
from pathlib import Path
import queue
import signal
import tempfile
import time
import traceback
import uuid

全数 = 198
時間上限秒 = 90 * 60
性能継承下限 = 43
資料SHA256 = "41d1213cd7a4998605a26c2798500652572007161b3a92817ba46b35befcd305"


def JSON値(値):
    if 値 is None or type(値) in (str,int,float,bool):return 値
    if isinstance(値,Enum):return 値.value
    if is_dataclass(値):return JSON値(asdict(値))
    if isinstance(値,dict):return {str(k):JSON値(v) for k,v in 値.items()}
    if isinstance(値,(tuple,list,set,frozenset)):return [JSON値(x) for x in 値]
    return {"型":type(値).__name__,"表現":repr(値)}


def 原子的保存(経路,値):
    経路=Path(経路);経路.parent.mkdir(parents=True,exist_ok=True)
    仮=経路.with_name(経路.name+".tmp")
    with 仮.open("w",encoding="utf-8") as f:
        json.dump(JSON値(値),f,ensure_ascii=False,indent=2,allow_nan=False);f.write("\n");f.flush();os.fsync(f.fileno())
    仮.replace(経路)


def _読込先(名称):
    単位,name=名称.split(":",1)
    return getattr(importlib.import_module(単位),name)


class _現行中核:
    def __init__(self):
        try:
            from . import 中核正本評価 as 実装
        except ImportError:
            import 中核正本評価 as 実装
        self.実装=実装
        self.構文化器=実装.公開HDSコンパイラ()
        期限 = os.getenv("GPQA_DEADLINE_EPOCH", "")
        停止 = (lambda: time.time() >= float(期限)) if 期限 else None
        self.中核=実装.HDS駆動コア(HDSコンパイラ=self.構文化器,最大作用回数=40,停止要求=停止)

    def __call__(self,番号,問題,選択肢,記録):
        行 = self.実装._一問を実行(番号,問題,tuple(選択肢),"",構文化器=self.構文化器,中核=self.中核,記録=記録)
        # 子側で採点欄を外してから親へ渡す。正解は親だけが保持する。
        for 鍵 in ("正解ラベル", "正答", "初期正答"):
            行.pop(鍵, None)
        保存先 = getattr(self, "復元点出力", None)
        if 保存先 is not None:
            開始 = time.monotonic()
            try:
                版 = self.実装._リポジトリ版()
                保存署名 = self.中核.継続状態を保存(保存先, リポジトリ版=版, 完了問題番号=番号)
                行["継続復元点"] = {"保存": True, "完了問題番号": 番号, "内容SHA256": 保存署名,
                    "ファイル": str(保存先), "リポジトリ版": 版}
            except Exception as exc:
                行["継続復元点"] = {"保存": False, "完了問題番号": 番号,
                    "理由": type(exc).__name__ + ": " + str(exc)}
            行["復元点保存秒"] = time.monotonic() - 開始
        return 行


def _ワーカー(宛先,問題群,実行器名,復元点ディレクトリ=None,共通締切epoch=None):
    if os.name=="posix":os.setsid()
    try:
        if 共通締切epoch is not None:
            os.environ["GPQA_DEADLINE_EPOCH"] = str(共通締切epoch)
        実行器=_読込先(実行器名)()
        if isinstance(実行器, _現行中核) and 復元点ディレクトリ is not None:
            実行器.復元点出力 = Path(復元点ディレクトリ) / (str(os.getpid()) + ".json")
        for 番号,問題,選択肢 in 問題群:
            def 記録(工程,番号=番号):宛先.put(("工程",番号,str(工程),time.time()))
            記録("開始");開始=time.monotonic()
            行=実行器(番号,問題,選択肢,記録)
            if not isinstance(行,dict) or 行.get("番号")!=番号:raise ValueError("実行結果の問題ID不一致")
            # 既存採点欄はここでは空gold由来。親の正解で採点し直す。
            for 鍵 in ("正解ラベル","正答","初期正答"):行.pop(鍵,None)
            行["問題実時間秒"]=time.monotonic()-開始
            宛先.put(("結果",番号,JSON値(行),time.time()))
        宛先.put(("完了",None,None,time.time()))
    except BaseException as exc:
        宛先.put(("例外",locals().get("番号"),type(exc).__name__+": "+str(exc),time.time()))
    finally:
        宛先.close();宛先.join_thread()


def _停止(過程):
    # 親が終了済みでも専用プロセス群の子孫を残さない。
    if os.name == "posix":
        try:
            os.killpg(過程.pid, signal.SIGTERM)
        except (ProcessLookupError, PermissionError):
            if 過程.is_alive():
                過程.terminate()
    elif 過程.is_alive():
        過程.terminate()
    過程.join(timeout=0.5)
    if os.name == "posix":
        try:
            os.killpg(過程.pid, signal.SIGKILL)
        except (ProcessLookupError, PermissionError):
            if 過程.is_alive():
                過程.kill()
    elif 過程.is_alive():
        過程.kill()
    過程.join(timeout=0.5)


def _実行を管理(問題群,出力,*,方式,条件,期限秒,並列数=1,実行器名=None,時計開始=None,復元点ディレクトリ=None):
    """期限秒は内部試験用。正本CLIは5400秒以外を受け付けない。"""
    if 方式 not in ("直列","並列"):raise ValueError("未知の実行方式")
    if type(並列数) is not int or not 1<=並列数<=40:raise ValueError("並列数は1..40")
    if not math.isfinite(期限秒) or 期限秒<0:raise ValueError("期限が不正")
    番号群=[x[0] for x in 問題群]
    if len(set(番号群))!=len(番号群):raise ValueError("問題ID重複")
    正解={番号:gold for 番号,q,c,gold in 問題群}
    if any(g not in ('A','B','C','D') for g in 正解.values()):raise ValueError("正解ラベル形式不正")
    問い={番号:(番号,q,tuple(c)) for 番号,q,c,g in 問題群}
    独立=方式=="並列";上限=並列数 if 独立 else 1
    未投入=list(番号群);行群={};進行={};失敗=[];過程群={};完了受信=set()
    文脈=mp.get_context('spawn');開始=time.monotonic();始時=time.time() if 時計開始 is None else 時計開始
    締切=開始+期限秒;実行器名=実行器名 or __name__+":_現行中核"
    測定ID=uuid.uuid4().hex;経路=Path(出力)
    def 保存(状態):
        経過=max(0,time.time()-始時)
        xs=[行群[i] for i in sorted(行群)]
        正答=sum(bool(x['正答']) for x in xs);回答=sum(bool(x['回答済み']) for x in xs)
        完走=not 失敗 and len(xs)==len(番号群) and all(x.get('問題束形成回数')==1 for x in xs)
        全数完走=完走 and sorted(番号群)==list(range(全数))
        時間内=経過<=時間上限秒 and 状態!='時間超過'
        受入=全数完走 and 時間内 and (not 独立 or 正答>=性能継承下限)
        値={"契約形式":"minidora.gpqa.measured-run.v4","測定ID":測定ID,"測定状態":状態,
            "評価条件":{**条件,"実行方式":"問題独立並列" if 独立 else "同一Core直列",
                "問題間継続状態":not 独立,"選択番号群":番号群,"全数wall_clock上限分":90,
                "実並列数":上限,"採点結果の学習利用":False},
            "実測": {"開始epoch":始時,"終了epoch":time.time() if 状態!='実行中' else None,"経過秒":経過,
                     "完走":完走,"全数完走":全数完走,"正本採用可":受入},
            "指標":{"全数":全数,"完了数":len(xs),"正答":正答,"回答":回答,"保留":len(xs)-回答,
                     "未完了":len(番号群)-len(xs),"初期継承正答":sum(bool(x['初期正答']) for x in xs)},
            "性能継承成立":(受入 if 独立 else None),"個票":xs,"実行中":list(進行.values()),"処理失敗":失敗}
        原子的保存(経路,値);return 値
    保存('実行中')
    try:
        while 未投入 or 過程群:
            if time.monotonic()>=締切:break
            while 未投入 and len(過程群)<上限:
                ids=[未投入.pop(0)] if 独立 else list(未投入)
                if not 独立:未投入.clear()
                q=文脈.Queue();p=文脈.Process(target=_ワーカー,args=(q,[問い[i] for i in ids],実行器名,復元点ディレクトリ,time.time()+max(0,締切-time.monotonic())));p.start();過程群[p.pid]=(p,q,ids)
            for pid,(p,q,ids) in list(過程群.items()):
                while True:
                    try:種類,番号,値,時点=q.get_nowait()
                    except queue.Empty:break
                    if 種類=='工程':
                        進行[pid]={"番号":番号,"工程":値,"観測epoch":時点}
                    elif 種類=='結果':
                        if 番号 in 行群 or 番号 not in ids:raise ValueError('結果ID重複または担当外')
                        pred=値.get('予測ラベル');answered=値.get('回答済み') is True
                        if answered!=(pred in ('A','B','C','D')):raise ValueError('回答形式不一致')
                        if answered and 値.get('終端')!='COMMIT':raise ValueError('未採用回答の混入')
                        値['正解ラベル']=正解[番号];値['正答']=answered and pred==正解[番号]
                        値['初期正答']=bool(値.get('初期回答済み')) and 値.get('初期予測ラベル')==正解[番号]
                        行群[番号]=値;進行.pop(pid,None)
                        print(f"CASE {番号+1:03d}/198 terminal={値.get('終端')} pred={pred} correct={値['正答']}",flush=True)
                    elif 種類=='例外':
                        失敗.append({'番号':番号,'理由':値});完了受信.add(pid)
                    elif 種類=='完了':完了受信.add(pid)
                    保存('実行中')
                if pid in 完了受信 or not p.is_alive():
                    p.join(timeout=0.1)
                    # 子はQueueのflushを完了してから終了する。未配達があれば次の周回で回収。
                    if not p.is_alive() and pid not in 完了受信:
                        try:msg=q.get(timeout=0.02)
                        except queue.Empty:
                            失敗.append({'番号群':ids,'理由':'ワーカー異常終了:'+str(p.exitcode)});完了受信.add(pid)
                        else:q.put(msg);continue
                    if pid in 完了受信:
                        _停止(p);q.close();q.join_thread();過程群.pop(pid);進行.pop(pid,None)
            if 過程群:time.sleep(min(0.01,max(0,締切-time.monotonic())))
        状態='時間超過' if 未投入 or 過程群 else ('処理失敗' if 失敗 else '完了')
    except BaseException as exc:
        失敗.append({'理由':type(exc).__name__+': '+str(exc)});状態='処理失敗'
    finally:
        for p,q,ids in 過程群.values():
            _停止(p);q.close();q.cancel_join_thread()
    結果=保存(状態)
    return 結果


def _資料読込(宛先):
    if os.name=='posix':os.setsid()
    try:
        try:from .GPQA現行測定 import _download_dataset,_load_cases
        except ImportError:from GPQA現行測定 import _download_dataset,_load_cases
        with tempfile.TemporaryDirectory(prefix='minidora-gpqa-') as d:
            p,z,h=_download_dataset(Path(d));cases=_load_cases(p)
        if len(cases)!=全数 or h!=資料SHA256:raise ValueError('GPQA資料集合不一致')
        宛先.put(('成功',cases,z))
    except BaseException as exc:宛先.put(('失敗',type(exc).__name__+': '+str(exc),None))
    finally:宛先.close();宛先.join_thread()


def GPQAを測定(出力,*,方式,開始番号=0,件数=198,期限epoch=None,並列数=1,共通開始epoch=None):
    今=time.time();起点=今 if 共通開始epoch is None else float(共通開始epoch)
    締切=今+時間上限秒 if 期限epoch is None else float(期限epoch)
    if not all(math.isfinite(x) for x in (起点,締切)) or 締切>起点+時間上限秒+0.001 or 起点>今+1:
        raise ValueError('90分境界の延長は許可しない')
    if 方式=='直列' and (開始番号!=0 or 件数!=198):raise ValueError('直列正本は全198問')
    if 開始番号<0 or 件数<=0 or 開始番号+件数>198:raise ValueError('問題範囲不正')
    c=mp.get_context('spawn');q=c.Queue();p=c.Process(target=_資料読込,args=(q,));p.start()
    原子的保存(出力,{'測定状態':'実行中','実測':{'開始epoch':起点,'正本採用可':False},'実行中':[{'工程':'資料集合取得'}],'個票':[]})
    try:
        while True:
            残=max(0,締切-time.time())
            if 残<=0:raise TimeoutError('資料集合取得中に90分経過')
            try:状態,cases,z=q.get(timeout=min(0.1,残));break
            except queue.Empty:
                if not p.is_alive():raise RuntimeError('資料集合取得プロセスの異常終了')
        if 状態!='成功':raise RuntimeError(cases)
    except BaseException as exc:
        結果={'測定状態':'時間超過' if isinstance(exc,TimeoutError) else '処理失敗','実測':{'開始epoch':起点,'経過秒':time.time()-起点,'正本採用可':False},'処理失敗':[str(exc)],'個票':[]}
        原子的保存(出力,結果);return 結果
    finally:_停止(p);q.close();q.cancel_join_thread()
    try:from .中核正本評価 import _リポジトリ版
    except ImportError:from 中核正本評価 import _リポジトリ版
    条件={"外部評価":"GPQA Diamond","資料集合ZIP_SHA256":z,"資料集合CSV_SHA256":資料SHA256,
        "全問題数":198,"選択肢シャッフル種":0,"OpenAlex有効":False,"EuropePMC有効":True,
        "Crossref有効":True,"Wikipedia言語群":["en"],"参照方式":"LIVE_ONLY","固定参照資料許可":False,
        "中核入口":"HDS駆動コア.選択実行","既存能力継承":True,"学習循環":True,
        "外付け能力モジュール":False,"科学専門モジュール":False,"旧HDS監督":False,
        "問題束一問一形成":True,"正解利用境界":"親プロセスで中核実行後に採点","リポジトリ版":_リポジトリ版()}
    問題群=[(i,*cases[i]) for i in range(開始番号,開始番号+件数)]
    return _実行を管理(問題群,出力,方式=方式,条件=条件,期限秒=max(0,締切-time.time()),並列数=並列数,時計開始=起点,
        復元点ディレクトリ=str(Path(出力).with_suffix(".checkpoints")))


def main():
    p=argparse.ArgumentParser(description='GPQA全数実測。90分・並列43点下限を固定する。')
    p.add_argument('--mode',choices=('parallel','serial'),required=True)
    p.add_argument('--out',type=Path,required=True);p.add_argument('--start-index',type=int,default=0)
    p.add_argument('--limit',type=int,default=198);p.add_argument('--workers',type=int,default=1)
    p.add_argument('--deadline-epoch',type=float);p.add_argument('--started-epoch',type=float)
    a=p.parse_args();r=GPQAを測定(a.out,方式='並列' if a.mode=='parallel' else '直列',開始番号=a.start_index,
        件数=a.limit,期限epoch=a.deadline_epoch,並列数=a.workers,共通開始epoch=a.started_epoch)
    if r.get('測定状態')!='完了' or not r.get('実測',{}).get('完走'):return 2
    if a.start_index==0 and a.limit==198 and not r['実測']['正本採用可']:return 3
    return 0

if __name__=='__main__':raise SystemExit(main())

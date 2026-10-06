"""分割成功の件数ではなく、198個票の完走・同一性・時間・得点を検査する。"""
from __future__ import annotations
import argparse,json,math,time
from pathlib import Path
from collections import Counter
from GPQA実測管理 import 原子的保存,資料SHA256,全数,時間上限秒,性能継承下限


def _参照健全性(rows):
    状態=Counter()
    HTTP429=Counter()
    子診断総数=0
    for row in rows:
        監査=row.get('採用監査')
        診断群=監査.get('取得診断',()) if isinstance(監査,dict) else ()
        for 診断 in 診断群 if isinstance(診断群,(list,tuple)) else ():
            子群=診断.get('子診断',()) if isinstance(診断,dict) else ()
            for 子 in 子群 if isinstance(子群,(list,tuple)) else ():
                if not isinstance(子,dict):continue
                子診断総数+=1
                供給器=str(子.get('供給器') or '未知')
                状態[(供給器,str(子.get('状態') or '未知'))]+=1
                if 子.get('HTTP状態')==429:HTTP429[供給器]+=1
    return {
        '子診断総数':子診断総数,
        'HTTP429総数':sum(HTTP429.values()),
        'Wikipedia429':sum(v for k,v in HTTP429.items() if k.startswith('Wikipedia')),
        'Crossref429':sum(v for k,v in HTTP429.items() if k.startswith('Crossref')),
        'EuropePMC429':sum(v for k,v in HTTP429.items() if k.startswith('EuropePMC')),
        '供給器状態':{f'{k[0]}:{k[1]}':v for k,v in sorted(状態.items())},
    }


def 集計(資料群,*,版,開始,締切,現在=None):
    今=time.time() if 現在 is None else 現在
    失敗=[];個票={}
    if not all(type(x) in (int,float) and math.isfinite(x) for x in (開始,締切,今)):
        raise ValueError('時刻が不正')
    if not 0<締切-開始<=時間上限秒:失敗.append('90分の共通締切違反')
    if not 版 or 版=='未知':失敗.append('版未確定')
    共通={'資料集合CSV_SHA256':資料SHA256,'全問題数':198,'選択肢シャッフル種':0,
        '実行方式':'問題独立並列','問題間継続状態':False,'参照方式':'LIVE_ONLY',
        '固定参照資料許可':False,'採点結果の学習利用':False,'中核入口':'HDS駆動コア.選択実行',
        'リポジトリ版':版,'OpenAlex有効':False,'EuropePMC有効':True,'Crossref有効':True,
        'Wikipedia言語群':['en'],'全数wall_clock上限分':90}
    for n,p in enumerate(資料群):
        条件=p.get('評価条件',{});実測=p.get('実測',{})
        for k,v in 共通.items():
            if 条件.get(k)!=v or type(条件.get(k)) is not type(v):失敗.append(f'shard{n}:条件不一致:{k}')
        if p.get('測定状態')!='完了' or 実測.get('完走') is not True:失敗.append(f'shard{n}:未完走')
        if 実測.get('開始epoch')!=開始:失敗.append(f'shard{n}:計測起点不一致')
        end=実測.get('終了epoch')
        if type(end) not in (int,float) or not math.isfinite(end) or not 開始<=end<=締切:失敗.append(f'shard{n}:締切違反')
        ids=[]
        for row in p.get('個票',[]):
            i=row.get('番号');ids.append(i)
            if type(i) is not int or not 0<=i<198:失敗.append(f'shard{n}:問題番号不正');continue
            if i in 個票:失敗.append(f'重複番号:{i}');continue
            if row.get('問題束形成回数')!=1:失敗.append(f'一問一形成違反:{i}')
            pred=row.get('予測ラベル');gold=row.get('正解ラベル');answered=row.get('回答済み')
            if gold not in ('A','B','C','D') or type(answered) is not bool or answered!=(pred in ('A','B','C','D')):
                失敗.append(f'回答形式違反:{i}')
            if answered and row.get('終端')!='COMMIT':失敗.append(f'採用前回答混入:{i}')
            correct=bool(answered and pred==gold)
            if row.get('正答') is not correct:失敗.append(f'採点不一致:{i}')
            個票[i]={**row,'正答':correct}
        if sorted(ids)!=条件.get('選択番号群'):失敗.append(f'shard{n}:実行範囲不一致')
    if sorted(個票)!=list(range(198)):失敗.append('198問の一意完走不成立')
    # 集計までを90分に含める。runner待ちを時間計測から消さない。
    if 今>締切:失敗.append('集計完了が90分超過')
    xs=[個票[i]for i in sorted(個票)];score=sum(x['正答'] for x in xs)
    if score<性能継承下限:失敗.append(f'性能継承下限未達:{score}/198')
    return {'契約形式':'minidora.gpqa.parallel-inheritance.v2','リポジトリ版':版,
        '全数':198,'完了数':len(xs),'正答':score,'回答':sum(x.get('回答済み') is True for x in xs),
        '性能継承下限':性能継承下限,'性能継承成立':not 失敗,'全数wall_clock上限分':90,
        '参照健全性':_参照健全性(xs),
        '開始epoch':開始,'終了epoch':今,'経過秒':今-開始,'受入失敗':失敗,'個票':xs}


def main():
    p=argparse.ArgumentParser();p.add_argument('--dir',type=Path,required=True);p.add_argument('--out',type=Path,required=True)
    p.add_argument('--revision',required=True);p.add_argument('--started-epoch',type=float,required=True);p.add_argument('--deadline-epoch',type=float,required=True)
    a=p.parse_args();資料=[];読込失敗=[]
    for f in sorted(a.dir.glob('gpqa_parallel_*.json')):
        try:資料.append(json.loads(f.read_text(encoding='utf-8')))
        except Exception as exc:読込失敗.append(f.name+': '+str(exc))
    r=集計(資料,版=a.revision,開始=a.started_epoch,締切=a.deadline_epoch)
    if 読込失敗:r['受入失敗'].extend(読込失敗);r['性能継承成立']=False
    原子的保存(a.out,r);print(json.dumps({k:v for k,v in r.items()if k!='個票'},ensure_ascii=False,indent=2))
    return 0 if r['性能継承成立'] else 3

if __name__=='__main__':raise SystemExit(main())

"""Git blob照合済みv1ソースと同梱版で、限定した従来契約を同条件比較する。"""
from __future__ import annotations
import argparse
from hashlib import sha1, sha256
import importlib.util
import json
from pathlib import Path
import sys

sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'src'))
import importlib
現行=importlib.import_module('minidora.HDS実行主体')
期待blob='3c9874c70a4280c9e2e9a6c4cb35bedcb24d7023'


def _投影(結果):
    return {'終端':結果.終端.value,'成立':sorted(結果.状態.成立状態),'残差':sorted(結果.状態.残差),
            '成果':list(結果.状態.成果),'主体状態':list(結果.状態.主体状態),
            '作用順':[x.作用ID for x in 結果.履歴],'理由':list(結果.理由)}


def 比較する(原本:Path):
    b=原本.read_bytes()
    blob=sha1(b'blob '+str(len(b)).encode()+b'\0'+b).hexdigest()
    if blob!=期待blob:raise ValueError('基準ソースのGit blobが不一致')
    spec=importlib.util.spec_from_file_location('minidora_exact_v1_baseline',原本)
    旧=importlib.util.module_from_spec(spec);sys.modules[spec.name]=旧;spec.loader.exec_module(旧)
    結果=[]
    def add(name,build):
        a=_投影(build(旧));b=_投影(build(現行))
        判定 = '一致' if a == b else '構造改善' if a['終端']=='SUSPEND' and b['終端']=='COMMIT' and set(a['成立']) <= set(b['成立']) and not b['残差'] else '要監査差'
        結果.append({'条件':name,'一致':a==b,'判定':判定,'基準':a,'修正版':b})

    for n in range(1,13):
        def 連鎖(m,n=n):
            acts=[]
            for i in range(n):
                acts.append(m.HDS関数作用(f'工程{i:02d}',lambda s,i=i:m.HDS作用結果(m.HDS作用状態.成立,追加状態=frozenset({str(i)})),
                                      入力状態=() if i==0 else (str(i-1),),出力状態=(str(i),)))
            return m.HDS実行主体(acts,最大作用回数=n).実行(m.HDS実行状態(要求状態=frozenset({str(n-1)})))
        add(f'従来直列工程{n}',連鎖)
    for n in range(3,13):
        def guarded(m,n=n):
            acts=tuple(m.HDS関数作用(f'条件付{i:02d}',lambda s,i=i:m.HDS作用結果(m.HDS作用状態.成立,追加状態=frozenset({str(i)})),
                        入力状態=() if i==0 else (str(i-1),),出力状態=(str(i),),
                        機会判定=lambda s,i=i:str(i) not in s.成立状態) for i in range(n))
            return m.HDS実行主体(acts,最大作用回数=n).実行(m.HDS実行状態(要求状態=frozenset({str(n-1)})))
        add(f'既存機会条件を明示した直列工程{n}',guarded)
    for n in (1,2,4,8):
        def shortage(m,n=n):
            acts=tuple(m.HDS関数作用('解消'+str(i),lambda s,i=i:m.HDS作用結果(m.HDS作用状態.成立,解消残差=frozenset({str(i)})),
                                      解消対象=(str(i),)) for i in range(n))
            return m.HDS実行主体(acts).実行(m.HDS実行状態(残差=frozenset(str(i) for i in range(n))))
        add(f'残差解消{n}',shortage)
    add('既に閉包',lambda m:m.HDS実行主体(()).実行(m.HDS実行状態(要求状態=frozenset({'済'}),成立状態=frozenset({'済'}))))
    add('未達で作用なし',lambda m:m.HDS実行主体(()).実行(m.HDS実行状態(要求状態=frozenset({'未達'}))))
    add('一度実行後に無進展停止',lambda m:m.HDS実行主体((m.HDS関数作用('無進展',lambda s:m.HDS作用結果(m.HDS作用状態.保留)),)).実行(m.HDS実行状態(要求状態=frozenset({'未達'}))))
    for 状態 in ('保留','失敗'):
        add('明示停止'+状態,lambda m,状態=状態:m.HDS実行主体((m.HDS関数作用('停止',lambda s:m.HDS作用結果(getattr(m.HDS作用状態,状態),停止要求=True,理由=('明示試験',))),)).実行(m.HDS実行状態(要求状態=frozenset({'未達'}))))
    def 主体(m):
        a=m.HDS関数作用('主体',lambda s:m.HDS作用結果(m.HDS作用状態.成立,解消残差=frozenset({'更新'}),主体状態差分=(('対象','新状態'),)),解消対象=('更新',))
        return m.HDS実行主体((a,)).実行(m.HDS実行状態(残差=frozenset({'更新'})))
    add('主体局所状態',主体)
    def artifact(m):
        a=m.HDS関数作用('作成',lambda s:m.HDS作用結果(m.HDS作用状態.成立,追加状態=frozenset({'完了'}),成果=(('結果',('値',123)),)),出力状態=('完了',))
        return m.HDS実行主体((a,)).実行(m.HDS実行状態(要求状態=frozenset({'完了'})))
    add('構造化成果',artifact)
    return {'範囲':'選定した実行契約・構造診断33条件。上流全回帰・MINIDORA30ベンチではない。',
            '基準GitBlob':blob,'基準SHA256':sha256(原本.read_bytes()).hexdigest(),
            '条件数':len(結果),'一致数':sum(x['一致'] for x in 結果),
            '構造改善数':sum(x['判定']=='構造改善' for x in 結果),
            '要監査差数':sum(x['判定']=='要監査差' for x in 結果),'結果':結果}


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--baseline-source',required=True,type=Path)
    p.add_argument('--output',type=Path)
    a=p.parse_args();r=比較する(a.baseline_source)
    text=json.dumps(r,ensure_ascii=False,indent=2)+'\n'
    if a.output:a.output.parent.mkdir(parents=True,exist_ok=True);a.output.write_text(text,encoding='utf-8')
    else:print(text)
    raise SystemExit(0 if r['要監査差数']==0 else 1)

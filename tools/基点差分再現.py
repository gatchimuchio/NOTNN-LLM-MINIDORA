"""取得済み原本と変更コピーを別Pythonプロセスで比較する。外部通信なし。"""
from __future__ import annotations
import argparse
import json
import os
from pathlib import Path
import subprocess
import sys


def 観測():
    from itertools import islice
    from minidora.能力合成 import 能力合成器, 登録能力, 合成計画, 合成工程
    from minidora.製品版.型 import 能力結果
    from minidora.命題句 import 最上位位置
    from minidora.命題解釈 import 命題を読む
    from minidora.文脈命題 import 文脈資料を読む, 文脈判定
    from minidora.公開本文取得 import 本文を復号
    class 不整合能力:
        名前='不整合能力';版='試験';優先度=0
        def 判定(self,c):return 1.0
        def 実行(self,c):return 能力結果(True,'確定回答',保留理由='意味未確定')
    out=能力合成器((登録能力(不整合能力()),)).実行(
        合成計画((合成工程('a',('不整合能力',),'p'),),('a',)),{'p':能力結果(True,'試験')})
    results={'成立保留併存':{'合成状態':out.状態,'出力採用':bool(out.出力),'監査整合':out.監査整合()}}
    try:
        # 無限消費せず最初の3出力だけを観測する。
        hits=list(islice(最上位位置('ABC',('',)),3))
        results['空区切り']={'結果':hits,'無進行反復':len(hits)==3 and len(set(i for i,_ in hits))==1}
    except ValueError as e:results['空区切り']={'拒否':str(e)}
    try:
        e=命題を読む('猫(彼)')[0].式
        results['未解決指示語']={'受理':True,'項':e.項[0].名前,'種別':e.項[0].種別}
    except ValueError as e:results['未解決指示語']={'受理':False,'理由':str(e)}
    html='<p>P。</p><table><tr><td>否定(P)。</td></tr></table>'
    doc=本文を復号('https://example.org/',('https://example.org/',),
        {'content-type':'text/html; charset=utf-8'},html.encode())
    results['表除外']={'抽出本文':doc.本文,'除外要素':list(doc.除外要素),
        '抽出本文のみの判定':文脈判定((文脈資料を読む(doc.本文,'甲'),),'P')['判定']}
    try:
        from minidora.取得意味境界 import 取得本文の意味境界を検査
    except ModuleNotFoundError:results['表除外']['追加意味境界']='基点に未実装'
    else:
        try:取得本文の意味境界を検査(doc);results['表除外']['追加意味境界']='通過'
        except ValueError as e:results['表除外']['追加意味境界']='拒否:'+str(e)
    for name,text,query in (
        ('帰属言い換え','太郎が「P」と言いました。','P'),
        ('否定言い換え','太郎は猫じゃない。','太郎は猫である'),
        ('時点引用','2026年では(太郎が「私は猫です」と言いました)。',
         '2026年では(太郎は「太郎は猫である」と述べた)')):
        try:results[name]={'判定':文脈判定((文脈資料を読む(text,'甲'),),query)['判定']}
        except ValueError as e:results[name]={'拒否':str(e)}
    return results


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--参照ソース',type=Path)
    parser.add_argument('--変更ソース',type=Path)
    parser.add_argument('--出力',type=Path)
    parser.add_argument('--子実行',action='store_true')
    args=parser.parse_args()
    if args.子実行:
        print(json.dumps(観測(),ensure_ascii=False));return 0
    if not args.参照ソース or not args.変更ソース or not args.出力:
        parser.error('参照ソース・変更ソース・出力が必要')
    report={}
    for name,path in (('基点',args.参照ソース),('変更後',args.変更ソース)):
        env=dict(os.environ);env['PYTHONPATH']=str(path.resolve());env['PYTHONDONTWRITEBYTECODE']='1'
        result=subprocess.run([sys.executable,str(Path(__file__).resolve()),'--子実行'],
            env=env,capture_output=True,text=True,encoding='utf-8',check=True,timeout=15)
        report[name]=json.loads(result.stdout)
    report['注記']='実ソースの局所比較。表除外の追加境界と命題化は個別実行であり、既存製品の取得接続全体の実行証明ではない。'
    args.出力.parent.mkdir(parents=True,exist_ok=True)
    args.出力.write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print(json.dumps(report,ensure_ascii=False,indent=2))
    return 0

if __name__=='__main__':raise SystemExit(main())

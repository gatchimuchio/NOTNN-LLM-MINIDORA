"""帰属・照応・場合別判定・説明・取得全文の命題検討を実接続する人工資料デモ。"""
from pathlib import Path
import argparse
import json
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'src'))
from minidora.汎用会話 import 汎用会話セッション
from minidora.知識取得 import 知識取得器
from minidora.公開本文取得 import 本文を復号
from minidora.製品版.型 import 参照資料
from minidora.会話回答 import 回答記録整合


def _判定(result):
    if result.結果 is None: return None
    d=result.結果.データ['元結果'][0]['データ']
    if d['種別']=='取得命題判定':d=d['文脈報告']['データ']
    return d['判定結果']['判定']


def 実演():
    session=汎用会話セッション('文脈命題デモ')
    script=(
        ('資料「発言」を登録:太郎は「私は猫である」と述べた。','合格',None),
        ('資料「発言」から「太郎は「太郎は猫である」と述べた」は言える？','合格','支持'),
        ('資料「発言」から「太郎は猫である」は言える？','合格','未確定'),
        ('資料「会話」を登録:太郎は猫である。彼は鳥である。','合格',None),
        ('資料「会話」から「太郎は鳥である」は言える？','合格','支持'),
        ('根拠を説明して','合格','支持'),
        ('資料「条件」を登録:PまたはQ。PならばR。QならばR。','合格',None),
        ('資料「条件」から「R」は言える？。詳しく','合格','支持'),
        ('資料「曖昧」を登録:PまたはQかつR。','合格',None),
        ('資料「曖昧」から「R」は言える？','確認待ち',None),
        ('資料解釈は2です','合格','支持'),
        ('資料「曖昧」から「PまたはQ」は言える？','合格','支持'),
        ('資料「曖昧」を更新:Q。','合格',None),
        ('根拠を説明して','保留',None),
    )
    rows=[]
    for text,state,status in script:
        r=session.応答(text);decision=_判定(r)
        if r.状態!=state or decision!=status or r.結果 is not None and not 回答記録整合(r.結果):
            raise RuntimeError('文脈会話の期待・整合不一致:'+text+':'+r.理由)
        rows.append({'入力':text,'状態':r.状態,'判定':decision,'本文':r.本文})
    return rows


def 人工取得実演():
    calls={'検索':0,'本文取得':0}
    class 検索:
        def 検索(self,query,limit=5):
            calls['検索']+=1
            return (参照資料('candidate','人工検索','検索抜粋','https://example.test/rules',
                           本文='太郎は哺乳類ではない'),)
    class 本文:
        def 取得(self,url):
            calls['本文取得']+=1
            text='すべての猫は哺乳類である。太郎は猫である。'
            return 本文を復号(url,(url,),{'content-type':'text/plain; charset=utf-8'},text.encode())
    session=汎用会話セッション('人工取得デモ',取得器=知識取得器(検索(),本文()),外部読取許可=True)
    query='公開資料から「太郎は哺乳類である」を検討して'
    rows=[]
    for text,permission,state,status in ((query,False,'確認待ち',None),(query,True,'合格','支持'),
                                        ('根拠を説明して',False,'合格','支持')):
        r=session.応答(text,外部読取許可=permission)
        if r.状態!=state or _判定(r)!=status:raise RuntimeError('人工取得の実接続不一致:'+r.理由)
        rows.append({'入力':text,'状態':r.状態,'判定':_判定(r),'本文':r.本文,'供給回数':dict(calls)})
    if calls!={'検索':1,'本文取得':1}:raise RuntimeError('説明で再取得した又は許可前に取得した')
    return rows


def main():
    for stream in (sys.stdout,sys.stderr):
        if hasattr(stream,'reconfigure'):stream.reconfigure(encoding='utf-8',errors='strict')
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--json',action='store_true')
    args=parser.parse_args()
    output={'種類':'人工資料・人工検索・人工本文。実HDSと実取得器、計画・採用・会話を使用。公開Webには通信しない。',
            '会話':実演(),'人工取得':人工取得実演()}
    if args.json:print(json.dumps(output,ensure_ascii=False,indent=2))
    else:
        print(output['種類']+'\n')
        for row in (*output['会話'],*output['人工取得']):
            print('利用者：'+row['入力']);print('MINIDORA［'+row['状態']+'］：'+row['本文']+'\n')
    return 0


if __name__=='__main__':raise SystemExit(main())

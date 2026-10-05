"""選択APIの意味契約を、共通の九座標と実結果へ接続する。

入力条件を一律に「接続済み」にしない。対応できる条件は検査方法と結び、
非対応の目的・書式・条件は原入力に残して共通境界で未接続とする。
"""
from __future__ import annotations
from dataclasses import dataclass
from ..コア.指示関係 import HDS指示条件

確認接頭辞='HDS選択:入力確認:'

@dataclass(frozen=True,slots=True)
class 選択入力接続:
    条件:tuple
    成果対応:tuple
    外部読取可:bool
    暫定採用可:bool
    参照必須:bool


def 選択入力を接続(入力):
    条件=[];対応=[]
    外部可=暫定可=True;参照必須=False
    def 接続(ID):
        条件.append(HDS指示条件('選択入力:'+ID,ID,'成果:'+確認接頭辞+ID,'一致',True))
    for 目的 in 入力.目的:
        # Compilerの問い空所・検索焦点は候補回答の役割であり、一般の目的文字列ではない。
        if 目的.種別 in ('未知始点','未知終点','検索焦点'):
            接続('目的/'+目的.ID)
    for 検証 in 入力.検証要求:
        if 検証.種別=='残差解消確認' and 検証.ID.startswith('検証:'):
            ID=検証.ID[len('検証:'):]
            元=next((x for x in 入力.残差 if x.ID==ID),None)
            if 元 is not None:
                条件.append(HDS指示条件('残差検証:'+ID,'検証要求/'+検証.ID,
                    '残差:HDS残差:'+元.種別+':'+元.理由))
    for 制約 in 入力.実行制約:
        if (制約.種別,制約.値)==('外部読取','禁止'):
            外部可=False;接続('実行制約/'+制約.ID)
        elif (制約.種別,制約.値)==('資料範囲','提供資料のみ'):
            外部可=False;接続('実行制約/'+制約.ID)
        elif (制約.種別,制約.値)==('推測','禁止'):
            暫定可=False;接続('実行制約/'+制約.ID)
        elif (制約.種別,制約.値)==('参照','必須'):
            参照必須=True;接続('実行制約/'+制約.ID)
    # 選択APIの標準出力は、推論方式が計算・取得・比較であっても最終的な候補回答である。
    # Compilerの論理成果名を別成果の生成要求へ昇格させず、実際の回答ラベルへ射影する。
    for 名前 in 入力.要求成果:
        対応.append((名前,'成果:HDS選択:回答ラベル'))
    # 選択APIの出力は言語非依存のラベル。追加の文書形式要求までは代理しない。
    if 入力.表現制約.出力言語 is not None and not 入力.表現制約.要求:
        接続('表現制約')
    return 選択入力接続(tuple(条件),tuple(対応),外部可,暫定可,参照必須)


def 選択入力の実結果(入力,接続,*,採用,参照,関係判定,外部取得回数):
    値={}
    for 条件 in 接続.条件:
        if not 条件.ノード.startswith('成果:'+確認接頭辞):continue
        ID=条件.座標ID
        if ID.startswith('目的/'):
            成立=採用 is not None
        elif ID=='表現制約':
            成立=採用 is not None and isinstance(採用.回答ラベル,str)
        else:
            制約=next(x for x in 入力.実行制約 if '実行制約/'+x.ID==ID)
            if 制約.種別 in ('外部読取','資料範囲'):成立=外部取得回数==0
            elif 制約.種別=='推測':成立=採用 is not None and 関係判定.一意成立==採用.回答ラベル
            elif 制約.種別=='参照':成立=bool(参照)
            else:成立=False
        値[確認接頭辞+ID]=成立
    return tuple(値.items())

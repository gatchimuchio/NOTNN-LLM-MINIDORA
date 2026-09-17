"""定型の数値変更とは別に、演算木を生成して日本語/記号/生成コードを対照する。"""
from __future__ import annotations
import argparse
from fractions import Fraction
import json
import random
from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from minidora.HDS運用.数量構造 import 数量を構成, 数量を評価
from minidora.HDS運用.数量生成 import 数量コード仕様, 数量コード実行, 数量を照合
from minidora.コード生成 import 関数を生成


def main():
    解析=argparse.ArgumentParser(description='数量の再帰合成に対する独立変形検証')
    解析.add_argument('--output',type=Path,required=True)
    引数=解析.parse_args()
    乱数=random.Random(260918)
    記録=[]
    名前=['量甲','量乙','量丙','量丁']
    def 構成(深さ):
        if not 深さ or 乱数.random()<0.25:
            return ('参照',乱数.randrange(4))
        return (乱数.choice(['+','-','*','/']),構成(深さ-1),構成(深さ-1))
    def 評価(木,値):
        if 木[0]=='参照':return Fraction(値[木[1]])
        左,右=評価(木[1],値),評価(木[2],値)
        if 木[0]=='+':return 左+右
        if 木[0]=='-':return 左-右
        if 木[0]=='*':return 左*右
        return 左/右
    def 表記(木,日本語):
        if 木[0]=='参照':return 名前[木[1]]
        左,右=表記(木[1],日本語),表記(木[2],日本語)
        if 日本語:return '('+左+'と'+右+{'+' : 'の和','-':'の差','*':'の積','/':'の商'}[木[0]]+')'
        return '('+左+木[0]+右+')'
    要求={'対象':['入力'],'規則':[],'数量':'報告量','操作':['計算','検算'],'条件変更':[],
           '表示':{'詳細':False,'コード':False,'形式':'文章','読者':'一般'}}
    for 番号 in range(240):
        値=[乱数.randint(-9,12) for _ in 名前]
        木=構成(3)
        try:期待=評価(木,値);ゼロ除算=False
        except ZeroDivisionError:期待=None;ゼロ除算=True
        行={'番号':番号,'演算木':木,'数値':値,'期待':str(期待) if 期待 is not None else 'ゼロ除算','出力':[]}
        for 日本語 in [False,True]:
            本文=''.join(f'{名}は{数}。' for 名,数 in zip(名前,値))+'報告量は'+表記(木,日本語)+'。'
            構造=数量を構成({'入力':本文},要求)
            try:計算=数量を評価(構造)
            except ValueError as e:
                if not ゼロ除算 or 'ゼロ除算' not in str(e):raise
                行['出力'].append({'日本語':日本語,'状態':'期待したゼロ除算拒否'})
                continue
            if ゼロ除算 or Fraction(計算['結果'][0]['値'])!=期待:
                raise AssertionError('独立演算木と数量構文化の結果不一致:'+本文)
            仕様=数量コード仕様(構造);コード=関数を生成(**仕様)
            if not コード.成立:raise AssertionError(コード.保留理由)
            検算=数量コード実行(構造,コード.本文)
            if Fraction(*検算['評価']['値'][0])!=期待:raise AssertionError('生成コード不一致')
            数量を照合(構造,計算,検算)
            行['出力'].append({'日本語':日本語,'状態':'一致','値':str(期待),'本文':本文})
        記録.append(行)
    成果={'seed':260918,'演算木数':len(記録),'入力表記数':2*len(記録),
            '有効計算木数':sum(r['期待']!='ゼロ除算' for r in 記録),
            'ゼロ除算木数':sum(r['期待']=='ゼロ除算' for r in 記録),
            '合格':True,'境界':'有限な合成文法・数値演算の検証。任意未見自然言語の性能評価ではない。',
            '記録':記録}
    引数.output.write_text(json.dumps(成果,ensure_ascii=False,indent=2),encoding='utf-8')
    print(json.dumps({k:v for k,v in 成果.items() if k!='記録'},ensure_ascii=False))
    return 0


if __name__=='__main__':raise SystemExit(main())

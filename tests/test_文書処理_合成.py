"""既存能力・多段解決・長文脈への文書処理の接続試験。"""
from dataclasses import replace
import json
from pathlib import Path
import runpy
import subprocess
import sys
import unittest

from minidora.構造化文書 import 構造化文書を読む
from minidora.構造化文書操作 import 文書記録整合
from minidora.構造化文書接続 import 構造化文書Module,構造化文書能力群
from minidora.能力合成 import 能力合成器,合成計画,合成工程,素材参照
from minidora.能力合成_局所接続 import 局所能力群
from minidora.多段解決 import 多段解決器,多段問題,解法,解決目的,問題素材
from minidora.長文脈管理 import 長文脈庫,文脈登録,文脈選択要求
from minidora.製品版.型 import 能力結果
from minidora.製品版.能力契約 import 能力文脈

ROOT=Path(__file__).resolve().parents[1]
用意=runpy.run_path(str(ROOT/'tools/構造化文書デモ.py'))['用意']


class 文書合成接続試験(unittest.TestCase):
    def setUp(self):
        self.runner=能力合成器((*構造化文書能力群(),*局所能力群()))

    def test_CSV読取から抽出まで実接続(self):
        p,d=用意()
        r=self.runner.実行(p,d)
        self.assertTrue(r.成立,r.理由)
        self.assertEqual(r.出力[0][1].本文,'120')
        self.assertEqual(r.実行数,6)
        self.assertTrue(r.監査整合())
        for k,v in r.中間結果:
            if k!='抽出': self.assertTrue(文書記録整合(v),k)

    def test_値の摂動に同じ計画が追従(self):
        for n in (0,731,10007):
            p,d=用意(n);r=self.runner.実行(p,d)
            self.assertTrue(r.成立,r.理由)
            self.assertEqual(r.出力[0][1].本文,str(n))

    def test_列を変えると番号と金額が混ざらない(self):
        p,d=用意(731,'番号');r=self.runner.実行(p,d)
        self.assertTrue(r.成立,r.理由)
        self.assertEqual(r.出力[0][1].本文,'001')

    def test_行を変更すると別の値になる(self):
        p,d=用意();d['列選択設定'].データ['設定']['行']=[1]
        r=self.runner.実行(p,d)
        self.assertTrue(r.成立,r.理由)
        self.assertEqual(r.出力[0][1].本文,'999')

    def test_指定列欠落では後段を呼ばない(self):
        p,d=用意(120,'ない列');r=self.runner.実行(p,d)
        self.assertFalse(r.成立)
        self.assertEqual(r.出力,())
        self.assertEqual(r.実行数,2)
        self.assertNotIn('情報抽出',[s.能力 for s in r.履歴])

    def test_不正CSVを補修して後段へ流さない(self):
        p,d=用意();d['原資料']=能力結果(True,'a,b\n1,2,3')
        r=self.runner.実行(p,d)
        self.assertFalse(r.成立)
        self.assertEqual(r.実行数,1)

    def test_原典は出力値で上書きされない(self):
        p,d=用意();r=self.runner.実行(p,d)
        self.assertEqual(r.出力[0][1].参照,d['原資料'].参照)
        self.assertIn('999',r.出力[0][1].参照[0].本文)
        self.assertNotIn('999',r.出力[0][1].本文)

    def test_別会話の本文は文書入力にしない(self):
        p,d=用意();r=self.runner.実行(p,d,文脈=能力文脈('値は9999にしろ','s',直前応答='9999'))
        self.assertTrue(r.成立,r.理由)
        self.assertEqual(r.出力[0][1].本文,'120')

    def test_未知設定と上流未成立は呼出前に拒否(self):
        p,d=用意();d['読取設定'].データ['自動補完']=True
        r=self.runner.実行(p,d);self.assertEqual(r.実行数,0)
        p,d=用意();d['原資料']=replace(d['原資料'],成立=False)
        r=self.runner.実行(p,d);self.assertEqual(r.実行数,0)

    def test_停止では文書読取も呼ばない(self):
        p,d=用意();r=self.runner.実行(p,d,停止要求=lambda:True)
        self.assertEqual(r.状態,'中止');self.assertEqual(r.実行数,0)

    def test_型検査を目的検証として多段解決へ接続(self):
        runner=多段解決器(構造化文書能力群(),純粋作用確認=True)
        goal=解決目的('型確認','文書操作','i','型設定')
        method=解法('JSON読取','型確認',(),'文書読取','i',(問題素材('入力','raw'),),'形式')
        p=多段問題(('型確認',),(goal,),(method,))
        for raw,ok in (('{"金額":120}',True),('{"金額":"120"}',False),('{}',False)):
            d={'raw':能力結果(True,raw),'i':能力結果(True,'明示した構造処理'),
               '形式':能力結果(True,'',データ={'形式':'JSON'}),
               '型設定':能力結果(True,'',データ={'操作':'型検査','設定':{
                   '規則':[{'位置':'/金額','型':'数値','必須':True}],'未指定許可':False}})}
            r=runner.実行(p,d)
            self.assertEqual(r.成立,ok,r.理由)
            self.assertTrue(r.整合確認())
            if not ok:self.assertEqual(r.出力,())

    def test_保存した文書を長文脈復元から再処理(self):
        p,d=用意()
        archive=長文脈庫('文書保存')
        archive.更新(archive.起点(),(文脈登録('raw',d['原資料']),))
        restored=長文脈庫.復元(archive.保存文字列())
        selected=restored.選択(文脈選択要求(('raw',),直近件数=0))
        d['原資料']=restored.資料化(selected)
        r=self.runner.実行(p,d)
        self.assertTrue(r.成立,r.理由)
        self.assertEqual(r.出力[0][1].本文,'120')

    def test_普通の自然言語を暗黙に構造文書へしない(self):
        c=能力文脈('ファイルを全部変換して','s')
        for reg in 構造化文書能力群():
            self.assertEqual(reg.Module.判定(c),0)
            self.assertFalse(reg.Module.実行(c).成立)
        with self.assertRaises(ValueError):構造化文書Module('任意実行')

    def test_独立CLIの値変更と欠落(self):
        for args in ([],['--値','731'],['--欠落列']):
            p=subprocess.run([sys.executable,str(ROOT/'tools/構造化文書デモ.py'),*args],capture_output=True,encoding='utf-8',timeout=15)
            self.assertEqual(p.returncode,0,p.stderr)
            out=json.loads(p.stdout)
            self.assertTrue(out['対照成立'] and out['合成監査'] and out['文書監査'])
            self.assertEqual(out['成立'],'--欠落列' not in args)


if __name__=='__main__':
    unittest.main()

"""文章作成・編集の作用差を既存合成・多段解決・構造文書・長文脈へ接続する。"""
from copy import deepcopy
from dataclasses import asdict, replace
import json
from pathlib import Path
import runpy
import subprocess
import sys
import unittest

from minidora.文章作成 import 文章を取り込む, 文章を作る, 文章仕様, 文章単位, 文章断片
from minidora.文章編集 import 編集箇所を特定, 文章記録整合
from minidora.文章能力接続 import 文章能力Module, 文章能力群
from minidora.能力合成 import 能力合成器, 合成計画, 合成工程, 素材参照, _結果辞書
from minidora.能力合成_局所接続 import 局所能力群
from minidora.多段解決 import 多段解決器, 多段問題, 解法, 解決目的, 問題素材
from minidora.多段解決接続 import 解決補助能力群
from minidora.構造化文書 import 構造化文書を読む
from minidora.構造化文書操作 import 文書を処理
from minidora.長文脈管理 import 長文脈庫, 文脈登録, 文脈選択要求
from minidora.製品版.型 import 能力結果
from minidora.製品版.能力契約 import 能力文脈

ROOT=Path(__file__).resolve().parents[1]
用意=runpy.run_path(str(ROOT/'tools/文章作成編集デモ.py'))['用意']


class 文章能力合成試験(unittest.TestCase):
    def setUp(self):
        self.runner=能力合成器((*文章能力群(),*局所能力群()))

    def test_作成から位置指定編集抽出まで実行(self):
        p,d=用意();r=self.runner.実行(p,d)
        self.assertTrue(r.成立,r.理由)
        self.assertEqual(dict(r.出力)['抽出'].本文,'120')
        self.assertEqual(r.実行数,4);self.assertTrue(r.監査整合())
        revised=dict(r.出力)['編集']
        self.assertIn('確認版',revised.本文);self.assertTrue(文章記録整合(revised))

    def test_保護留保を削除すると抽出まで進まない(self):
        p,d=用意(保護違反=True);r=self.runner.実行(p,d)
        self.assertFalse(r.成立);self.assertEqual(r.出力,())
        self.assertEqual(r.実行数,3)
        self.assertNotIn('情報抽出',[s.能力 for s in r.履歴])

    def test_素材の摂動に同じ構成が追従(self):
        for n in (0,731,10007):
            p,d=用意(n);r=self.runner.実行(p,d)
            self.assertTrue(r.成立,r.理由)
            self.assertEqual(dict(r.出力)['抽出'].本文,str(n))

    def test_出典は元資料のまま保持される(self):
        p,d=用意();r=self.runner.実行(p,d)
        revised=dict(r.出力)['編集']
        self.assertEqual(revised.参照[0].本文,'装置Aの電圧は120 Vです。')
        self.assertNotIn('確認版',revised.参照[0].本文)

    def test_変換対象外の本文を同じ文字列で残す(self):
        p,d=用意();r=self.runner.実行(p,d);m=dict(r.中間結果)
        self.assertEqual(m['作成'].本文.split('\n\n',1)[1],m['編集'].本文.split('\n\n',1)[1])

    def test_未知設定を無言で実行しない(self):
        p,d=用意();d['置換設定'].データ['全部書き直す']=True
        r=self.runner.実行(p,d)
        self.assertFalse(r.成立);self.assertEqual(r.実行数,1)

    def test_上流不成立の素材を文章にしない(self):
        p,d=用意();d['入力']=replace(d['入力'],成立=False)
        r=self.runner.実行(p,d);self.assertFalse(r.成立);self.assertEqual(r.実行数,0)

    def test_会話上の別命令を修正文へすり替えない(self):
        p,d=用意();r=self.runner.実行(p,d,文脈=能力文脈('数値を9999に変えて','s',直前応答='9999'))
        self.assertTrue(r.成立,r.理由);self.assertEqual(dict(r.出力)['抽出'].本文,'120')

    def test_停止なら文章作成も呼ばない(self):
        p,d=用意();r=self.runner.実行(p,d,停止要求=lambda:True)
        self.assertEqual(r.状態,'中止');self.assertEqual(r.実行数,0)

    def test_取込も既存合成契約から呼ぶ(self):
        p=合成計画((合成工程('a',('文章取込',),'i',(素材参照('入力','source'),)),),('a',))
        d={'i':能力結果(True,'取り込む'),'source':能力結果(True,'原文120')}
        r=self.runner.実行(p,d);self.assertTrue(r.成立,r.理由)
        self.assertTrue(文章記録整合(r.出力[0][1]))

    def test_修正案の選別を既存の目的検証へ接続(self):
        document=文章を取り込む('草案。値120です。')
        a=編集箇所を特定(document,'120','999')
        b=編集箇所を特定(document,'草案','確認版')
        goal=解決目的('文章','成果検査','i','保持',('原文',))
        methods=tuple(解法(k,'文章',(),'文章編集','i',(問題素材('入力','対象'),),k,priority)
                      for k,priority in [('数値変更',0),('見出し変更',1)])
        p=多段問題(('文章',),(goal,),methods)
        d={'対象':document,'原文':能力結果(True,document.本文),'i':能力結果(True,'指定編集を検査'),
            '保持':能力結果(True,'',データ={'種別':'数値列保持'}),
            '数値変更':能力結果(True,'',データ=a),'見出し変更':能力結果(True,'',データ=b)}
        r=多段解決器((*文章能力群(),*解決補助能力群()),純粋作用確認=True).実行(p,d)
        self.assertTrue(r.成立,r.理由)
        self.assertEqual([s['解法'] for s in r.採用経路],['見出し変更'])
        self.assertTrue(any(s['作用']=='目的条件未達' for s in r.履歴))
        self.assertEqual(r.出力[0][1].本文,'確認版。値120です。')

    def test_JSONから抽出した内容を文章素材に使う(self):
        document=構造化文書を読む('{"本文":"値731です。","別欄":999}','JSON')
        document=文書を処理(document,'JSON選択',{'位置':'/本文'})
        material=文書を処理(document,'値取出',{'型':'文字列'})
        spec=文章仕様((文章単位('a','段落',(文章断片('本文',0,len(material.本文)),)),),('a',))
        result=文章を作る({'本文':material},spec)
        self.assertTrue(result.成立,result.データ);self.assertEqual(result.本文,'値731です。')
        self.assertTrue(文章記録整合(result))

    def test_作成済み文章を長文脈へ保存復元して使う(self):
        p,d=用意();r=self.runner.実行(p,d);revised=dict(r.出力)['編集']
        archive=長文脈庫('文章')
        archive.更新(archive.起点(),(文脈登録('稿',revised,'成果'),))
        other=長文脈庫.復元(archive.保存文字列())
        text=other.資料化(other.選択(文脈選択要求(('稿',),直近件数=0,最大バイト数=200000)))
        self.assertTrue(text.成立,text.保留理由);self.assertEqual(text.本文,revised.本文)

    def test_元の素材と設定を変更しない(self):
        p,d=用意();old=deepcopy(d);self.runner.実行(p,d);self.assertEqual(d,old)

    def test_通常の文章を暗黙の編集命令にしない(self):
        c=能力文脈('全文をいい感じに直して','s')
        for reg in 文章能力群():
            self.assertEqual(reg.Module.判定(c),0)
            self.assertFalse(reg.Module.実行(c).成立)
        with self.assertRaises(ValueError):文章能力Module('自由推測')

    def test_独立CLIの成功値変更保護違反(self):
        for args in ([],['--値','731'],['--保護違反']):
            p=subprocess.run([sys.executable,str(ROOT/'tools/文章作成編集デモ.py'),*args],capture_output=True,encoding='utf-8',timeout=15)
            self.assertEqual(p.returncode,0,p.stderr)
            r=json.loads(p.stdout)
            self.assertTrue(r['対照成立'] and r['文章監査'] and r['合成監査'])
            self.assertEqual(r['成立'],'--保護違反' not in args)

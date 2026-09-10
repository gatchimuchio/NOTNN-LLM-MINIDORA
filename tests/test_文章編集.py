"""差分編集・保護範囲・原文対応・履歴再構成を検査する。"""
from copy import deepcopy
from dataclasses import replace
from itertools import combinations, product
import unittest

from minidora.文章作成 import 文章を取り込む, 保護範囲, _指紋, _由来原文
from minidora.文章編集 import 文章修正, 文章を編集, 文章記録整合, 編集箇所を特定
from minidora.製品版.型 import 能力結果


def patch(key,a,b,old,new):
    return 文章修正(key,a,b,old,new,'明示修正')


def edit(document,*mods):
    return 文章を編集(document,document.データ['記録SHA256'],tuple(mods))


class 文章編集試験(unittest.TestCase):
    def ok(self,result):
        self.assertTrue(result.成立,(result.保留理由,result.データ))
        self.assertTrue(文章記録整合(result))
        pos=0
        for span in result.データ['対応']:
            self.assertEqual(pos,span['開始'])
            origin=span['由来'];raw=_由来原文(origin,result.データ['原本'],result.データ['編集履歴'])
            self.assertEqual(raw[origin['開始']:origin['終了']],result.本文[span['開始']:span['終了']])
            pos=span['終了']
        self.assertEqual(pos,len(result.本文))
        return result

    def test_指定された語だけを変更(self):
        d=文章を取り込む('草案\r\n値120、条件は未確認。')
        r=self.ok(edit(d,patch('題',0,2,'草案','確定前の案')))
        self.assertEqual(r.本文,'確定前の案\r\n値120、条件は未確認。')
        self.assertEqual(r.データ['直近差分'][0]['旧文'],'草案')

    def test_挿入削除置換を同じ旧座標から一括適用(self):
        d=文章を取り込む('abcdef')
        r=self.ok(edit(d,patch('c',4,6,'ef','X'),patch('a',0,0,'','前'),patch('b',1,3,'bc','')))
        self.assertEqual(r.本文,'前adX')
        self.assertEqual([x['修正ID'] for x in r.データ['直近差分']],['a','b','c'])

    def test_挿入文に古い出典を付けない(self):
        d=文章を取り込む('原文120')
        r=self.ok(edit(d,patch('新規',2,5,'120','731')))
        self.assertEqual([s['由来']['種別'] for s in r.データ['対応']],['原本文','修正文'])
        self.assertEqual(r.データ['対応'][1]['由来']['ID'],'新規')

    def test_後の編集も初期原文と過去修正文に対応(self):
        d=文章を取り込む('abcde')
        r=self.ok(edit(d,patch('one',1,3,'bc','XYZ')))
        r=self.ok(edit(r,patch('two',2,3,'Y','長い')))
        self.assertEqual(r.本文,'aX長いZde')
        origins=[s['由来'] for s in r.データ['対応']]
        self.assertTrue(any(o['種別']=='修正文' and o['改訂']==1 for o in origins))
        self.assertTrue(any(o['種別']=='修正文' and o['改訂']==2 for o in origins))

    def test_保護内容の一字変更を拒否(self):
        d=文章を取り込む('甲120乙',(保護範囲('値',1,4,'120'),))
        before=deepcopy(d)
        r=edit(d,patch('変更',2,3,'2','3'))
        self.assertFalse(r.成立);self.assertEqual(r.本文,'');self.assertEqual(d,before)

    def test_保護内への挿入を拒否(self):
        d=文章を取り込む('甲120乙',(保護範囲('値',1,4,'120'),))
        self.assertFalse(edit(d,patch('挿入',2,2,'','x')).成立)

    def test_保護の前後への挿入を認め位置を移動(self):
        d=文章を取り込む('甲120乙',(保護範囲('値',1,4,'120'),))
        r=self.ok(edit(d,patch('前',1,1,'','['),patch('後',4,4,'',']')))
        self.assertEqual(r.本文,'甲[120]乙')
        lock=r.データ['保護'][0]
        self.assertEqual((lock['開始'],lock['終了']),(2,5))
        self.assertEqual(r.本文[lock['開始']:lock['終了']],'120')

    def test_保護位置より前の長さ変更で位置を再計算(self):
        d=文章を取り込む('abc120',(保護範囲('値',3,6,'120'),))
        r=self.ok(edit(d,patch('前',0,3,'abc','長い前置き')))
        self.assertEqual(r.データ['保護'][0]['開始'],5)

    def test_保護に触れる一件があれば他の修正も確定しない(self):
        d=文章を取り込む('草案120',(保護範囲('値',2,5,'120'),));before=deepcopy(d)
        r=edit(d,patch('題',0,2,'草案','案'),patch('値',2,5,'120','999'))
        self.assertFalse(r.成立);self.assertEqual(d,before);self.assertEqual(r.本文,'')

    def test_期待原文が違う場合は近い文字列に適用しない(self):
        d=文章を取り込む('abc')
        self.assertFalse(edit(d,patch('x',0,1,'b','X')).成立)

    def test_重なる修正を拒否(self):
        d=文章を取り込む('abcd')
        for rows in ((patch('a',0,2,'ab','x'),patch('b',1,3,'bc','y')),
                     (patch('a',1,1,'','x'),patch('b',1,2,'b','y')),
                     (patch('a',1,1,'','x'),patch('b',1,1,'','y'))):
            self.assertFalse(edit(d,*rows).成立)

    def test_隣接する範囲は独立に修正できる(self):
        d=文章を取り込む('abcd')
        r=self.ok(edit(d,patch('a',0,2,'ab','甲'),patch('b',2,4,'cd','乙')))
        self.assertEqual(r.本文,'甲乙')

    def test_新しい本文へ古い起点で適用しない(self):
        d=文章を取り込む('abc');r=edit(d,patch('a',0,1,'a','A'))
        attempt=文章を編集(r,d.データ['記録SHA256'],(patch('b',1,2,'b','B'),))
        self.assertFalse(attempt.成立)

    def test_同じ本文でも異なる保護契約の起点を使わない(self):
        a=文章を取り込む('abc');b=文章を取り込む('abc',(保護範囲('p',1,2,'b'),))
        self.assertFalse(文章を編集(a,b.データ['記録SHA256'],(patch('x',0,1,'a','A'),)).成立)

    def test_古い不変オブジェクトからの別枝は許可(self):
        # 庫のグローバル最新版管理ではなく、渡された文書に対する楽観的な起点検査。
        d=文章を取り込む('abc');a=edit(d,patch('a',0,1,'a','A'));b=edit(d,patch('b',0,1,'a','B'))
        self.ok(a);self.ok(b);self.assertEqual(d.本文,'abc')

    def test_検索文字列が一箇所なら位置を特定するだけ(self):
        d=文章を取り込む('abc120def');proposal=編集箇所を特定(d,'120','731')
        self.assertEqual(d.本文,'abc120def')
        self.assertEqual((proposal['修正'][0]['開始'],proposal['修正'][0]['終了']),(3,6))

    def test_欠落複数一致重なり一致は曖昧として拒否(self):
        for text,search in [('abc','x'),('120 120','120'),('aaa','aa')]:
            with self.assertRaises(ValueError):編集箇所を特定(文章を取り込む(text),search,'Z')

    def test_正規表現は実行せず完全一致で探す(self):
        d=文章を取り込む('x.*y ABC')
        p=編集箇所を特定(d,'.*','literal')
        self.assertEqual(p['修正'][0]['期待原文'],'.*')

    def test_Unicodeの文字位置と改行を保持(self):
        d=文章を取り込む('甲😀e\u0301\r\n乙')
        r=self.ok(edit(d,patch('a',1,2,'😀','表情')))
        self.assertEqual(r.本文,'甲表情e\u0301\r\n乙')

    def test_全削除や空白だけにはしない(self):
        d=文章を取り込む('abc')
        for text in ('',' \n'):
            self.assertFalse(edit(d,patch('a',0,3,'abc',text)).成立)

    def test_文字数上限で内容を途中切断しない(self):
        d=文章を取り込む('abc',最大文字数=3)
        self.assertFalse(edit(d,patch('a',3,3,'','d')).成立)

    def test_修正件数と履歴上限(self):
        d=文章を取り込む('abc')
        self.assertFalse(edit(d).成立)
        for i in range(16):
            d=self.ok(edit(d,patch('a',0,1,d.本文[0],'X' if i%2==0 else 'Y')))
        self.assertFalse(edit(d,patch('a',0,1,d.本文[0],'Z')).成立)

    def test_無変化と重複IDを拒否(self):
        d=文章を取り込む('abcd')
        self.assertFalse(edit(d,patch('a',0,1,'a','a')).成立)
        self.assertFalse(edit(d,patch('a',0,1,'a','X'),patch('a',2,3,'c','Y')).成立)

    def test_異常範囲と型を補完しない(self):
        d=文章を取り込む('abc')
        for a,b,old in [(-1,0,''),(0,4,'abc'),(True,2,'b'),(2,1,'')]:
            self.assertFalse(edit(d,patch('x',a,b,old,'Z')).成立)
        self.assertFalse(文章を編集(d,d.データ['記録SHA256'],[]).成立)

    def test_修正文の制御文字を拒否(self):
        d=文章を取り込む('abc')
        self.assertFalse(edit(d,patch('x',0,1,'a','\u202e')).成立)

    def test_本文改変とハッシュ再作成も再実行で検出(self):
        r=edit(文章を取り込む('abc'),patch('x',0,1,'a','X'))
        r=replace(r,本文='Zbc');r.データ.pop('記録SHA256')
        r.データ['記録SHA256']=_指紋({'本文':r.本文,'データ':r.データ})
        self.assertFalse(文章記録整合(r))

    def test_保護や対応の削除を検出(self):
        d=文章を取り込む('abc',(保護範囲('p',1,2,'b'),))
        for field in ('対応','保護'):
            bad=deepcopy(d);bad.データ[field]=[];self.assertFalse(文章記録整合(bad))

    def test_型不正や通常能力結果を文章記録へ昇格しない(self):
        for r in (None,{},能力結果(True,'本文'),能力結果(False,'')):
            self.assertFalse(文章記録整合(r))

    def test_旧原本と修正履歴を消さず残す(self):
        r=edit(文章を取り込む('abc'),patch('x',0,1,'a','X'))
        self.assertEqual(r.データ['原本']['本文'],'abc')
        self.assertEqual(r.データ['編集履歴'][0]['修正'][0]['期待原文'],'a')

    def test_編集で原入力を変更せず再現できる(self):
        d=文章を取り込む('abc');before=deepcopy(d)
        a=edit(d,patch('x',0,1,'a','X'));b=edit(d,patch('x',0,1,'a','X'))
        self.assertEqual(a,b);self.assertEqual(d,before)


class 編集独立対照試験(unittest.TestCase):
    def test_文字単位の別実装と全小規模修正を比較(self):
        original='abcde';count=0
        for a,b in combinations(range(5),2):
            for x,y in product(('','甲','XYZ'),repeat=2):
                expected=''.join(x if i==a else y if i==b else c for i,c in enumerate(original))
                d=文章を取り込む(original)
                r=edit(d,patch('a',a,a+1,original[a],x),patch('b',b,b+1,original[b],y))
                self.assertTrue(r.成立,r.データ);self.assertEqual(r.本文,expected)
                self.assertTrue(文章記録整合(r));count+=1
        self.assertEqual(count,90)

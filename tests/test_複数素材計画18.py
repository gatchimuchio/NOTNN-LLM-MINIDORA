"""二入力合成と後方探索の独立した人工作用による確認。"""
from copy import deepcopy
from dataclasses import replace
from itertools import product
import unittest
from minidora.複数素材計画 import 役割状態 as S, 結合作用 as R, 複数素材計画器
from minidora.製品版.型 import 能力結果


def rules():
    return (R('加工','加工',(S('原文',('対象',)),),S('値',('対象',)),lambda b,s:dict(b)),
            R('結合','比較',(S('値',('左',)),S('値',('右',))),S('比較',('左','右')),lambda b,s:dict(b)))

def data():return {S('原文',('A',)):能力結果(True,'7'),S('原文',('B',)):能力結果(True,'2')}

class 複数入力計画試験(unittest.TestCase):
    def test_二対象の役割を混線させない(self):
        p=複数素材計画器(rules()).計画する(S('比較',('A','B')),data(),{})
        self.assertEqual(len(p.計画.工程),3)
        self.assertEqual(p.計画.工程[-1].能力候補,('比較',))
        self.assertEqual(len(p.計画.工程[-1].入力),2)
        self.assertEqual(p.Data['設定:結合工程:002'].データ,{'左':'A','右':'B'})
    def test_資料挿入順は役割結果を変えない(self):
        p=複数素材計画器(rules());a=p.計画する(S('比較',('A','B')),data(),{})
        b=p.計画する(S('比較',('A','B')),dict(reversed(list(data().items()))),{})
        self.assertEqual(a.計画,b.計画);self.assertEqual(a.Data,b.Data)
    def test_役割反転は素材束縛も反転(self):
        p=複数素材計画器(rules()).計画する(S('比較',('B','A')),data(),{})
        self.assertEqual(p.Data['結合素材:0'].本文,'2')
    def test_依存を共有し重複実行しない(self):
        p=複数素材計画器(rules()).計画する(S('比較',('A','A')),data(),{})
        self.assertEqual(len(p.計画.工程),2)
        self.assertEqual(p.計画.工程[-1].入力[0],p.計画.工程[-1].入力[1])
    def test_片方の対象欠落を別の値で埋めない(self):
        with self.assertRaises(ValueError): 複数素材計画器(rules()).計画する(S('比較',('A','C')),data(),{})
    def test_探索中は設定以外の能力を実行しない(self):
        d=data();before=deepcopy(d);複数素材計画器(rules()).計画する(S('比較',('A','B')),d,{})
        self.assertEqual(d,before)
    def test_計画Dataは複製(self):
        d=data();p=複数素材計画器(rules()).計画する(S('比較',('A','B')),d,{})
        d[S('原文',('A',))].データ['汚染']=1
        self.assertEqual(p.Data['結合素材:0'].データ,{})
    def test_外部読取許可を二値で検査(self):
        p=複数素材計画器((replace(rules()[0],外部読取=True),rules()[1]))
        for allowed in (False,1):
            with self.assertRaises(ValueError):p.計画する(S('比較',('A','B')),data(),{},外部読取許可=allowed)
        self.assertEqual(p.計画する(S('比較',('A','B')),data(),{},外部読取許可=True).費用[0],2)
    def test_同順位の別作用を勝手に選択しない(self):
        with self.assertRaises(ValueError):複数素材計画器((*rules(),replace(rules()[0],識別子='別加工'))).計画する(S('比較',('A','B')),data(),{})
    def test_安い経路を選択(self):
        p=複数素材計画器((*rules(),replace(rules()[0],識別子='高費用',費用=5))).計画する(S('比較',('A','B')),data(),{})
        self.assertNotIn('高費用',[r[0] for r in p.工程意味.values()])
    def test_作用禁止は特定対象だけ(self):
        alternate=replace(rules()[0],識別子='予備',費用=3)
        p=複数素材計画器((*rules(),alternate)).計画する(S('比較',('A','B')),data(),{},禁止=(('加工',S('値',('B',))),))
        self.assertEqual([r[0] for r in p.工程意味.values()],['加工','予備','結合'])
    def test_循環だけなら完了しない(self):
        r=R('ループ','loop',(S('値',('対象',)),),S('値',('対象',)),lambda b,s:{})
        with self.assertRaises(ValueError):複数素材計画器((r,)).計画する(S('値',('A',)),{}, {})
    def test_探索上限は部分計画を成功にしない(self):
        with self.assertRaises(ValueError):複数素材計画器(rules(),最大展開数=1).計画する(S('比較',('A','B')),data(),{})
    def test_候補上限を守る(self):
        rs=(*rules(),replace(rules()[0],識別子='別'))
        with self.assertRaises(ValueError):複数素材計画器(rs,最大候補数=1).計画する(S('比較',('A','B')),data(),{})
    def test_不正役割と不成立素材を拒否(self):
        with self.assertRaises(ValueError):複数素材計画器((replace(rules()[0],入力=(S('原文',('未宣言',)),)),))
        d=data();d[S('原文',('A',))]=能力結果(False,'7')
        with self.assertRaises(ValueError):複数素材計画器(rules()).計画する(S('比較',('A','B')),d,{})
    def test_直積全列挙と最小費用が一致(self):
        # 左右独立の2候補作用を全列挙する参照計算。内部探索器を使わない。
        for x,y in product(range(1,4),repeat=2):
            rs=tuple(replace(r,費用=x) if r.識別子=='加工' else r for r in rules())
            rs=(*rs,replace(rs[0],識別子='別加工',費用=y))
            minimum=min(a+b+1 for a,b in product((x,y),repeat=2))
            if x==y:
                with self.assertRaises(ValueError):複数素材計画器(rs).計画する(S('比較',('A','B')),data(),{})
            else:
                self.assertEqual(複数素材計画器(rs).計画する(S('比較',('A','B')),data(),{}).費用[1],minimum)

if __name__=='__main__':unittest.main()

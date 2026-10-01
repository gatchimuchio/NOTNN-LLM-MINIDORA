"""動的な既存能力の接続と、同じ対象の文脈変化を通常循環で確認する。"""
import unittest
from dataclasses import replace
if __package__:
    from .test_指示九座標 import 指示を作る,初期,作用群,run
else:
    from test_指示九座標 import 指示を作る,初期,作用群,run
from minidora.HDS実行主体 import HDS関数作用,HDS作用結果,HDS作用状態,HDS実行主体,HDS終端,HDS作用供給器
from minidora.コア.指示関係 import HDS作用対応,HDS指示条件,HDS帰還先
from minidora.統合駆動_v2.政策 import HDS運用政策
from minidora.統合駆動_v2.計画 import HDS作用仕様, HDS探索契約
from minidora.統合駆動_v2.依存 import HDS依存辺


def 動的計算(ID='新計算', binding=None):
    binding = binding or HDS作用対応(ID,('対象/実体',),'手段/作用',('単価あり',))
    spec=HDS作用仕様(ID,追加状態=frozenset({'回答済'}),読取成果=('数量','単価'),
        生成成果=('合計',),契約完全=True,指示対応=binding)
    def apply(s):
        d=s.成果辞書()
        return HDS作用結果(HDS作用状態.成立,成果=(('合計',d['数量']*d['単価']),),追加状態=frozenset({'回答済'}))
    return HDS関数作用(ID,apply,計画仕様=spec)


class 動的接続試験(unittest.TestCase):
    def test_原指示に列挙されない手段を既存契約から接続する(self):
        p=replace(指示を作る(),作用対応=())
        a=動的計算()
        s=初期(p,成果=(('対象','注文A'),('数量',3),('単価',7)))
        r=run(s,(a,))
        self.assertEqual(r.終端,HDS終端.採用,r.理由)
        self.assertEqual(r.状態.指示関係.作用対応,())
        self.assertEqual(r.履歴[0].作用対応,a.計画仕様.指示対応)
    def test_動的供給作用も目的関係を構成し実測値を使う(self):
        p=指示を作る()
        supply=HDS作用供給器('条件から既存能力を供給',lambda s:(動的計算(),) if '単価' in s.成果辞書() else ())
        s=初期(p,成果=(('対象','注文A'),('数量',3),('単価',7)))
        r=run(s,(),作用供給器=(supply,))
        self.assertEqual(r.終端,HDS終端.採用,r.理由)
        self.assertEqual([h.作用ID for h in r.履歴],['新計算'])
        self.assertEqual(r.指示帰還.内容,(('依頼者','成果:合計',21),))
    def test_探索で得た関係を動的手段へ使う(self):
        p=指示を作る(bindings=(HDS作用対応('対応取得',('対象/実体',),'手段/作用'),))
        search=HDS探索契約('対応を調べる','合計に使う単価対応が未確定',('成果:単価',),('成果:合計',),2,2)
        a=HDS関数作用('対応取得',lambda s:HDS作用結果(HDS作用状態.成立,成果=(('単価',7),)),
            計画仕様=HDS作用仕様('対応取得',純粋=True,探索=search),機会判定=lambda s:'単価' not in s.成果辞書())
        supply=HDS作用供給器('観測後の手段供給',lambda s:(動的計算(),) if '単価' in s.成果辞書() else ())
        r=run(初期(p),(a,),作用供給器=(supply,))
        self.assertEqual(r.終端,HDS終端.採用,r.理由)
        self.assertEqual([h.作用ID for h in r.履歴],['対応取得','新計算'])
        self.assertEqual(r.計装.探索実行数,1)
        self.assertEqual(r.状態.指示関係,p)
    def test_存在しない座標へ接続した動的作用を拒否する(self):
        r=run(初期(),(動的計算(binding=HDS作用対応('新計算',('存在しない対象',),'手段/作用')),))
        self.assertEqual(r.終端,HDS終端.失敗)
        self.assertEqual(len(r.履歴),0)
    def test_原指示の対応を動的作用が上書きできない(self):
        a=動的計算('計算',HDS作用対応('計算',('対象/現在状態',),'手段/作用',('単価あり',)))
        r=run(初期(),(a,))
        self.assertEqual(r.終端,HDS終端.失敗)
    def test_仕様と対応の作用IDが異なる場合を拒否する(self):
        with self.assertRaisesRegex(ValueError,'ID'):
            HDS作用仕様('A',指示対応=HDS作用対応('B',('対象/実体',),'手段/作用'))
    def test_存在しない適用条件を補完しない(self):
        a=動的計算(binding=HDS作用対応('新計算',('対象/実体',),'手段/作用',('未定義条件',)))
        r=run(初期(),(a,))
        self.assertEqual(r.終端,HDS終端.失敗)
    def test_動的作用も取得前の値を読めない(self):
        r=run(初期(),(動的計算(),))
        self.assertEqual(r.終端,HDS終端.保留)
        self.assertEqual(r.履歴,())
    def test_同じ対象でも文脈が変われば適用する手段が変わる(self):
        p=指示を作る(conditions=(
            HDS指示条件('文脈A','対象/文脈・関係','成果:文脈','一致','A','適用'),
            HDS指示条件('文脈B','対象/文脈・関係','成果:文脈','一致','B','適用')))
        bindings=[HDS作用対応('文脈計算'+c,('対象/実体',),'手段/作用',('単価あり','文脈'+c)) for c in ('A','B')]
        actions=tuple(動的計算(b.作用ID,b) for b in bindings)
        first=run(初期(p,成果=(('対象','注文A'),('数量',3),('単価',7),('文脈','A'))),actions)
        self.assertEqual(first.終端,HDS終端.採用,first.理由)
        self.assertEqual(first.履歴[-1].作用ID,'文脈計算A')
        second=HDS実行主体(actions,政策=HDS運用政策(自動形成=False)).再開(first,
            HDS作用結果(HDS作用状態.成立,成果=(('文脈','B'),)))
        self.assertEqual(second.終端,HDS終端.採用,second.理由)
        self.assertEqual(second.履歴[-1].作用ID,'文脈計算B')
        self.assertEqual(second.状態.指示関係,p)
        self.assertGreater(second.計装.依存失効数,0)
    def test_仮の条件生成ラベルで実際の評価を迂回しない(self):
        spec=HDS作用仕様('偽装',追加状態=frozenset({'回答済'}),生成ノード=('指示条件:合計一致',),
            指示対応=HDS作用対応('偽装',('対象/実体',),'手段/作用'))
        a=HDS関数作用('偽装',lambda s:HDS作用結果(HDS作用状態.成立,追加状態=frozenset({'回答済'})),計画仕様=spec)
        r=run(初期(),(a,))
        self.assertNotEqual(r.終端,HDS終端.採用)
        self.assertEqual(r.指示帰還.内容,())
    def test_同じ契約版で対応だけ変える再開を拒否する(self):
        a=動的計算();s=初期(成果=(('対象','注文A'),('数量',3),('単価',7)))
        first=run(s,(a,))
        self.assertEqual(first.終端,HDS終端.採用)
        changed=動的計算(binding=HDS作用対応('新計算',('対象/現在状態',),'手段/作用',('単価あり',)))
        r=HDS実行主体((changed,),政策=HDS運用政策(自動形成=False)).再開(first,
            HDS作用結果(HDS作用状態.成立,成果=(('単価',8),)))
        self.assertEqual(r.終端,HDS終端.失敗)
        self.assertTrue(any('無言変更' in b.詳細 for b in r.阻害履歴))
    def test_再開時に必須検証器を外して採用できない(self):
        from minidora.統合駆動_v2.検証 import HDS検証器
        p=指示を作る(validators=(('必須検算','v1'),))
        v=HDS検証器('必須検算',lambda s,d:True)
        first=HDS実行主体(作用群(),最大作用回数=1,最終検証器=(v,),政策=HDS運用政策(自動形成=False)).実行(初期(p))
        self.assertEqual(first.終端,HDS終端.保留)
        self.assertEqual([h.作用ID for h in first.履歴],['単価取得'])
        r=HDS実行主体(作用群(),政策=HDS運用政策(自動形成=False)).再開(first)
        self.assertEqual(r.終端,HDS終端.失敗)
        self.assertEqual(r.指示帰還.内容,())
    def test_再開時に同名検証器の版を置換できない(self):
        from minidora.統合駆動_v2.検証 import HDS検証器
        p=指示を作る(validators=(('必須検算','v1'),))
        v=HDS検証器('必須検算',lambda s,d:True)
        first=HDS実行主体(作用群(),最大作用回数=1,最終検証器=(v,),政策=HDS運用政策(自動形成=False)).実行(初期(p))
        r=HDS実行主体(作用群(),最終検証器=(replace(v,版='v2'),),政策=HDS運用政策(自動形成=False)).再開(first)
        self.assertEqual(r.終端,HDS終端.失敗)
    def test_追加帰還値の根拠不足を例外でなく未成立として返す(self):
        p=指示を作る();p=replace(p,帰還先=p.帰還先+(HDS帰還先('手段/検証・帰還','成果:別値','監査先'),))
        s=初期(p,成立状態=frozenset({'回答済'}),成果=(('対象','注文A'),('数量',3),('合計',21),('別値',1)),
            依存=(HDS依存辺('成果:不存在','成果:別値'),))
        r=run(s,())
        self.assertEqual(r.終端,HDS終端.保留)
        self.assertEqual(r.指示帰還.内容,())


if __name__=='__main__':unittest.main()

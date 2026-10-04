from dataclasses import replace
from unittest import TestCase
from minidora.HDS実行主体 import HDS実行状態,HDS実行主体,HDS関数作用,HDS作用結果,HDS作用状態,HDS終端
from minidora.HDS駆動コア import HDS駆動コア
from minidora.HDSコア入力 import HDSコア入力束,HDSコア目的,HDSコア表現制約
from minidora.統合駆動_v2.政策 import HDS運用政策
from minidora.統合駆動_v2.計画 import HDS作用仕様
from minidora.統合駆動_v2.座標接続 import 全入力を座標へ,座標成果名
from minidora.コア.座標展開 import 指示を座標場へ
from minidora.コア.指示関係 import HDS指示関係,九座標を用意,座標状態

def 中核():
    return HDS駆動コア(最大作用回数=20,政策=HDS運用政策(自動形成=False))

def 入力(目的=(),要求成果=()):
    return HDSコア入力束('実入力を処理する','試験世界',(),(),(),tuple(目的),(),tuple(要求成果),(),(),(),HDSコア表現制約('ja'))

def 値作用(名前,値,読取=()):
    def 実行(状態):
        return HDS作用結果(HDS作用状態.成立,成果=((名前,dict(状態.成果)[読取[0]] if 読取 else 値),))
    return HDS関数作用('生成:'+名前,実行,計画仕様=HDS作用仕様('生成:'+名前,
        読取成果=tuple(読取),生成成果=(名前,),純粋=True))

class 座標展開試験(TestCase):
    def setUp(self):
        self.原指示=HDS指示関係('原文','世界',九座標を用意())
        self.場=指示を座標場へ(self.原指示)
    def test_九根を27操作面へ区分する(self):
        self.assertEqual(len(self.場.原指示.座標),9)
        self.assertEqual(len(self.場.面),27)
        self.assertEqual(len(self.場.末端面),27)
    def test_未観測を推測で埋めない(self):
        self.assertTrue(all(x.内容 is None for x in self.場.面))
        self.assertTrue(all(x.状態==座標状態.未観測 for x in self.場.面))
    def test_局所だけ展開し原面を残す(self):
        次=self.場.展開('目的/評価規則/変換',理由='評価条件が不足',利用先=('成果:答え',))
        self.assertEqual(len(次.面),30)
        self.assertEqual(len(次.末端面),29)
        self.assertEqual(次.原指示,self.原指示)
        self.assertEqual(len(self.場.面),27)
    def test_81末端でも27親を消さない(self):
        次=self.場
        for 項 in self.場.面: 次=次.展開(項.ID,理由='比較実験',利用先=('成果:答え',))
        self.assertEqual(len(次.末端面),81)
        self.assertEqual(len(次.面),108)
    def test_展開の再呼出は重複しない(self):
        次=self.場.展開(self.場.面[0].ID,理由='必要',利用先=('成果:答え',))
        self.assertIs(次.展開(self.場.面[0].ID,理由='再呼出',利用先=('成果:答え',)),次)
    def test_利用先なしに深掘りしない(self):
        with self.assertRaises(ValueError): self.場.展開(self.場.面[0].ID,理由='不要',利用先=())
    def test_容量不足は原面を失わない(self):
        with self.assertRaises(ValueError): self.場.展開(self.場.面[0].ID,理由='必要',利用先=('成果:答え',),最大追加面=2)
        self.assertEqual(len(self.場.面),27)
    def test_訂正は旧版と影響範囲を残す(self):
        次=self.場.帰還('対象/現在状態/取得','訂正後',状態=座標状態.確定値,根拠=('観測:1',),理由='訂正',期待版=0)
        self.assertEqual(次.原指示,self.原指示)
        self.assertEqual(len(次.旧面),3)
        self.assertEqual(次.履歴[0].後版,1)
    def test_競合版で上書きしない(self):
        with self.assertRaises(ValueError): self.場.帰還(self.場.面[0].ID,'値',状態=座標状態.確定値,根拠=('資料',),理由='訂正',期待版=9)

class 通常入口座標試験(TestCase):
    def test_実行入口が九座標を迂回しない(self):
        op=HDS関数作用('完了',lambda s:HDS作用結果(HDS作用状態.成立,追加状態=frozenset({'済'})),出力状態=('済',))
        r=中核().実行('処理',要求状態=('済',),追加作用=(op,))
        self.assertEqual(r.終端,HDS終端.採用,r.阻害履歴)
        self.assertEqual(len(r.状態.操作座標.面),27)
        self.assertIsNotNone(r.履歴[0].作用対応)
    def test_目的を変えると必要な作用が変わる(self):
        ops=tuple(HDS関数作用('生成:'+k,lambda s,k=k:HDS作用結果(HDS作用状態.成立,追加状態=frozenset({k})),出力状態=(k,)) for k in ('甲','乙'))
        for k in ('甲','乙'):
            r=中核().実行('指定目的を処理',要求状態=(k,),追加作用=ops)
            self.assertEqual(r.終端,HDS終端.採用,r.阻害履歴)
            self.assertEqual([h.作用ID for h in r.履歴],['生成:'+k])
    def test_構造化された目的評価を実値へ接続(self):
        原=入力((HDSコア目的('判定','評価規則',('成果:答え','一致',14)),))
        r=中核().実行(原.原文,入力正本=原,追加作用=(値作用('答え',14),))
        self.assertEqual(r.終端,HDS終端.採用,r.阻害履歴)
        self.assertEqual(r.状態.操作座標.原指示.原文,原.原文)
    def test_間違った値を完了ラベルで通さない(self):
        原=入力((HDSコア目的('判定','評価規則',('成果:答え','一致',14)),))
        r=中核().実行(原.原文,入力正本=原,要求状態=('済',),追加作用=(値作用('答え',99),))
        self.assertNotEqual(r.終端,HDS終端.採用)
    def test_未知評価規則をラベルへの参照だけで接続済みにしない(self):
        原=入力((HDSコア目的('判定','評価規則','意味がまだ構造化されていない'),))
        r=中核().実行(原.原文,入力正本=原,要求状態=('済',))
        self.assertIn('目的/判定',r.状態.指示関係.未接続座標)
        self.assertNotEqual(r.終端,HDS終端.採用)
    def test_要求成果そのものを完了条件へ使う(self):
        原=入力(要求成果=('答え',))
        r=中核().実行(原.原文,入力正本=原,追加作用=(値作用('答え',14),))
        self.assertEqual(r.終端,HDS終端.採用,r.阻害履歴)
        self.assertEqual(r.指示帰還.内容,(('答え','成果:答え',14),))
    def test_必要な中間成果の生産消費を自動計画する(self):
        原=入力(要求成果=('答え',))
        r=中核().実行(原.原文,入力正本=原,追加作用=(値作用('答え',None,('中間',)),値作用('中間',14)))
        self.assertEqual(r.終端,HDS終端.採用,r.阻害履歴)
        self.assertEqual([h.作用ID for h in r.履歴],['生成:中間','生成:答え'])
    def test_既存明示指示を自動射影で変更しない(self):
        from minidora.コア.指示関係 import HDS指示条件
        指示=HDS指示関係('原文','世界',九座標を用意(),条件=(HDS指示条件('評価','目的/到達状態','成果:答え'),))
        st=HDS実行状態(指示関係=指示)
        新=全入力を座標へ(st,原文='原文')
        self.assertIs(新.指示関係,指示)
        self.assertFalse(新.指示関係.自動作用接続)

    def test_実結果と条件観測を27面へ帰還する(self):
        原=入力(要求成果=('答え',))
        r=中核().実行(原.原文,入力正本=原,追加作用=(値作用('答え',14),))
        self.assertEqual(r.終端,HDS終端.採用,r.阻害履歴)
        self.assertTrue(r.状態.操作座標.履歴)
        self.assertEqual(r.状態.操作座標.原指示.原文,原.原文)
        面=next(x for x in r.状態.操作座標.面 if x.ID=='目的/評価規則/射影')
        self.assertIn('成立',tuple(x[1] for x in 面.内容))
    def test_中間進展に後続利用先と目的条件を記録する(self):
        原=入力(要求成果=('答え',))
        r=中核().実行(原.原文,入力正本=原,追加作用=(値作用('答え',None,('中間',)),値作用('中間',14)))
        self.assertEqual(r.終端,HDS終端.採用,r.阻害履歴)
        対応=next(x for x in r.履歴[0].目的進展対応 if x[0]=='成果:中間')
        self.assertIn('生成:答え',対応[2]);self.assertIn('要求成果:答え',対応[1])

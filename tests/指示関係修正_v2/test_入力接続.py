"""Git blob一致を確認した既存Core入力型・既存入力準備関数との接続試験。"""
import unittest
from dataclasses import replace
from minidora.HDSコア入力 import (HDSコア入力束,HDSコア意味項目,HDSコア関係,HDSコア目的,
    HDSコア作用要求,HDSコア条件,HDSコア検証要求,HDSコア実行制約,HDSコア表現制約,HDSコア表現要求)
from minidora.入力系.互換 import 既存入力を準備
from minidora.HDS実行主体 import HDS実行主体,HDS実行状態,HDS関数作用,HDS作用結果,HDS作用状態,HDS終端
from minidora.コア.指示関係 import (コア入力を指示へ射影,HDS指示条件,HDS作用対応,HDS帰還先,座標状態)
from minidora.コア.値 import 署名
from minidora.統合駆動_v2.依存 import HDS依存辺
from minidora.統合駆動_v2.政策 import HDS運用政策
if __package__:
    from .test_指示九座標 import run,初期,指示を作る,作用群
else:
    from test_指示九座標 import run,初期,指示を作る,作用群


def コア入力():
    return HDSコア入力束('注文Aの数量3、単価7の合計を返す。注文A以外に変更しない。','注文世界:A',
        (HDSコア意味項目('t','対象.注文','注文A','確定','明示入力',(0,3)),
         HDSコア意味項目('q','属性.数量',3,'確定','明示入力'),
         HDSコア意味項目('u','属性.単価',7,'確定','明示入力'),
         HDSコア意味項目('option','選択肢',{'候補':'未採用'},'未確定','候補')), 
        (HDSコア関係('r',('q',),('u',),'積',('c',),('対象=注文A',),'未確定'),),
        (HDSコア条件('c','対象範囲','注文A','確定','明示入力',('t',)),),
        (HDSコア目的('p','回答','合計を返す',('t',)),),
        (HDSコア作用要求('act','計算',('t',),('合計',)),),('合計',),(),
        (HDSコア検証要求('v','計算結果一致',('t',),('合計を照合',)),),
        (HDSコア実行制約('bound','対象固定','注文Aを保持'),),
        HDSコア表現制約('ja'),('元の依頼',))


def 射影(core):
    return コア入力を指示へ射影(core,
        条件=(HDS指示条件('対象','意味/t','成果:対象','一致','注文A','維持',
                          参照座標=('条件/c','実行制約/bound')),
              HDS指示条件('単価','意味/u','成果:単価',段階='適用'),
              HDS指示条件('合計','目的/p','成果:合計','一致',21,
                          参照座標=('検証要求/v','要求成果'))),
        作用対応=(HDS作用対応('単価取得',('意味/t',),'作用要求/act'),
                  HDS作用対応('計算',('意味/t',),'作用要求/act',('単価',))),
        帰還先=(HDS帰還先('手段/検証・帰還','成果:合計','依頼者'),))


def 入力状態(core=None, projection=None):
    core=core or コア入力();p=projection or 射影(core)
    prepared=既存入力を準備(core.原文,None,入力正本=core,
        成果初期値=(('対象','注文A'),('数量',3)),主体初期値=(('HDS指示関係',p),))
    return HDS実行状態(目的=prepared.目的初期値,要求状態=frozenset({'回答済'}),
        成果=prepared.成果初期値,主体状態=prepared.主体初期値,
        残差=prepared.残差群,成立状態=prepared.成立初期値)


class 入力接続試験(unittest.TestCase):
    def test_既存入力束から実際の通常循環で回答する(self):
        s=入力状態();r=run(s)
        self.assertEqual(r.終端,HDS終端.採用,r.理由)
        self.assertEqual(r.指示帰還.内容,(('依頼者','成果:合計',21),))
        self.assertEqual(r.状態.成果辞書()['HDSコア入力'],コア入力())
    def test_原入力全体を正規形で保存する(self):
        core=コア入力();p=射影(core)
        self.assertEqual(p.原入力署名,署名(core))
        self.assertIn('候補',p.原入力正本)
        self.assertIn('注文A以外',p.原文)
        self.assertIn('条件ID',p.座標辞書()['関係/r'].内容)
    def test_不明な選択肢は事実にしない(self):
        p=射影(コア入力())
        self.assertEqual(p.座標辞書()['意味/option'].状態,座標状態.未確定)
        self.assertEqual(p.座標辞書()['目的/必要性'].状態,座標状態.未観測)
    def test_未知の意味種別を原文付きで残す(self):
        core=コア入力();x=HDSコア意味項目('new','未知の分類',('原文',1),'将来追加状態','元の観測')
        p=射影(replace(core,意味項目=core.意味項目+(x,)))
        self.assertIn('未知の分類',p.座標辞書()['意味/new'].内容)
        self.assertEqual(p.座標辞書()['意味/new'].状態,座標状態.未確定)
    def test_未対応の実行制約を保存だけで済ませない(self):
        core=コア入力();core=replace(core,実行制約=core.実行制約+(HDSコア実行制約('新制約','追加','未対応制約'),))
        p=射影(core);self.assertEqual(p.未接続座標,('実行制約/新制約',))
        r=run(入力状態(core,p))
        self.assertEqual(r.終端,HDS終端.保留)
        self.assertEqual(r.履歴,())
        self.assertIn('実行制約/新制約',r.理由[-1])
    def test_未対応の表現要求を勝手に無視しない(self):
        core=replace(コア入力(),表現制約=HDSコア表現制約('ja','en',(HDSコア表現要求('style','形式','一文'),)))
        p=射影(core)
        self.assertIn('表現制約',p.未接続座標)
        self.assertEqual(run(入力状態(core,p)).終端,HDS終端.保留)
    def test_別入力の射影を混ぜない(self):
        a=コア入力();b=replace(a,認知世界ID='注文B')
        r=run(入力状態(b,射影(a)))
        self.assertEqual(r.終端,HDS終端.失敗)
        self.assertEqual(r.履歴,())
    def test_原入力正本を改変した射影は作れない(self):
        p=射影(コア入力())
        with self.assertRaisesRegex(ValueError,'不一致'):
            replace(p,原入力正本=p.原入力正本+' ')
    def test_入力束型以外を推測で受けない(self):
        with self.assertRaisesRegex(TypeError,'入力束'):コア入力を指示へ射影(object())
    def test_入力準備と実行欄の二つの指示を競合させない(self):
        s=入力状態()
        with self.assertRaisesRegex(ValueError,'競合'):
            replace(s,指示関係=指示を作る())
    def test_座標矛盾を値一致で隠さない(self):
        p=指示を作る();coords=tuple(replace(x,状態=座標状態.矛盾) if x.ID=='目的/評価規則' else x for x in p.座標)
        r=run(初期(replace(p,座標=coords)))
        self.assertNotEqual(r.終端,HDS終端.採用)
        self.assertTrue(any('矛盾' in x.理由 for x in r.指示帰還.観測.条件))
    def test_新しい到達条件も孤立依存を無視しない(self):
        s=初期(成立状態=frozenset({'回答済'}),成果=(('対象','注文A'),('数量',3),('合計',21)),
            依存=(HDS依存辺('成果:存在しない前提','成果:合計'),))
        r=run(s,())
        self.assertNotEqual(r.終端,HDS終端.採用)
    def test_新しい到達条件も循環依存を無視しない(self):
        s=初期(成立状態=frozenset({'回答済'}),成果=(('対象','注文A'),('数量',3),('合計',21),('仮根拠',1)),
            依存=(HDS依存辺('成果:仮根拠','成果:合計'),HDS依存辺('成果:合計','成果:仮根拠')))
        self.assertNotEqual(run(s,()).終端,HDS終端.採用)
    def test_復帰しても原文と過去の観測を保持する(self):
        s=入力状態();first=HDS実行主体(作用群()[:1],政策=HDS運用政策(自動形成=False)).実行(s)
        self.assertEqual(first.終端,HDS終端.保留)
        resumed=HDS実行主体(作用群(),政策=HDS運用政策(自動形成=False)).再開(first)
        self.assertEqual(resumed.終端,HDS終端.採用,resumed.理由)
        self.assertEqual(resumed.履歴[:len(first.履歴)],first.履歴)
        self.assertEqual(resumed.状態.指示関係,s.指示関係)
    def test_開始の必要性は維持条件と同一視しない(self):
        p=指示を作る(conditions=(HDS指示条件('開始必要','目的/必要性','成果:必要','一致',True,'開始'),),
            bindings=(HDS作用対応('前処理',('対象/実体',),'手段/作用'),))
        s=初期(p,成果=(('対象','注文A'),('数量',3),('必要',True)))
        prep=HDS関数作用('前処理',lambda s:HDS作用結果(HDS作用状態.成立,成果=(('必要',False),('単価',7))),
            生成成果=('単価',))
        # 利用先の契約を先に与え、実行予算で工程間を中断する。
        # 消費者も経路も未記述の準備を、必要だと推測して実行させない。
        first=HDS実行主体((prep,作用群()[1]),最大作用回数=1,政策=HDS運用政策(自動形成=False)).実行(s)
        self.assertEqual(first.終端,HDS終端.保留)
        self.assertEqual([h.作用ID for h in first.履歴],['前処理'])
        self.assertIs(first.状態.成果辞書()['必要'],False)
        resumed=HDS実行主体(作用群()[1:],政策=HDS運用政策(自動形成=False)).再開(first)
        self.assertEqual(resumed.終端,HDS終端.採用,resumed.理由)


if __name__=='__main__':unittest.main()

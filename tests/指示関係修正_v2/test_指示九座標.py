"""九座標を実際の通常循環へ接続する正例と反例。人工入力の構造試験。"""
import unittest
from dataclasses import replace
from unittest.mock import patch
from minidora.HDS実行主体 import (HDS実行主体, HDS実行状態, HDS関数作用,
    HDS作用結果, HDS作用状態, HDS終端, HDS作用供給器)
from minidora.統合駆動_v2.政策 import HDS運用政策
from minidora.統合駆動_v2.目的保持 import 目的契約署名
from minidora.統合駆動_v2.指示接続 import 帰還を読む, 条件を観測
from minidora.統合駆動_v2.検証 import HDS検証器
from minidora.コア.指示関係 import (HDS指示座標, 座標状態, 三組九座標, 九座標を用意,
    HDS指示関係, HDS指示条件, HDS作用対応, HDS帰還先, 指示を接続)


def 指示を作る(*, expected=21, extra=(), conditions=(), bindings=(), validators=()):
    raw = '注文Aの数量3、単価7から合計を計算し、検算して依頼者へ返す。対象の取り違えは禁止。'
    values = ('注文A', ('数量', 3), '注文Aの単価を利用', '依頼者へ請求額を示す',
              ('合計', expected), '整数の合計が期待内容と一致', '取得して計算する', '対象を変更しない', '検算結果を依頼者へ返す')
    coords = tuple(HDS指示座標(g+'/'+n,g,n,v,座標状態.確定値,('試験の明示要求',),((0,len(raw)),))
                   for (g,n),v in zip(三組九座標,values)) + tuple(extra)
    conds = (HDS指示条件('対象一致','対象/実体','成果:対象','一致','注文A','維持'),
             HDS指示条件('単価あり','対象/現在状態','成果:単価',段階='適用'),
             HDS指示条件('合計一致','目的/評価規則','成果:合計','一致',expected),
             HDS指示条件('返却内容','手段/検証・帰還','成果:合計',段階='返却')) + tuple(conditions)
    maps = (HDS作用対応('単価取得',('対象/実体',),'手段/作用'),
            HDS作用対応('計算',('対象/実体',),'手段/作用',('単価あり',))) + tuple(bindings)
    return HDS指示関係(raw,'注文世界:A',九座標を用意(coords),
        (('目的/必要性','目的/到達状態','必要性に基づく'),('目的/到達状態','目的/評価規則','成立を判定'),
         ('手段/作用','目的/到達状態','成立を試みる'),('手段/検証・帰還','目的/必要性','結果を帰還')),
        conds,maps,(HDS帰還先('手段/検証・帰還','成果:合計','依頼者'),),tuple(validators))


def 初期(指示=None, **changes):
    s=HDS実行状態(目的=('注文Aの合計を返す',),要求状態=frozenset({'回答済'}),
                 成果=(('対象','注文A'),('数量',3)),指示関係=指示 or 指示を作る())
    return replace(s,**changes)


def 作用群(*, wrong=False, calls=None):
    calls=calls if calls is not None else []
    def get(s):
        calls.append('単価取得')
        return HDS作用結果(HDS作用状態.成立,成果=(('単価',7),))
    def calc(s):
        calls.append('計算')
        data=s.成果辞書()
        return HDS作用結果(HDS作用状態.成立,追加状態=frozenset({'回答済'}),
            成果=(('合計',99 if wrong else data['数量']*data['単価']),))
    return (HDS関数作用('単価取得',get,生成成果=('単価',),契約完全=True),
            HDS関数作用('計算',calc,読取成果=('数量','単価'),生成成果=('合計',),出力状態=('回答済',),契約完全=True))


def run(s=None, actions=None, **kw):
    return HDS実行主体(actions if actions is not None else 作用群(),
        政策=HDS運用政策(初期作用予算=1,予算増分=1,自動形成=False),最大作用回数=8,**kw).実行(s or 初期())


class 九座標構造試験(unittest.TestCase):
    def test_九座標は未観測で残る(self):
        coords=九座標を用意()
        self.assertEqual([(x.組,x.名称) for x in coords],list(三組九座標))
        self.assertTrue(all(x.状態==座標状態.未観測 and x.内容 is None for x in coords))
    def test_追加座標と階層を保持する(self):
        extra=HDS指示座標('必要性/依存','目的','依存関係','請求処理',座標状態.推定値,('観測候補',),親='目的/必要性')
        p=指示を作る(extra=(extra,))
        self.assertEqual(len(p.座標),10)
        self.assertEqual(p.座標辞書()[extra.ID],extra)
    def test_非三項の子も排除しない(self):
        extra=tuple(HDS指示座標(str(i),'目的','条件',親='目的/必要性') for i in range(5))
        self.assertEqual(len(指示を作る(extra=extra).座標),14)
    def test_深さを固定しない(self):
        rows=[];parent='目的/必要性'
        for i in range(150):
            rows.append(HDS指示座標('深さ'+str(i),'目的','条件',親=parent));parent=rows[-1].ID
        self.assertEqual(len(指示を作る(extra=rows).座標),159)
    def test_親の循環を拒否する(self):
        a=HDS指示座標('a','目的','条件',親='b');b=replace(a,ID='b',親='a')
        with self.assertRaisesRegex(ValueError,'循環'):指示を作る(extra=(a,b))
    def test_存在しない参照を拒否する(self):
        with self.assertRaisesRegex(ValueError,'不存在'):
            指示を作る(extra=(HDS指示座標('a','目的','条件',親='不存在'),))
    def test_確定に由来を要求する(self):
        with self.assertRaisesRegex(ValueError,'由来'):
            HDS指示座標('a','対象','実体','A',座標状態.確定値)
    def test_可変内容を拒否する(self):
        with self.assertRaises(TypeError):HDS指示座標('a','対象','実体',{'x':1})
    def test_座標原文範囲を照合する(self):
        with self.assertRaisesRegex(ValueError,'原文'):
            指示を作る(extra=(HDS指示座標('a','目的','条件',原文範囲=((0,500),)),))
    def test_原文と条件が署名に反映する(self):
        s=初期();p=s.指示関係
        self.assertNotEqual(目的契約署名(s),目的契約署名(replace(s,指示関係=replace(p,原文=p.原文+'追加'))))
        c=replace(p.条件[2],期待値=22)
        self.assertNotEqual(目的契約署名(s),目的契約署名(replace(s,指示関係=replace(p,条件=p.条件[:2]+(c,)+p.条件[3:]))))
    def test_使わない未観測項を理由に全体停止しない(self):
        p=指示を作る(extra=(HDS指示座標('未観測追加','目的','追加観点'),))
        self.assertEqual(run(初期(p)).終端,HDS終端.採用)
    def test_九座標を強制最小数としない(self):
        p=HDS指示関係('入力','世界',(HDS指示座標('単独','任意','観点'),))
        self.assertEqual(len(p.座標),1)
    def test_同じIDを重ねない(self):
        x=HDS指示座標('a','対象','実体')
        with self.assertRaisesRegex(ValueError,'重複'):九座標を用意((x,x))
    def test_未観測を否定としない(self):
        c=HDS指示条件('a','対象/実体','成果:不存在','不一致',123)
        self.assertEqual(条件を観測(初期(),c).判定,'未確定')
    def test_数値と真偽値を同一視しない(self):
        c=HDS指示条件('a','対象/実体','成果:値','一致',True)
        self.assertEqual(条件を観測(初期(成果=(('値',1),)),c).判定,'不成立')


class 九座標通常循環試験(unittest.TestCase):
    def test_対象目的手段から途中成果を使って回答する(self):
        r=run()
        self.assertEqual(r.終端,HDS終端.採用,r.理由)
        self.assertEqual([x.作用ID for x in r.履歴],['単価取得','計算'])
        self.assertEqual(r.指示帰還.内容,(('依頼者','成果:合計',21),))
        self.assertEqual(r.計装.予算拡張数,1)
    def test_準備で新しい状態名がなくても条件が前進する(self):
        r=run()
        self.assertIn('指示条件:単価あり',r.履歴[0].進展根拠)
        self.assertTrue(r.履歴[0].目的進展)
    def test_現在状態だけが変化し原目的は保持する(self):
        s=初期();p=s.指示関係;r=run(s)
        self.assertEqual(r.状態.指示関係,p)
        self.assertEqual(r.履歴[0].指示前観測.指示署名,r.履歴[0].指示後観測.指示署名)
        self.assertNotEqual(r.履歴[0].指示前観測.状態署名,r.履歴[0].指示後観測.状態署名)
        self.assertEqual(r.履歴[1].対応座標,('対象/実体','手段/作用'))
    def test_対象が違えば実行しない(self):
        calls=[];r=run(初期(成果=(('対象','注文B'),('数量',3))),作用群(calls=calls))
        self.assertEqual(r.終端,HDS終端.保留)
        self.assertEqual(calls,[])
    def test_対象が未観測なら補完せず保留する(self):
        r=run(初期(成果=(('数量',3),)))
        self.assertEqual(r.終端,HDS終端.保留)
        self.assertIn('未確定',r.理由[-1])
    def test_評価が不成立なら完了ラベルでも採用しない(self):
        r=run(actions=作用群(wrong=True))
        self.assertNotEqual(r.終端,HDS終端.採用)
        self.assertEqual(r.指示帰還.内容,())
        row=next(x for x in r.指示帰還.観測.条件 if x.ID=='合計一致')
        self.assertEqual(row.判定,'不成立')
    def test_未接続の目的を空条件で採用しない(self):
        p=replace(指示を作る(),条件=(),作用対応=())
        r=run(初期(p,成立状態=frozenset({'回答済'})))
        self.assertEqual(r.終端,HDS終端.保留)
        self.assertIn('未接続',r.理由[-1])
    def test_目的に合うラベルでも対応がなければ実行しない(self):
        calls=[]
        a=HDS関数作用('誤対象',lambda s:(calls.append(1) or HDS作用結果(HDS作用状態.成立)),出力状態=('回答済',))
        r=run(actions=(a,))
        self.assertEqual(calls,[])
        self.assertEqual(r.指示除外[0][0],'誤対象')
    def test_維持境界を破る結果はロールバックする(self):
        p=指示を作る(bindings=(HDS作用対応('対象交換',('対象/実体',),'手段/作用'),))
        a=HDS関数作用('対象交換',lambda s:HDS作用結果(HDS作用状態.成立,
            成果=(('対象','注文B'),('合計',21)),追加状態=frozenset({'回答済'})),
            生成成果=('合計','対象'),出力状態=('回答済',))
        r=run(初期(p),(a,))
        self.assertEqual(r.終端,HDS終端.失敗)
        self.assertEqual(r.状態.成果辞書()['対象'],'注文A')
        self.assertNotIn('合計',r.状態.成果辞書())
    def test_不明な適用条件の取得作用は止めない(self):
        r=run()
        self.assertEqual(r.終端,HDS終端.採用,r.理由)
        self.assertTrue(any(x[0]=='計算' for x in r.指示除外))
    def test_必要性は到達状態の言い換えにしない(self):
        c=HDS指示条件('必要','目的/必要性','成果:請求必要','一致',True,'開始')
        r=run(初期(指示を作る(conditions=(c,))))
        self.assertEqual(r.終端,HDS終端.保留)
        self.assertIn('必要:未確定',r.理由)
    def test_必要性の開始条件を充足すれば実行する(self):
        c=HDS指示条件('必要','目的/必要性','成果:請求必要','一致',True,'開始')
        s=初期(指示を作る(conditions=(c,)),成果=(('対象','注文A'),('数量',3),('請求必要',True)))
        self.assertEqual(run(s).終端,HDS終端.採用)
    def test_最終検証器の版がなければ採用しない(self):
        p=指示を作る(validators=(('最終検算','v3'),))
        r=run(初期(p),最終検証器=(HDS検証器('最終検算',lambda s,d:True,'v2'),))
        self.assertEqual(r.終端,HDS終端.失敗)
    def test_要求した検証器を実行して帰還する(self):
        calls=[];p=指示を作る(validators=(('最終検算','v3'),))
        def verify(s,d):calls.append(1);return s.成果辞書()['合計']==21
        r=run(初期(p),最終検証器=(HDS検証器('最終検算',verify,'v3'),))
        self.assertEqual(r.終端,HDS終端.採用,r.理由)
        self.assertEqual(calls,[1])
    def test_最終検証不合格を優先返却で飛ばさない(self):
        p=指示を作る(validators=(('最終検算','v3'),))
        r=run(初期(p),最終検証器=(HDS検証器('最終検算',lambda s,d:False,'v3'),))
        self.assertNotEqual(r.終端,HDS終端.採用)
    def test_任意保守の故障で成立した回答を失わない(self):
        with patch('minidora.統合駆動_v2.自動記憶.自動記憶圧縮作用.機会',side_effect=RuntimeError('任意保守故障')):
            r=run()
        self.assertEqual(r.終端,HDS終端.採用)
        self.assertIn('任意の記憶圧縮',r.指示帰還.保守待ち)
    def test_再送では作用を再実行しない(self):
        calls=[];r=run(actions=作用群(calls=calls));n=len(calls)
        self.assertEqual(帰還を読む(r),帰還を読む(r))
        self.assertEqual(len(calls),n)
    def test_帰還の改変を再送しない(self):
        r=run();bad=replace(r,指示帰還=replace(r.指示帰還,内容=(('依頼者','成果:合計',99),)))
        with self.assertRaisesRegex(ValueError,'変更'):帰還を読む(bad)
    def test_再開で指示を差し替えられない(self):
        r=run();bad=replace(r,状態=replace(r.状態,指示関係=replace(r.状態.指示関係,認知世界ID='別世界')))
        again=HDS実行主体((),政策=HDS運用政策(自動形成=False)).再開(bad)
        self.assertEqual(again.終端,HDS終端.失敗)
    def test_明示停止を返却優先でも守る(self):
        r=run(停止要求=lambda:True)
        self.assertEqual(r.終端,HDS終端.保留)
        self.assertEqual(r.指示開始署名,'')
    def test_後付け接続を通常更新と混同しない(self):
        s=HDS実行状態()
        bound=指示を接続(s,指示を作る())
        with self.assertRaisesRegex(ValueError,'一度'):指示を接続(bound,指示を作る())
        with self.assertRaisesRegex(ValueError,'未実行'):指示を接続(replace(s,版=1),指示を作る())


if __name__=='__main__':unittest.main()

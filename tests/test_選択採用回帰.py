"""外部観測・評価器の境界を制御し、選択採用と通常循環の実コードを検査する。"""
from dataclasses import dataclass, replace
from types import SimpleNamespace
from unittest import TestCase
from unittest.mock import patch
import importlib
m=importlib.import_module('minidora.HDS選択継承循環')
from minidora.HDS実行主体 import HDS実行状態,HDS実行主体,HDS作用供給器,HDS終端
from minidora.統合駆動_v2.政策 import HDS運用政策

@dataclass(frozen=True)
class 試験質問IR:
 入力言語: str = 'ja'
 認知世界ID: str = 'world'

def 参照(本文='支持',ID='ref'):
 return m.参照記録(ID,'対象',本文,'試験','人工供給器',1.0)
def 回答(ラベル='A',証明=True):
 return m.HDS選択実行結果('APPROVE',ラベル,'候補'+ラベル,('CONTROLLED_EVALUATOR',),None,4,1,0,0,int(証明),0)
def 保留():
 return m.HDS選択実行結果('SUSPEND',None,None,('NO_KNOWLEDGE_EVIDENCE',),None,4,0,0,0,0,0)
def 供給(資料,評価):
 s=m.HDS選択継承供給.__new__(m.HDS選択継承供給)
 s.初期参照=tuple(資料);s.初期参照署名=m._参照署名(資料);s.質問IR=試験質問IR()
 s.候補意味IR={'A':'A','B':'B','C':'C','D':'D'};s.数量計算契約=SimpleNamespace(状態='不要')
 s.コンパイラ=SimpleNamespace(コンパイル=lambda x:x);s.選択肢=('A','B','C','D');s.設定=m.HDS選択継承設定(3)
 s.参照観測要求=();s.基礎能力核=None;s.模型核=object();s.既存能力継承=True;s.入力残差非阻害対象=frozenset()
 s.参照供給器=object();s.計算実行器=None;s.拡張採用証明=None;s._計算降下済み=None;s._評価=評価
 return s

def 状態(資料,基準=None,原資料=None):
 値={m.参照成果名:tuple(資料),m.参照世代成果名:0,m.関係観測世代成果名:0,m.関係観測消費成果名:(),m.計算済み成果名:False,m.参照記憶成果名:tuple(資料),m.参照取得診断成果名:()}
 if 原資料 is not None:値[m.初回評価参照成果名]=tuple(原資料)
 return HDS実行状態(目的=('候補を選ぶ',),要求状態=frozenset({m.選択閉包状態}),残差=frozenset({m.残差_未評価}),成果=tuple(値.items()),主体状態=((m.基準結果主体名,基準),) if 基準 is not None else ())

class 選択採用回帰(TestCase):
 def setUp(self):
  self.ps=[]
  self.差替('HDS入力資料本文',lambda r:r.内容)
  self.差替('_候補対象関係群',lambda q,c,label:(label,))
  self.差替('HDS内部言語状態',lambda ir,**kw:SimpleNamespace(証拠利用可=True,関係構造=(ir,)))
  self.差替('証拠状態照合',lambda targets,refs:SimpleNamespace(反証=int('反証'+targets[0] in refs),矛盾=0,未観測=int('支持' not in refs)))
  self.差替('HDS候補関係観測計画を構成',lambda *a,**kw:m.HDS候補関係観測計画((),3,0))
  self.差替('HDS既存能力直接反証評価',lambda *a,**kw:None)
  self.差替('_候補証拠優越',lambda *a,**kw:False)
 def 差替(self,k,v):
  p=patch.object(m,k,v);p.start();self.ps.append(p)
 def tearDown(self):
  for p in reversed(self.ps):p.stop()
 def 評価(self,s,作業状態):return s._評価作用(作業状態).実行(作業状態)
 def 循環(self,s,作業状態,上限=20):
  中核=HDS実行主体((),作用供給器=(HDS作用供給器('選択供給',s.構成,'unit'),),最大作用回数=上限,政策=HDS運用政策(自動形成=False))
  return 中核.実行(作業状態)
 def 観測設定(self,fn):
  self.差替('HDS追加参照検索',fn);self.差替('HDS追加参照統合上限',lambda *a:32)
  self.差替('HDS候補被覆優先統合',lambda a,b,*args:tuple(dict((r.識別子,r) for r in (*a,*b)).values()))
  self.差替('参照記録群を統合',lambda a,b:tuple(dict((r.識別子,r) for r in (*a,*b)).values()))
  self.差替('HDS追加観測要求群',lambda *a,**kw:('次層',))
 def test_他候補未観測でも根拠付き回答を保持(self):
  rs=(参照(),);x=self.評価(供給(rs,lambda r:回答()),状態(rs));self.assertEqual(dict(x.成果).get(m.回答成果名),'A')
 def test_追加資料なしでも既存根拠を保持(self):
  rs=(参照(),);x=self.評価(供給(rs,lambda r:回答()),状態(rs,回答(),rs));self.assertEqual(dict(x.成果).get(m.回答成果名),'A')
 def test_無関係な取得障害を一意回答の反証にしない(self):
  rs=(参照(),);st=replace(状態(rs),残差=frozenset({m.残差_未評価,m.残差_参照取得障害}));x=self.評価(供給(rs,lambda r:回答()),st);self.assertEqual(dict(x.成果).get(m.回答成果名),'A')
 def test_無根拠APPROVEを採用しない(self):
  rs=(参照('未観測'),);x=self.評価(供給(rs,lambda r:回答(証明=False)),状態(rs));self.assertNotIn(m.回答成果名,dict(x.成果))
 def test_採用候補の反証は保留する(self):
  rs=(参照('反証A'),);x=self.評価(供給(rs,lambda r:回答()),状態(rs));self.assertNotIn(m.回答成果名,dict(x.成果))
 def test_他候補の反証は採用候補と混同しない(self):
  rs=(参照('反証B'),);x=self.評価(供給(rs,lambda r:回答()),状態(rs));self.assertEqual(dict(x.成果).get(m.回答成果名),'A')
 def test_根拠訂正後に旧回答へ逃げない(self):
  old=(参照(),);rs=(参照('撤回'),);x=self.評価(供給(old,lambda r:保留()),状態(rs,回答(),old));self.assertNotIn(m.回答成果名,dict(x.成果))
 def test_訂正後の再証明で再採用する(self):
  old=(参照(),);rs=(参照('支持訂正版'),);x=self.評価(供給(old,lambda r:回答()),状態(rs,回答(),old));self.assertEqual(dict(x.成果).get(m.回答成果名),'A')
 def test_窓からの除外を証拠撤回にしない(self):
  old=(参照(),);rs=(参照('別資料','ref2'),);x=self.評価(供給(old,lambda r:保留()),状態(rs,回答(),old));self.assertEqual(dict(x.成果).get(m.回答成果名),'A')
 def test_新規証明を採用する(self):
  old=(参照('不明'),);rs=(参照('支持','ref2'),);x=self.評価(供給(old,lambda r:回答()),状態(rs,保留(),old));self.assertEqual(dict(x.成果).get(m.回答成果名),'A');self.assertTrue(dict(x.成果)[m.非退行判定成果名].拡張採用)
 def test_既存模型の一意閉包を能力継承として再採用する(self):
  old=(参照('不明'),);rs=(参照('支持','ref2'),)
  模型=SimpleNamespace(参照最有力候補ID='A',参照候補辞書=lambda:{'A':2.0,'B':1.0,'C':0.0,'D':0.0})
  実回答=replace(回答(証明=False),MINIDORA模型結果=模型)
  self.assertFalse(m._根拠付き承認(実回答));self.assertTrue(m._暫定採用可能(実回答))
  x=self.評価(供給(old,lambda r:実回答),状態(rs,保留(),old))
  self.assertEqual(dict(x.成果).get(m.回答成果名),'A')
  self.assertTrue(dict(x.成果)[m.非退行判定成果名].拡張採用)
 def test_暫定順位は必要観測が残る初回では確定しない(self):
  old=(参照('初期'),)
  模型=SimpleNamespace(参照最有力候補ID='A',参照候補辞書=lambda:{'A':2.0,'B':1.0,'C':0.0,'D':0.0})
  実回答=replace(回答(証明=False),MINIDORA模型結果=模型)
  s=供給(old,lambda r:実回答)
  判定=SimpleNamespace(一意成立=None,候補=(),学習提案=(),照合数=0,未完了=())
  s._目的関係評価=lambda _r:判定
  s._必要観測=lambda *_a,**_kw:(SimpleNamespace(),)
  x=self.評価(s,状態(old))
  self.assertNotIn(m.回答成果名,dict(x.成果))
  self.assertTrue(m.残差_候補証拠未閉包 in x.追加残差)

 def test_暫定順位は異なる参照で同一ラベル再現後に安定採用する(self):
  old=(参照('初期'),);new=(参照('初期'),参照('追加','new'))
  模型=SimpleNamespace(参照最有力候補ID='A',参照候補辞書=lambda:{'A':2.0,'B':1.0,'C':0.0,'D':0.0})
  実回答=replace(回答(証明=False),MINIDORA模型結果=模型)
  s=供給(old,lambda r:実回答)
  判定=SimpleNamespace(一意成立=None,候補=(),学習提案=(),照合数=0,未完了=())
  s._目的関係評価=lambda _r:判定
  s._必要観測=lambda *_a,**_kw:(SimpleNamespace(),)
  x=self.評価(s,状態(new,実回答,old))
  self.assertEqual(dict(x.成果).get(m.回答成果名),'A')
  self.assertIn('HDS_BASELINE_REOBSERVED_STABLE',x.理由)

 def test_選択APIは論理成果名を回答ラベルへ射影する(self):
  from minidora.入力系.選択契約 import 選択入力を接続
  入力=SimpleNamespace(目的=(),検証要求=(),残差=(),実行制約=(),
      要求成果=('計算結果','取得結果'),表現制約=SimpleNamespace(出力言語=None,要求=()))
  接続=選択入力を接続(入力)
  self.assertEqual(接続.成果対応,(('計算結果','成果:HDS選択:回答ラベル'),('取得結果','成果:HDS選択:回答ラベル')))
 def test_拡張証明拒否を守る(self):
  old=(参照('不明'),);rs=(参照('支持','ref2'),);s=供給(old,lambda r:回答());s.拡張採用証明=lambda *a:False;x=self.評価(s,状態(rs,保留(),old));self.assertNotIn(m.回答成果名,dict(x.成果))
 def test_優越証拠で変更できる(self):
  old=(参照(),);rs=(参照('支持','ref2'),);self.差替('_候補証拠優越',lambda *a,**kw:True);x=self.評価(供給(old,lambda r:回答('B')),状態(rs,回答(),old));self.assertEqual(dict(x.成果).get(m.回答成果名),'B')
 def test_証明なし変更では基準保持(self):
  old=(参照(),);rs=(参照('支持','ref2'),);x=self.評価(供給(old,lambda r:回答('B')),状態(rs,回答(),old));self.assertEqual(dict(x.成果).get(m.回答成果名),'A')
 def test_参照本文の同一性で構文化を再利用(self):
  rs=(参照(),);s=供給(rs,lambda r:回答());calls=[];s.コンパイラ.コンパイル=lambda x:(calls.append(x) or x)
  s._資料IR群(rs);s._資料IR群(rs);self.assertEqual(len(calls),1);s._資料IR群((参照('訂正'),));self.assertEqual(len(calls),2)
 def test_構文失敗を隠さない(self):
  s=供給((),lambda r:保留())
  def error(x):raise ValueError('unknown')
  s.コンパイラ.コンパイル=error;self.assertEqual(s._資料IR群((参照(),)),());self.assertTrue(s._資料診断)
 def test_表示値以外の意味変更を署名へ含める(self):
  r=replace(参照(),意味キー='値',値=1)
  for c in ({'内容':'変更'},{'時点':'翌日'},{'対象':'別対象'},{'範囲':'別範囲'}):
   with self.subTest(c=c):self.assertNotEqual(m._参照署名((r,)),m._参照署名((replace(r,**c),)))
 def test_候補外ラベル拒否(self):
  rs=(参照(),);x=self.評価(供給(rs,lambda r:回答('Z')),状態(rs));self.assertNotIn(m.回答成果名,dict(x.成果))
 def test_通常循環で成立回答を返す(self):
  rs=(参照(),);x=self.循環(供給(rs,lambda r:回答()),状態(rs));self.assertEqual(x.終端,HDS終端.採用,x.阻害履歴)
  self.assertEqual([h.作用ID for h in x.履歴],['HDS継承/模型再評価'])
 def test_通常循環で追加観測から再評価し採用(self):
  rs=(参照('不明'),);s=供給(rs,lambda r:回答() if any(x.内容=='支持' for x in r) else 保留())
  self.観測設定(lambda *a,**kw:(参照('支持','new'),));x=self.循環(s,状態(rs));self.assertEqual(x.終端,HDS終端.採用,(x.阻害履歴,[h.理由 for h in x.履歴]))
 def test_空振り観測は有限に終了する(self):
  rs=(参照('不明'),);s=供給(rs,lambda r:保留());calls=[];self.観測設定(lambda *a,**kw:(calls.append(1) or ()))
  x=self.循環(s,状態(rs));self.assertEqual(x.終端,HDS終端.保留,x.阻害履歴);self.assertEqual(len(calls),3)
 def test_第一層空でも第二層で証拠を回収(self):
  rs=(参照('不明'),);s=供給(rs,lambda r:回答() if any(x.内容=='支持' for x in r) else 保留());calls=[]
  def get(*a,**kw):
   calls.append(1);return () if len(calls)==1 else (参照('支持','new'),)
  self.観測設定(get);x=self.循環(s,状態(rs));self.assertEqual(x.終端,HDS終端.採用,(x.阻害履歴,[h.理由 for h in x.履歴]));self.assertEqual(len(calls),2)
 def test_無関係な必須残差は勝手に消さない(self):
  rs=(参照(),);st=replace(状態(rs),残差=frozenset({m.残差_未評価,'要求:承認未了'}));x=self.循環(供給(rs,lambda r:回答()),st)
  self.assertNotEqual(x.終端,HDS終端.採用);self.assertIn('要求:承認未了',x.状態.残差)

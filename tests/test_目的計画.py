"""人工素材の局所契約。計画成立と実行結果、有限対応と汎用能力を分離する。"""
from dataclasses import replace
from copy import deepcopy
import unittest
from minidora.統合実行 import 統合セッション
from minidora.能力意味カタログ import 能力意味カタログ
from minidora.目的計画 import 目的計画器
from minidora.汎用要求IR import 汎用要求IR, 目的指定
from minidora.製品版.型 import 能力結果


def 要求(effect='定数値', kind='数式', value=None, args=None):
    value = value if value is not None else 能力結果(True, '2+3', データ={'式': '2+3', '変数': []})
    return 汎用要求IR('成果を求める', {'a': value}, {'a': kind},
        (目的指定('g', 'a', effect, 'p', (0, 6)),), {'p': args or {}}, ('g',))

class 目的計画契約試験(unittest.TestCase):
    def setUp(self):
        self.s = 統合セッション('目的契約')
        self.catalog = 能力意味カタログ(self.s.能力一覧())
        self.p = 目的計画器(self.catalog)

    def execute(self, req):
        r = self.p.計画する(req)
        self.assertTrue(r.成立, r.理由)
        value = self.s.計画実行(r.計画, r.Data, 依頼文=req.原文)
        self.assertTrue(value.成立, value.理由)
        return r, value

    def test_29能力の名前版作用境界が一致(self):
        self.assertEqual(len(self.catalog.記述), 29)
        self.assertEqual(sum(r.外部読取 for r in self.catalog.記述), 2)
        self.assertTrue(all(r.限界 for r in self.catalog.記述))

    def test_能力版変更を暗黙適用しない(self):
        rows = list(self.s.能力一覧()); rows[0] = {**rows[0], '版': '未監査版'}
        with self.assertRaises(ValueError): 能力意味カタログ(rows)

    def test_外部属性の変更を拒否(self):
        rows = list(self.s.能力一覧()); rows[0] = {**rows[0], '外部読取': True}
        with self.assertRaises(ValueError): 能力意味カタログ(rows)

    def test_重複能力を拒否(self):
        with self.assertRaises(ValueError): 能力意味カタログ((*self.s.能力一覧(), self.s.能力一覧()[0]))

    def test_定数値から二工程を生成(self):
        r, value = self.execute(要求())
        self.assertEqual(r.作用経路[0][1], ('式正規化', '定数採用'))
        self.assertEqual(value.本文, '5')

    def test_JSON指定数値から三工程を生成(self):
        r, value = self.execute(要求('文書単一値', 'JSON原文', 能力結果(True, '{"a":7,"b":90}'), {'位置': '/a', '型': '数値'}))
        self.assertEqual(r.作用経路[0][1], ('JSON読取', 'JSON位置選択', '単一値取出'))
        self.assertEqual(value.本文, '7')

    def test_CSVから型を保ったJSONを生成(self):
        _, value = self.execute(要求('JSON変換文書', 'CSV原文', 能力結果(True, 'a,b\n7,8\n')))
        self.assertEqual(value.本文, '[{"a":"7","b":"8"}]')

    def test_型だけで未知能力を生成しない(self):
        r = self.p.計画する(要求('売上低下の原因'))
        self.assertFalse(r.成立); self.assertIsNone(r.計画)

    def test_欠落した引数を補完しない(self):
        r = self.p.計画する(要求('微分結果'))
        self.assertFalse(r.成立)

    def test_未知制約を捨てない(self):
        r = self.p.計画する(要求(args={'整数だけ': True}))
        self.assertFalse(r.成立)

    def test_計画時に能力も会話更新も起こらない(self):
        before = self.s.保存文脈()
        r = self.p.計画する(要求())
        self.assertTrue(r.成立); self.assertEqual(before, self.s.保存文脈())
        self.assertEqual(self.s.再利用統計()['能力別'], {})

    def test_入力Data変更は既成計画に波及しない(self):
        req = 要求(); r = self.p.計画する(req)
        req.素材['a'].データ['式'] = '99'
        self.assertEqual(r.Data['素材:a'].データ['式'], '2+3')

    def test_残差付き要求は停止(self):
        self.assertFalse(self.p.計画する(replace(要求(), 残差=('条件未解決',))).成立)

    def test_不成立素材は停止(self):
        self.assertFalse(self.p.計画する(要求(value=能力結果(False, '2'))).成立)

    def test_型宣言欠落は停止(self):
        self.assertFalse(self.p.計画する(replace(要求(), 素材種別={})).成立)

    def test_原文範囲のboolを拒否(self):
        req = 要求(); g = replace(req.目的[0], 原文範囲=(False, 6))
        self.assertFalse(self.p.計画する(replace(req, 目的=(g,))).成立)

    def test_目的循環は停止(self):
        req = 要求(); g = replace(req.目的[0], 対象='g')
        self.assertFalse(self.p.計画する(replace(req, 目的=(g,))).成立)

    def test_出力に繋がらない目的を捨てない(self):
        req = 要求(); g = replace(req.目的[0], 識別子='h', 引数参照='q')
        self.assertFalse(self.p.計画する(replace(req, 目的=(*req.目的,g), 引数Data={'p':{},'q':{}})).成立)

    def test_対象欠落は停止(self):
        req=要求();g=replace(req.目的[0],対象='不在')
        self.assertFalse(self.p.計画する(replace(req,目的=(g,))).成立)

    def test_出力不正は停止(self):
        self.assertFalse(self.p.計画する(replace(要求(),出力目的=('不在',))).成立)

    def test_未使用の引数を拒否(self):
        self.assertFalse(self.p.計画する(replace(要求(),引数Data={'p':{},'余計':{}})).成立)

    def test_探索予算を超えた候補は成功としない(self):
        p=目的計画器(self.catalog,最大展開数=1)
        self.assertFalse(p.計画する(要求()).成立)

    def test_必要経路禁止なら不成立(self):
        self.assertFalse(self.p.計画する(要求(),禁止作用=('定数採用',)).成立)

    def test_不明な禁止作用は拒否(self):
        self.assertFalse(self.p.計画する(要求(),禁止作用=('存在しない',)).成立)

    def test_別対象の結果で目的を満たさない(self):
        req=要求();g=replace(req.目的[0],識別子='h',対象='b',引数参照='q')
        req=replace(req,素材={**req.素材,'b':能力結果(True,'8',データ={'式':'8','変数':[]})},
                    素材種別={'a':'数式','b':'数式'},目的=(*req.目的,g),引数Data={'p':{},'q':{}},出力目的=('g','h'))
        r,value=self.execute(req)
        self.assertEqual([v.本文 for _,v in value.出力],['5','8'])

    def test_同じ出力型でも操作を省略しない(self):
        req=要求('微分結果',value=能力結果(True,'x**3',データ={'式':'x**3','変数':['x']}),args={'変数':'x'})
        g=目的指定('h','g','微分結果','q',(0,6))
        req=replace(req,目的=(*req.目的,g),引数Data={'p':{'変数':'x'},'q':{'変数':'x'}},出力目的=('h',))
        r,value=self.execute(req)
        self.assertEqual(value.本文,'6*x')
        self.assertEqual(len(r.計画.工程),2)

    def test_積分の任意定数を正規化で消して採用しない(self):
        from minidora.記号演算 import 記号を処理
        value=記号を処理('0',('x',),操作='積分',対象変数='x')
        self.assertFalse(self.p.計画する(要求('定数値','積分結果',value)).成立)

    def test_型宣言が偽でも実行段階で拒否(self):
        req=要求('定数値','数式',能力結果(True,'not math'))
        r=self.p.計画する(req);self.assertTrue(r.成立)
        before=self.s.保存文脈()
        result=self.s.計画実行(r.計画,r.Data)
        self.assertFalse(result.成立);self.assertEqual(before,self.s.保存文脈())

    def test_一次式を定数値として採用しない(self):
        req=要求(value=能力結果(True,'x+1',データ={'式':'x+1','変数':['x']}))
        r=self.p.計画する(req);self.assertTrue(r.成立)
        result=self.s.計画実行(r.計画,r.Data)
        self.assertFalse(result.成立)

    def test_コード本文の構造読解(self):
        _,value=self.execute(要求('コード構造報告','コード本文',能力結果(True,'def f(x):\n    return x + 1\n')))
        self.assertTrue(value.成立)

    def test_構造化仕様から生成と評価を自動接続(self):
        spec = {'名前':'inc','引数':['x'],'手順':[{'種別':'返却','式':{
            '種別':'算術','演算':'加算','左':{'種別':'参照','名前':'x'},
            '右':{'種別':'定数参照','キー':'step'}}}]}
        value = 能力結果(True,'',データ={'仕様':spec,'定数':{'step':1}})
        r,result = self.execute(要求('コード評価結果','コード仕様',value,
                                    {'引数':{'x':2,'定数':{'step':1}}}))
        self.assertEqual(r.作用経路[0][1],('仕様からコード生成','コード引数評価'))
        self.assertEqual(result.本文,'3')

    def test_許可の整数偽装を拒否(self):
        rows=list(self.s.能力一覧()); rows[0]={**rows[0],'外部読取':0}
        with self.assertRaises(ValueError): 能力意味カタログ(rows)

if __name__ == '__main__': unittest.main()

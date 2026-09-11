"""第19バッチ。実HDS・実能力で数量集合と会話の接続を確認する。"""
from copy import deepcopy
from dataclasses import replace
from fractions import Fraction
import json
import unittest
from minidora.汎用会話 import 汎用会話セッション
from minidora.製品版.型 import 能力結果
from minidora.会話解釈 import 会話を解釈, HDS会話を照合
from minidora.会話句 import 句を分割
from minidora.会話回答 import 回答記録整合
from minidora.数量集合 import 集合記録整合, 数量群を処理, 有理数を表記
from minidora.応答構成 import 能力結果を復元
from minidora.会話意味 import 意味指紋
from minidora.hds_compiler import 公開HDSコンパイラ
from minidora.hds_ir import HDS残差


def 資料(values=(75,60,95), *, unit='円', nested=False):
    result={}
    for i,value in enumerate(values):
        data={'売上':value,'費用':i+1}
        if unit: data['単位']=unit
        if nested: data={'箱':data}
        result[chr(65+i)]=能力結果(True,json.dumps(data,ensure_ascii=False))
    return result

Q='この3つの売上の合計と平均を円で教えて'

class 集合会話試験(unittest.TestCase):
    def setUp(self): self.s=汎用会話セッション('集合動作')
    def ok(self,q=Q,data=None):
        r=self.s.応答(q,data)
        self.assertTrue(r.成立,(r.理由,r.追跡))
        self.assertTrue(回答記録整合(r.結果))
        return r
    def group(self,r): return r.結果.データ['元結果'][0]['データ']
    def test_三資料の合計と厳密平均(self):
        d=self.group(self.ok(data=資料()))
        self.assertEqual(d['集約']['合計'],'230');self.assertEqual(d['集約']['平均'],'230/3')
    def test_三資料比較を計画から実行する(self):
        r=self.ok('資料「A」と資料「B」と資料「C」の売上を比較して',資料())
        self.assertIn('差は35円',r.本文)
        self.assertEqual(self.group(r)['順位'],[{'対象':2,'順位':1},{'対象':0,'順位':2},{'対象':1,'順位':3}])
    def test_同値を任意の勝敗にしない(self):
        r=self.ok('全資料の売上を比較して',資料((75,75,60)))
        self.assertEqual([x['順位'] for x in self.group(r)['順位']],[1,1,3])
    def test_最大の同値対象を全て返す(self):
        r=self.ok('全資料の売上の最大値は？',資料((75,75,60)))
        self.assertIn('該当：資料「A」、資料「B」',r.本文)
    def test_負数を含む合計(self):
        self.assertEqual(self.group(self.ok(data=資料((-1,-2,0))))['集約']['合計'],'-3')
    def test_小数を浮動小数の丸めで変えない(self):
        self.assertEqual(self.group(self.ok(data=資料((0.1,0.2,0.3))))['集約']['平均'],'0.2')
    def test_全八資料と個別入れ子の回復(self):
        r=self.ok('全資料の売上の合計と平均は？',資料(tuple(range(1,9)),nested=True))
        self.assertEqual(self.group(r)['集約']['合計'],'36')
        self.assertEqual(len(r.追跡['試行']),9)
        self.assertEqual(len(self.s.統合.採用履歴スナップショット()[1]),1)
        self.assertEqual(len({x['目的印'] for x in r.追跡['試行']}),1)
    def test_九対象を八対象へ切り捨てない(self):
        self.assertFalse(self.s.応答('全資料の売上の合計は？',資料(tuple(range(9)))).成立)
        self.assertEqual(self.s.統合.採用履歴スナップショット()[1],())
    def test_同一資料三時点の読取を共有(self):
        r=self.ok('資料「表」の2024年と2025年と2026年の売上の平均は？',
            {'表':能力結果(True,'年,売上,単位\n2024,2,円\n2025,3,円\n2026,5,円')})
        self.assertIn('10/3円',r.本文)
        self.assertEqual([x[2] for x in r.追跡['試行'][0]['工程作用']].count('構造文書読取'),1)
    def test_年と条件を共通の入力役割へ束縛(self):
        data={n:能力結果(True,f'年,売上,単位,条件\n2024,999,円,国内\n2025,{v},円,国内\n2025,888,円,海外') for n,v in [('A',2),('B',3),('C',5)]}
        r=self.ok('全資料の売上の合計は？2025年だけ。条件「国内」で。',data)
        self.assertIn('10円',r.本文);self.assertIn('国内',r.本文);self.assertNotIn('999円',r.本文)
    def test_条件句の順序を変更しても同じ成果(self):
        a=汎用会話セッション('a').応答('全資料の売上の合計は？表で。単位は円です。',資料())
        b=汎用会話セッション('b').応答('単位は円です。表で。全資料の売上の合計は？',資料())
        self.assertTrue(a.成立,a.理由);self.assertTrue(b.成立,b.理由);self.assertEqual(a.本文,b.本文)
    def test_句頭の表示単位(self):
        self.assertIn('230円',self.ok('円で、全資料の売上の合計は？',資料()).本文)
    def test_表で値と選別結果を表示(self):
        r=self.ok(Q+'。表で。値が70円以上だけ',資料())
        self.assertIn('| 資料「B」 | 60 | 条件外 |',r.本文)
        self.assertIn('170円',r.本文);self.assertIn('85円',r.本文)
    def test_同次元の閾値へ換算して選別(self):
        data={n:能力結果(True,json.dumps({'電圧':v,'単位':u})) for n,v,u in [('A',1000,'mV'),('B',2,'V'),('C',3000,'mV')]}
        r=self.ok('全資料の電圧の合計をmVで教えて。値が2V以上だけ',data)
        self.assertEqual(self.group(r)['表示集約']['合計'],'5000')
    def test_六比較演算を境界値で対照(self):
        expected={'以上':[1,2],'以下':[0,1],'未満':[0],'超':[2],'と一致':[1],'と不一致':[0,2]}
        for op,indices in expected.items():
            with self.subTest(op=op):
                r=汎用会話セッション(op).応答('全資料の売上を一覧にして。値が2円'+op+'だけ',資料((1,2,3)))
                self.assertTrue(r.成立,r.理由);self.assertEqual(self.group(r)['採用対象'],indices)
    def test_除外した資料を集計と依存から外す(self):
        r=self.ok('全資料の売上の合計は？資料「B」を除いて',資料())
        self.assertEqual(self.group(r)['集約']['合計'],'170')
        self.assertIn('要求で除外：資料「B」',r.本文)
        self.s.応答('資料「B」を更新:{"売上":999,"単位":"円"}')
        self.assertTrue(self.s.状態()['最後の成果有効'])
    def test_存在しない除外を無視しない(self):
        self.assertFalse(self.s.応答(Q+'。資料「Z」を除いて',資料()).成立)
    def test_全除外をゼロ合計へしない(self):
        self.assertFalse(self.s.応答(Q+'。資料「A」を除いて。資料「B」を除いて。資料「C」を除いて',資料()).成立)
    def test_空の選別一覧はゼロ件という診断(self):
        r=self.ok('全資料の売上の一覧と件数は？値が1000円以上だけ',資料())
        self.assertEqual(self.group(r)['集約'],{'件数':0})
    def test_空集合の平均を生成しない(self):
        r=self.s.応答(Q+'。値が1000円以上だけ',資料())
        self.assertFalse(r.成立);self.assertEqual(self.s.統合.採用履歴スナップショット()[1],())
    def test_一対象の比較を無理に成立させない(self):
        self.assertFalse(self.s.応答('全資料の売上を比較して。値が90円以上だけ',資料()).成立)
    def test_違う属性の条件を適用しない(self):
        self.assertFalse(self.s.応答(Q+'。ただし「費用」が1円以上だけ',資料()).成立)
    def test_閾値の異次元を拒否(self):
        self.assertFalse(self.s.応答(Q+'。値が1V以上だけ',資料()).成立)
    def test_矛盾する条件を後勝ちにしない(self):
        self.assertFalse(self.s.応答(Q+'。単位はVです',資料()).成立)
    def test_未対応の否定条件を削除しない(self):
        self.assertFalse(self.s.応答(Q+'。ただし集計しないで',資料()).成立)
        self.assertEqual(self.s.統合.再利用統計()['能力別'],{})
    def test_未対応の原因推定を後半から切らない(self):
        self.assertFalse(self.s.応答(Q+'。原因を断定して',資料()).成立)
        self.assertEqual(self.s.統合.採用履歴スナップショット()[1],())
    def test_単位確認から集合目的を再開する(self):
        r=self.s.応答('全資料の売上の合計と平均は？',資料(unit=''))
        self.assertEqual(r.状態,'確認待ち')
        self.assertIn('230円',self.ok('単位は円です').本文)
    def test_属性訂正で再計算する(self):
        old=self.ok(data=資料());new=self.ok('訂正:属性は費用です')
        self.assertEqual(self.group(new)['集約']['合計'],'6');self.assertIn('売上',old.本文)
    def test_全対象の年確認を共通条件へ戻す(self):
        data={n:能力結果(True,f'年,売上,単位\n2024,999,円\n2025,{v},円') for n,v in [('A',1),('B',2),('C',3)]}
        self.assertEqual(self.s.応答('全資料の売上の合計は？',data).状態,'確認待ち')
        self.assertIn('6円',self.ok('年は2025です').本文)
    def test_資料更新で集合成果は失効(self):
        self.ok(data=資料());self.s.応答('資料「C」を更新:{"売上":1,"単位":"円"}')
        self.assertFalse(self.s.応答('それを詳しく説明して').成立)
    def test_再表現しても平均の厳密値と条件を保持(self):
        self.ok(data=資料());r=self.ok('それを表にして')
        self.assertIn('| 資料',r.本文);self.assertIn('230/3円',r.本文)
        detailed=self.ok('それを詳しく説明して');self.assertIn('| 資料',detailed.本文);self.assertIn('原文「75」',detailed.本文)
    def test_計算手順が原成果から導出される(self):
        self.ok(data=資料());r=self.ok('計算過程も説明して')
        self.assertIn('(75) + (60) + (95)',r.本文);self.assertIn('平均 = 合計 / 3',r.本文)
    def test_資料名の表記をMarkdown列にしない(self):
        data={'東|部':資料()['A'],'西':資料()['B'],'南':資料()['C']}
        r=self.ok('全資料の売上の合計は？表で',data)
        self.assertIn('東\\|部',r.本文)
    def test_意味IRに各演算の根拠依存が残る(self):
        d=self.group(self.ok(data=資料()))
        mean=next(x for x in d['生成関係'] if x['ID']=='演算:平均')
        self.assertEqual(mean['依存'],['数量:0','数量:1','数量:2'])
    def test_停止後に成果も資料も更新しない(self):
        r=self.s.応答(Q,資料(),停止要求=lambda:True)
        self.assertEqual(r.状態,'中止');self.assertEqual(self.s.状態()['資料版'],{})
    def test_異なる条件の数量を平均しない(self):
        data=資料();data['B']=能力結果(True,'{"売上":60,"単位":"円","条件":"別条件"}')
        self.assertFalse(self.s.応答(Q,data).成立)
    def test_無断で異時点を集約しない(self):
        data=資料();data['B']=能力結果(True,'{"売上":60,"単位":"円","年":2025}')
        self.assertFalse(self.s.応答(Q,data).成立)
    def test_誤ったJSON型を別経路で数値に変えない(self):
        data=資料();data['C']=能力結果(True,'{"売上":"95","単位":"円"}')
        r=self.s.応答(Q,data);self.assertFalse(r.成立);self.assertEqual(len(r.追跡['試行']),1)
    def test_未解釈の注記を平均から捨てない(self):
        data=資料();data['C']=能力結果(True,'{"売上":95,"単位":"円","備考":"暫定"}')
        self.assertFalse(self.s.応答(Q,data).成立)
    def test_名前付きの集合に同じ対象を二回入れない(self):
        self.assertFalse(self.s.応答('資料「A」と資料「B」と資料「A」の売上の合計は？',資料()).成立)
    def test_未知HDS残差を新しい集合でも免除しない(self):
        req=会話を解釈(Q,('A','B','C'));ir=公開HDSコンパイラ().コンパイル(Q)
        bad=replace(ir,残差=(*ir.残差,HDS残差('bad','semantic_loss','条件','未解釈')))
        with self.assertRaises(ValueError):HDS会話を照合(bad,req)
    def test_引用中の疑問符を句境界にしない(self):
        text='資料「何？これ！」の売上の合計は？表で'
        spans=list(句を分割(text))
        self.assertEqual([text[a:b] for a,b in spans],['資料「何？これ！」の売上の合計は','表で'])
    def test_引用の不整合を無視しない(self):
        with self.assertRaises(ValueError):list(句を分割('「未閉鎖'))
    def test_平均は分母に応じた厳密表記(self):
        self.assertEqual(有理数を表記(Fraction(1,3)),'1/3')
        self.assertEqual(有理数を表記(Fraction(-1,8)),'-0.125')
    def test_集合出力の出典削除を検出(self):
        r=self.ok(data=資料());value=能力結果を復元(r.結果.データ['元結果'][0])
        self.assertFalse(集合記録整合(replace(value,参照=())))
    def test_回答の出典削除を検出(self):
        r=self.ok(data=資料());self.assertFalse(回答記録整合(replace(r.結果,参照=())))
    def test_回答の根拠欄削除を検出(self):
        r=self.ok(data=資料());self.assertFalse(回答記録整合(replace(r.結果,根拠=())))
    def test_計算値とhashだけ改変しても原結果から検出(self):
        r=self.ok(data=資料());value=能力結果を復元(r.結果.データ['元結果'][0])
        value.データ['集約']['平均']='0'
        raw=deepcopy(value.データ);raw.pop('記録SHA256');value.データ['記録SHA256']=意味指紋(raw)
        self.assertFalse(集合記録整合(value))

    def test_成果参照と計算過程要求を別の句として扱う(self):
        self.ok(data=資料())
        r=self.s.応答('その結果の計算過程も説明して')
        self.assertTrue(r.成立,r.理由);self.assertIn('処理手順',r.本文)

if __name__=='__main__':unittest.main()

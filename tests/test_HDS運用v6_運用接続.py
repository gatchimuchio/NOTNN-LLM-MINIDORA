"""v6意味構成を通常HDS・原記録・知識取得・保存に接続した受入試験。"""
from copy import deepcopy
import json
import unittest
from minidora.HDS運用 import HDS運用セッション
from minidora.HDS運用.値 import 開封, 封緘, 結果を復元, 結果を保存
from minidora.HDS運用.関係内容 import 関係回答を検査
from test_HDS運用v5_運用接続 import 試験供給

質問 = '資料「手順」をもとに、担当Aが書類を担当Bに送るかどうか説明して'
規則 = '担当Aが書類を読むなら担当Aは担当Bに書類を送る（ただし、装置Aが停止する場合を除く）。'
通常 = '担当Aは書類を読みます。装置Aは停止しない。' + 規則


class 意味運用試験(unittest.TestCase):
    def 会話(self, 本文=通常, **設定):
        s = HDS運用セッション('v6意味試験', **{'手順形成': False, **設定})
        self.assertTrue(s.資料を登録('手順', 本文).成立)
        return s

    def 成功(self, s, 文=質問, **設定):
        r = s.応答(文, **設定)
        self.assertTrue(r.成立, r.本文); self.assertEqual(r.状態, 'COMMIT')
        return r

    def 構造(self, s):
        結果 = 結果を復元(開封(json.loads(s.保存()))['前回結果'])
        self.assertTrue(関係回答を検査(結果))
        return 結果.データ['構造']

    def test_格役割と例外を既存四工程で実導出する(self):
        s = self.会話(); r = self.成功(s)
        self.assertEqual({行['能力'] for 行 in r.追跡['能力試行']},
                         {'資料関係読解', '関係内容構成', '文章作成', '関係文章照合'})
        x = self.構造(s)['資料群']['手順']
        self.assertEqual(x['判定']['判定'], '支持')
        self.assertTrue(x['例外監査'][0]['採用'])
        self.assertIn('条件適用', r.本文); self.assertIn('書類を担当Bに送る', r.本文)
        self.assertIn('例外', r.本文)

    def test_例外不明は質問を支持せず説明だけ完了する(self):
        s = self.会話('担当Aは書類を読む。' + 規則); r = self.成功(s)
        x = self.構造(s)['資料群']['手順']
        self.assertEqual(x['判定']['判定'], '未確定'); self.assertFalse(x['例外監査'][0]['採用'])
        self.assertIn('未確定', r.本文); self.assertNotIn('判定：支持', r.本文)

    def test_例外矛盾を無視せず原文と規則を残す(self):
        s = self.会話(通常 + '装置Aは停止する。'); r = self.成功(s)
        x = self.構造(s)['資料群']['手順']
        self.assertEqual(x['判定']['判定'], '未確定')
        self.assertEqual(x['例外監査'][0]['独立判定']['判定'], '矛盾')
        self.assertIn('ただし', r.本文); self.assertIn('装置A', r.本文)

    def test_例外の更新で旧支持が失効し再作用で未確定になる(self):
        s = self.会話(); self.成功(s)
        self.assertTrue(s.資料を登録('手順', '担当Aは書類を読む。' + 規則, 更新=True).成立)
        self.assertFalse(s.状態()['前回有効']); self.assertFalse(s.応答('文章にして').成立)
        self.成功(s, '再計算して')
        self.assertEqual(self.構造(s)['資料群']['手順']['判定']['判定'], '未確定')
        self.assertTrue(HDS運用セッション.復元(s.保存()).状態()['前回有効'])

    def test_保存と再表現は原文と意味構造を変えない(self):
        s = self.会話(); self.成功(s); old = self.構造(s)
        t = HDS運用セッション.復元(s.保存()); self.成功(t, '文章にして')
        self.assertEqual(self.構造(t), old)
        self.成功(t, '引用形式にして'); self.assertEqual(self.構造(t), old)

    def test_例外監査の改変を再封緘でも拒否する(self):
        s = self.会話(); self.成功(s)
        保存 = 開封(json.loads(s.保存()))
        # 保存形式の辞書を介さず能力結果の構造そのものを改変する。
        結果 = 結果を復元(保存['前回結果'])
        結果.データ['構造']['資料群']['手順']['例外監査'][0]['採用'] = False
        self.assertFalse(関係回答を検査(結果))
        保存['前回結果'] = 結果を保存(結果)
        with self.assertRaises(ValueError):
            HDS運用セッション.復元(json.dumps(封緘(保存), ensure_ascii=False))

    def test_役割を交換した事実は根拠にならない(self):
        s = self.会話('担当Bは書類を担当Aに送ります。'); self.成功(s)
        self.assertEqual(self.構造(s)['資料群']['手順']['判定']['判定'], '未確定')

    def test_複数資料を同名だけで結合しない(self):
        s = self.会話('担当Aは書類を読みます。')
        self.assertTrue(s.資料を登録('別記', '装置Aは停止しない。' + 規則).成立)
        self.成功(s, '登録資料から担当Aが書類を担当Bに送るかどうか説明して')
        self.assertEqual({行['判定']['判定'] for 行 in self.構造(s)['資料群'].values()}, {'未確定'})

    def test_必要条件の逆向き推論を通常入口でもしない(self):
        s = self.会話('装置Aが稼働するためには、装置Aは有効であることが必要です。装置Aは有効である。')
        self.成功(s, '資料「手順」から装置Aが稼働するかどうか説明して')
        self.assertEqual(self.構造(s)['資料群']['手順']['判定']['判定'], '未確定')

    def test_新しい意味結果を純粋手順として形成する(self):
        s = self.会話(手順形成=True); self.成功(s)
        self.assertTrue(開封(json.loads(s.保存()))['形成手順'])
        self.成功(s, '再計算して')
        self.assertEqual(self.構造(s)['資料群']['手順']['判定']['判定'], '支持')

    def test_取得本文の格役割を再読解し再表現で再通信しない(self):
        b = 試験供給('担当Aは担当Bに書類を送ります。')
        s = self.会話('装置Cは停止する。', 外部読取許可=True, 取得器=b.接続())
        self.成功(s, 質問 + '、不足は公開資料で調べて', 外部読取許可=True)
        構造 = self.構造(s)
        self.assertEqual(構造['資料群']['手順']['判定']['判定'], '未確定')
        self.assertEqual({行['判定']['判定'] for 行 in 構造['公開資料群'].values()}, {'支持'})
        self.assertEqual(b.呼出[0][1], '担当Aが書類を担当Bに送る')
        数 = len(b.呼出)
        t = HDS運用セッション.復元(s.保存(), 外部読取許可=True, 取得器=b.接続())
        self.成功(t, '文章にして'); self.assertEqual(len(b.呼出), 数)

    def test_内部の例外や本文を検索語へ流出させない(self):
        b = 試験供給('担当Aは書類を担当Bに送る。')
        s = self.会話('担当Aは書類を読む。秘密装置XYZは有効である。' + 規則,
                      外部読取許可=True, 取得器=b.接続())
        self.成功(s, 質問 + '、不足は公開資料で調べて', 外部読取許可=True)
        self.assertTrue(b.呼出)
        for 種, 内容 in b.呼出:
            if 種 == '検索':
                self.assertNotIn('秘密', 内容); self.assertNotIn('停止', 内容)

    def test_停止要求と表示予算を採用へすり替えない(self):
        s = self.会話()
        self.assertFalse(s.応答(質問, 停止要求=lambda: True).成立)
        self.assertFalse(s.応答(質問 + '、100文字以内で').成立)


if __name__ == '__main__': unittest.main()

"""依頼の実解釈・命題の実導出・原要求照合。期待値と実行入力を分離する。"""
from copy import deepcopy
import json
import unittest

from minidora.依頼表層 import 依頼外形を分離, 表層対応を検査
from minidora.監査改善会話解釈 import 改善発話を解釈
from minidora.監査改善会話 import 監査改善会話セッション
from minidora.監査改善接続 import 拡張命題を検討, 拡張命題報告を検査, 改善回答を構成, 改善回答を検査
from minidora.命題解釈 import 命題を読む, 命題を表現
from minidora.明示別名 import 別名宣言を分離, 別名対応を構成, 別名を適用


def 命題報告(body, question='太郎は哺乳類である'):
    return 拡張命題を検討({'資料': [{'名前': '分類', '本文': body}], '問い': question})


def 会話():
    s=監査改善会話セッション('第25')
    assert s.応答('命題資料「例」を登録：P。PならばQ。').成立
    return s


class 依頼境界試験(unittest.TestCase):
    def test_語尾と接続の組合せを既存意味へ写す(self):
        for link in ('から','に基づいて','に基づき','をもとに','を基に'):
            for verb in ('判断','判定'):
                for ending in ('して','してください','して下さい','してくれる？','してもらえる？',
                               'してくれますか？','してもらえますか？','していただけますか？','してほしい'):
                    raw=f'資料「例」{link}「Q」を{verb}{ending}'
                    with self.subTest(入力=raw):
                        c=改善発話を解釈(raw)
                        self.assertEqual(c['行為'],'検討');self.assertEqual(c['変更'],{'問い':'Q'})
                        self.assertEqual(c['原文'],raw)
                        if '表層対応' in c:
                            self.assertTrue(表層対応を検査(raw,c['表層対応']))

    def test_引用を変形しない(self):
        for quote in ('「','『'):
            close='」' if quote=='「' else '』'
            raw=f'資料{quote}判断して、短く説明して{close}に基づいて{quote}PまたはQ{close}を判断してくれる？'
            c=改善発話を解釈(raw)
            self.assertEqual(c['資料'],'判断して、短く説明して')
            self.assertEqual(c['変更']['問い'],'PまたはQ')

    def test_登録本文を射影しない(self):
        raw='命題資料「例」を登録：太郎は「判断して、短く説明して」と述べた。'
        projected=依頼外形を分離(raw)
        self.assertEqual(projected['射影文'],raw)
        self.assertEqual(projected['対応'],[])

    def test_表層対応の改変を検出する(self):
        raw='資料「例」に基づいて「Q」を判断してくれる？'
        original=依頼外形を分離(raw)
        for key,value in (('射影文','資料「例」から「P」を判定して'),('版','別版'),('表示',{'詳細':False})):
            row=deepcopy(original);row[key]=value
            self.assertFalse(表層対応を検査(raw,row))
        row=deepcopy(original);row['対応'][0]['開始']=1
        self.assertFalse(表層対応を検査(raw,row))

    def test_複合要求は表示条件だけを合成する(self):
        for join in ('、',',','。','\n'):
            for display in ('短く説明して','簡潔に説明してください','詳細に説明してくれる？'):
                raw='資料「例」から「Q」を判断して'+join+display
                c=改善発話を解釈(raw)
                self.assertEqual(c['原文'],raw)
                self.assertEqual(c['詳細'],display.startswith('詳細'))
                self.assertEqual(len(c['表層対応']['対応']),2)

    def test_未知条件と否定を落とさない(self):
        for suffix in ('、否定を無視して','、ただしQでない場合は除く','、根拠なしでも答えて',
                       '、短く説明して、詳しく説明して','、短く説明して、短く説明して',
                       '、外に送信して','、','、、短く説明して','、もう少し短く説明して'):
            with self.subTest(条件=suffix):
                with self.assertRaises(ValueError):
                    改善発話を解釈('資料「例」から「Q」を判断して'+suffix)
        for verb in ('判断しないで','判断してはいけない','判定しなくてよい','判断して、翻訳して'):
            with self.assertRaises(ValueError):改善発話を解釈('資料「例」から「Q」を'+verb)

    def test_引用しない問いは実命題文法を通す(self):
        for raw in ('資料「例」からQと言える？','資料「例」からQと言えるか？',
                    '資料「例」に基づいてQと言える？'):
            self.assertEqual(改善発話を解釈(raw)['変更'],{'問い':'Q'})
        with self.assertRaises(ValueError):
            改善発話を解釈('資料「例」からQと言える？ただし反例を無視する')

    def test_引用の不整合と過大入力を拒否(self):
        for text in ('資料「例」から「Qを判断して','資料「例』から「Q」を判断して', '', 'あ'*8193):
            with self.assertRaises(ValueError):改善発話を解釈(text)


class 会話接続試験(unittest.TestCase):
    def test_言い換えを実三工程で完遂する(self):
        for raw in ('資料「例」から「Q」を判断して','資料「例」から「Q」を判定してくれる？',
                    '資料「例」に基づいて「Q」を判断してください','資料「例」からQと言える？'):
            s=会話();r=s.応答(raw)
            self.assertTrue(r.成立,r.本文)
            self.assertEqual(r.結果.データ['報告']['状態'],'支持')
            self.assertEqual(len(r.追跡['工程作用']),3)
            self.assertEqual(s.状態()['最後目的']['起点発話'],raw)

    def test_一括短縮と相対再表示(self):
        s=会話();r=s.応答('資料「例」から「Q」を判断して、短く説明して')
        self.assertTrue(r.成立,r.本文);self.assertFalse(r.結果.データ['詳細'])
        s0=s.状態();r=s.応答('もう少し短く説明して')
        self.assertFalse(r.成立);self.assertEqual(s0['成果'],s.状態()['成果'])
        r=s.応答('もう少し詳しく説明して');self.assertTrue(r.成立,r.本文)
        self.assertTrue(r.結果.データ['詳細'])
        r=s.応答('もう少し短く説明して');self.assertTrue(r.成立,r.本文)
        self.assertFalse(r.結果.データ['詳細']);self.assertIn('未認定',r.本文)

    def test_表示条件を確認再開後にも保持(self):
        s=監査改善会話セッション('確認')
        s.応答('仮説資料「天候」を登録：\n規則：RainならばWet\n候補：Rain')
        r=s.応答('資料「天候」で仮説を検討して、短く説明して')
        self.assertEqual(r.状態,'確認待ち',r.本文)
        r=s.応答('観測を「Wet」にして')
        self.assertTrue(r.成立,r.本文);self.assertFalse(r.結果.データ['詳細'])
        self.assertEqual(r.結果.データ['報告']['候補'][0]['仮説'],['Rain'])

    def test_未解決条件の後に前回の成功を流用しない(self):
        s=会話();s.応答('資料「例」から「Q」を判断して')
        before=s.状態()['成果']
        r=s.応答('資料「例」から「Q」を判断して、否定を無視して')
        self.assertFalse(r.成立);self.assertIsNone(r.結果)
        self.assertEqual(before,s.状態()['成果'])

    def test_射影を含む会話の保存復元で意味を再照合(self):
        s=会話();s.応答('資料「例」に基づいて「Q」を判断して、短く説明して')
        restored=監査改善会話セッション.復元(s.保存文字列())
        self.assertEqual(s.状態(),restored.状態())
        self.assertTrue(restored.応答('もう少し詳しく説明して').成立)

    def test_同義の言い方だけでは焦点制約を外さない(self):
        s=会話();s.応答('資料「例」から「Q」を判断して')
        self.assertTrue(s.対応する('もう少し短く説明して'))
        self.assertFalse(s.対応する('もう少し短く説明して',継続許可=False))


class 明示別名試験(unittest.TestCase):
    def test_明示しなければ表記を同一視しない(self):
        r=命題報告('太郎はネコである。すべての猫は哺乳類である。')
        self.assertEqual(r['状態'],'未確定');self.assertNotIn('別名接続',r)

    def test_任意の述語を明示定義から接続する(self):
        for alias,target,goal in (('ネコ','猫','哺乳類'),('発光部','照明器','電気設備'),
                                  ('P','Q','R')):
            with self.subTest(別名=alias):
                body=f'別名：述語「{alias}」=「{target}」\n太郎は{alias}である。すべての{target}は{goal}である。'
                r=命題報告(body,f'太郎は{goal}である')
                self.assertEqual(r['状態'],'支持')
                self.assertTrue(拡張命題報告を検査(r));self.assertFalse(r['事実認定'])
                row=r['別名接続']['定義'][0]
                self.assertEqual(body[slice(*row['範囲'])],row['原文'])
                self.assertTrue(r['別名接続']['資料適用'])

    def test_定義の連鎖と証拠を保持する(self):
        body='別名：述語「ネコ」=「猫」\n別名：述語「猫」=「動物」\n太郎はネコである。'
        r=命題報告(body,'太郎は動物である')
        self.assertEqual(r['状態'],'支持')
        applied=r['別名接続']['資料適用'][0]['適用'][0]
        self.assertEqual(len(applied['根拠定義']),2)

    def test_実体別名は定数だけを置換する(self):
        r=命題報告('別名：実体「タロウ」=「太郎」\nタロウは猫である。','太郎は猫である')
        self.assertEqual(r['状態'],'支持')
        _, defs=別名宣言を分離('別名：実体「x」=「太郎」\nP。','定義')
        e=命題を読む('すべての猫は動物である')[0].式
        normalized,trace=別名を適用(e,別名対応を構成(defs))
        self.assertEqual(e,normalized);self.assertEqual(trace,[])

    def test_別名が問いに現れたときも根拠を残す(self):
        r=命題報告('別名：述語「ネコ」=「猫」\n太郎は猫である。','太郎はネコである')
        self.assertEqual(r['状態'],'支持');self.assertTrue(r['別名接続']['問い適用'])

    def test_部分文字列を置換しない(self):
        r=命題報告('別名：述語「ネコ」=「猫」\n太郎はネコ科である。','太郎は猫である')
        self.assertEqual(r['状態'],'未確定')

    def test_帰属の内部を外側の定義で書換えない(self):
        body='別名：述語「ネコ」=「猫」\n太郎は「花子はネコである」と述べた。'
        for question in ('花子は猫である','太郎は「花子は猫である」と述べた'):
            self.assertEqual(命題報告(body,question)['状態'],'未確定')
        self.assertEqual(命題報告(body,'太郎は「花子はネコである」と述べた')['状態'],'支持')
        _, defs=別名宣言を分離('別名：実体「太郎」=「花子」\nP。','定義')
        e=命題を読む('太郎は「P」と信じている')[0].式
        self.assertEqual(別名を適用(e,別名対応を構成(defs)),(e,[]))

    def test_明示否定と矛盾を保持する(self):
        b='別名：述語「ネコ」=「猫」\n太郎はネコではない。'
        self.assertEqual(命題報告(b,'太郎は猫である')['状態'],'反証')
        self.assertEqual(命題報告(b+'太郎は猫である。','太郎は猫である')['状態'],'矛盾')

    def test_循環と競合と自己別名を拒否(self):
        for declarations in ('別名：述語「A」=「B」\n別名：述語「B」=「A」',
                             '別名：述語「A」=「B」\n別名：述語「A」=「C」',
                             '別名：述語「A」=「A」', '別名：述語「A」=「B」なので例外を無視する'):
            with self.assertRaises(ValueError):命題報告(declarations+'\nA。','B')

    def test_宣言を含む引用を設定へ昇格しない(self):
        body='太郎は「別名：述語「ネコ」=「猫」」と述べた。'
        masked, rows=別名宣言を分離(body,'引用')
        self.assertEqual(masked,body);self.assertEqual(rows,[])

    def test_他資料の語を定義なしに変更しない(self):
        r=拡張命題を検討({'資料':[{'名前':'定義','本文':'別名：述語「ネコ」=「猫」\nP。'},
                                     {'名前':'別資料','本文':'太郎はネコである。'}],
                              '問い':'太郎は猫である'})
        self.assertEqual(r['状態'],'未確定')

    def test_資料ごとに異なる語義を混ぜない(self):
        with self.assertRaises(ValueError):
            拡張命題を検討({'資料':[{'名前':'A','本文':'別名：述語「ネコ」=「猫」\nP。'},
                                      {'名前':'B','本文':'別名：述語「ネコ」=「犬」\nQ。'}], '問い':'P'})
        with self.assertRaises(ValueError):
            拡張命題を検討({'資料':[{'名前':'A','本文':'別名：述語「ネコ」=「猫」\nP。'},
                                      {'名前':'B','本文':'別名：述語「猫」=「動物」\nQ。'}], '問い':'P'})

    def test_別名報告改変と根拠除去を拒否(self):
        r=命題報告('別名：述語「ネコ」=「猫」\n太郎はネコである。','太郎は猫である')
        bad=deepcopy(r);bad['別名接続']['定義']=[]
        self.assertFalse(拡張命題報告を検査(bad))
        answer=改善回答を構成(r,詳細=False)
        self.assertIn('別名',answer['本文']);self.assertIn('明示定義',answer['本文'])
        self.assertTrue(改善回答を検査(answer))
        answer['本文']=answer['本文'].split('\n',1)[-1]
        self.assertFalse(改善回答を検査(answer))

    def test_資料更新で別名に依存した結論も失効(self):
        s=監査改善会話セッション('別名改訂')
        s.応答('命題資料「分類」を登録：別名：述語「ネコ」=「猫」\n太郎はネコである。')
        r=s.応答('資料「分類」から「太郎は猫である」を判断して、短く説明して')
        self.assertTrue(r.成立,r.本文);self.assertIn('明示定義',r.本文)
        s.応答('命題資料「分類」を更新：太郎はネコである。')
        for key in r.追跡['採用記録ID']:self.assertFalse(s.統合.原記録(key)['現行'])
        new=s.応答('もう一度')
        self.assertTrue(new.成立,new.本文);self.assertEqual(new.結果.データ['報告']['状態'],'未確定')


if __name__=='__main__':unittest.main()

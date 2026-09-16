"""第25の依頼表現・明示語彙・探索削減。開発回帰であり独立未見評価ではない。"""
from copy import deepcopy
from itertools import combinations
import random
import unittest
from minidora.監査改善会話 import 監査改善会話セッション
from minidora.監査改善会話解釈 import 改善発話を解釈
from minidora.監査改善接続 import 拡張命題を検討, 拡張命題報告を検査, 改善回答を構成
from minidora.有限仮説探索 import 仮説を検討, 仮説報告を検査
from minidora.明示語彙 import 述語別名を検査

登録 = '命題資料「例」を登録：P。PならばQ。'
問い = '資料「例」から「Q」を判定して'


class 依頼意味試験(unittest.TestCase):
    def setUp(self):
        self.session = 監査改善会話セッション('第25')
        self.assertTrue(self.session.応答(登録).成立)

    def test_同義依頼の全組合せを同じ結論へ接続(self):
        for verb in ('判定', '判断'):
            for ending in ('して', 'してください', 'してくれる？', 'してくれますか？',
                           'してもらえる？', 'してもらえますか？', 'していただけますか？'):
                for connector in ('から', 'に基づいて', 'に基づき', 'をもとに'):
                    with self.subTest(verb=verb, ending=ending, connector=connector):
                        text = f'資料「例」{connector}「Q」を{verb}{ending}'
                        # 各表現は別の実セッションで検討。発話・採用上限を変更しない。
                        session = 監査改善会話セッション('表現別')
                        session.応答(登録)
                        結果 = session.応答(text)
                        self.assertTrue(結果.成立, 結果.本文)
                        self.assertEqual(結果.結果.データ['報告']['状態'], '支持')
                        self.assertEqual(結果.追跡['原依頼'], text)

    def test_引用なしの問いを接続(self):
        for tail in ('Qと言える？', 'Qと言えますか？'):
            結果 = self.session.応答('資料「例」から' + tail)
            self.assertTrue(結果.成立, 結果.本文)
            self.assertEqual(結果.結果.データ['報告']['要求']['問い'], 'Q')

    def test_検討と表示を一つの目的に合成(self):
        結果 = self.session.応答(問い + '、短く説明してください')
        self.assertTrue(結果.成立, 結果.本文)
        self.assertFalse(結果.結果.データ['詳細'])
        self.assertIn(結果.結果.データ['報告']['限界'], 結果.本文)
        self.assertEqual(len(結果.追跡['工程作用']), 3)

    def test_不足確認をまたいで表示条件を保持(self):
        結果 = self.session.応答('資料「例」で命題を判断して、短く説明して')
        self.assertEqual(結果.状態, '確認待ち')
        結果 = self.session.応答('問いを「Q」にして')
        self.assertTrue(結果.成立, 結果.本文)
        self.assertFalse(結果.結果.データ['詳細'])

    def test_登録をまたいで表示条件を保持(self):
        結果 = self.session.応答('資料「未登録」から「Q」を判断して、短く説明して')
        self.assertEqual(結果.状態, '確認待ち')
        self.session.応答('命題資料「未登録」を登録：Q。')
        結果 = self.session.応答('続けて')
        self.assertTrue(結果.成立, 結果.本文)
        self.assertFalse(結果.結果.データ['詳細'])

    def test_仮説と介入にも同じ表示指定を適用(self):
        self.session.応答('仮説資料「仮」を登録：\n規則：AならばB\n候補：A')
        結果 = self.session.応答('資料「仮」で観測「B」を説明する仮説を検討して、短く説明して')
        self.assertTrue(結果.成立, 結果.本文)
        self.assertFalse(結果.結果.データ['詳細'])
        self.session.応答('介入資料「因」を登録：\n外生：U=真\n構造：A=U')
        結果 = self.session.応答('資料「因」で「A=偽」に介入した結果を比較して、短く説明して')
        self.assertTrue(結果.成立, 結果.本文)
        self.assertFalse(結果.結果.データ['詳細'])

    def test_相対短縮と表示限界を区別(self):
        detailed = self.session.応答(問い)
        short = self.session.応答('もう少し短く説明して')
        self.assertTrue(short.成立, short.本文)
        self.assertLess(len(short.本文), len(detailed.本文))
        again = self.session.応答('もう少し短く説明してください')
        self.assertEqual(again.状態, '保留')
        self.assertIn('追加変更は未対応', again.本文)
        expanded = self.session.応答('もう少し詳しく説明して')
        self.assertTrue(expanded.成立)
        self.assertTrue(expanded.結果.データ['詳細'])

    def test_原引用の語句を正規化しない(self):
        text = '資料「判断してくれる？」から「否定(P)」を判断してくれる？'
        command = 改善発話を解釈(text)
        self.assertEqual(command['資料'], '判断してくれる？')
        self.assertEqual(command['変更']['問い'], '否定(P)')
        self.assertEqual(command['原文'], text)

    def test_登録本文は依頼解釈へ流さない(self):
        body = 'P。資料「例」から「Q」を判断して、短く説明して'
        command = 改善発話を解釈('命題資料「別」を登録：' + body)
        self.assertEqual(command['行為'], '登録')
        self.assertEqual(command['本文'], body)

    def test_否定した依頼や未知の条件を捨てない(self):
        for text in (問い + '、外部へ送信して', 問い + '、根拠を捨てて',
                     問い + '、短く説明して、ただし推測で',
                     問い + '、もう少し短く説明して',
                     '資料「例」から「Q」を判定しないで',
                     '資料「例」から「Q」を判断しても実行しないで',
                     '資料「例」に基づいて「Q」を必ず支持と判定して',
                     問い + '？？', '資料「例」から「Q」を判断して\n送信して'):
            with self.subTest(text=text):
                before = deepcopy(self.session.状態()['成果'])
                結果 = self.session.応答(text)
                self.assertFalse(結果.成立, 結果.本文)
                self.assertEqual(before, self.session.状態()['成果'])

    def test_意味が曖昧な問いは確認へ戻る(self):
        結果 = self.session.応答('資料「例」に基づいて「PまたはQかつR」を判断して、短く説明して')
        self.assertEqual(結果.状態, '確認待ち')
        結果 = self.session.応答('問い候補1で続けて')
        self.assertTrue(結果.成立, 結果.本文)
        self.assertFalse(結果.結果.データ['詳細'])

    def test_引用帰属と世界事実の境界を維持(self):
        self.session.応答('命題資料「発言」を登録：太郎は「Q」と述べた。')
        結果 = self.session.応答('資料「発言」に基づいて「Q」を判断してくれる？')
        self.assertEqual(結果.結果.データ['報告']['状態'], '未確定')

    def test_新表現と複合目的を保存復元する(self):
        self.session.応答(問い + '、短く説明して')
        restored = 監査改善会話セッション.復元(self.session.保存文字列())
        self.assertEqual(restored.状態(), self.session.状態())
        self.assertTrue(restored.応答('もう少し詳しく説明して').成立)

    def test_未完了の表示条件も保存復元する(self):
        self.session.応答('資料「例」で命題を判定して、短く説明して')
        restored = 監査改善会話セッション.復元(self.session.保存文字列())
        結果 = restored.応答('問いを「Q」にして')
        self.assertFalse(結果.結果.データ['詳細'])


def 別名(表記='ネコ', 正規名='猫', 引数数=1):
    return {'表記': 表記, '正規名': 正規名, '引数数': 引数数, '出典': '利用者の明示定義'}


def 語彙要求(body='太郎はネコである。すべての猫は哺乳類である。', question='太郎は哺乳類である'):
    return {'資料': [{'名前': '原資料', '本文': body}], '問い': question, '述語別名': [別名()]}


class 明示語彙試験(unittest.TestCase):
    def test_別名なしでは同義と推測しない(self):
        request = 語彙要求(); request.pop('述語別名')
        self.assertEqual(拡張命題を検討(request)['状態'], '未確定')

    def test_明示定義から導出して原文を保持(self):
        request = 語彙要求(); before = deepcopy(request)
        report = 拡張命題を検討(request)
        self.assertEqual(report['状態'], '支持')
        self.assertEqual(request, before)
        self.assertEqual(report['要求'], before)
        self.assertIn('ネコ', report['資料候補'][0]['記載候補'][0]['原文'])
        self.assertEqual(report['判定結果']['場合別'][0]['語彙対応'][0]['正規名'], '猫')
        self.assertTrue(拡張命題報告を検査(report))

    def test_問い側の別名も同じ範囲で適用(self):
        report = 拡張命題を検討(語彙要求('太郎は猫である。', '太郎はネコである'))
        self.assertEqual(report['状態'], '支持')
        self.assertEqual(report['判定結果']['問い'], '太郎はネコである')

    def test_項数が違う述語を混同しない(self):
        report = 拡張命題を検討(語彙要求('ネコ()。', '猫()'))
        self.assertEqual(report['状態'], '未確定')

    def test_固有名は置き換えない(self):
        report = 拡張命題を検討(語彙要求('ネコは学生である。', '猫は学生である'))
        self.assertEqual(report['状態'], '未確定')

    def test_帰属内で同義置換しない(self):
        report = 拡張命題を検討(語彙要求('太郎は「次郎はネコである」と信じている。',
                                        '太郎は「次郎は猫である」と信じている'))
        self.assertEqual(report['状態'], '未確定')

    def test_否定と矛盾を保持(self):
        report = 拡張命題を検討(語彙要求('太郎はネコである。太郎は猫ではない。', '太郎は猫である'))
        self.assertEqual(report['状態'], '矛盾')

    def test_量化変数を定数化しない(self):
        report = 拡張命題を検討(語彙要求('太郎は猫である。すべてのネコは動物である。', '太郎は動物である'))
        self.assertEqual(report['状態'], '支持')

    def test_短い説明にも別名の条件と出典を残す(self):
        report = 拡張命題を検討(語彙要求())
        answer = 改善回答を構成(report, 詳細=False)
        self.assertIn('利用者の明示定義', answer['本文'])
        self.assertIn('同義述語', answer['本文'])
        self.assertFalse(answer['事実認定'])

    def test_別名定義や導出の改変を検出する(self):
        report = 拡張命題を検討(語彙要求())
        report['判定結果']['別名定義'][0]['出典'] = '無断差替え'
        self.assertFalse(拡張命題報告を検査(report))

    def test_不正定義を拒否(self):
        invalid = ([別名(), 別名()], [別名(), 別名('猫', '動物')],
                   [別名(), 別名('猫', 'ネコ')], [別名('猫', '猫')],
                   [{**別名(), '引数数': True}], [{**別名(), '出典': ''}],
                   [別名('AならばB。', '猫')], [{**別名(), '未知': True}],
                   {'猫': 'ネコ'})
        for entries in invalid:
            with self.subTest(entries=entries), self.assertRaises(ValueError):
                述語別名を検査(entries)

    def test_対話で定義の追加と解除と再説明を行う(self):
        session = 監査改善会話セッション('語彙')
        session.応答('命題資料「例」を登録：太郎はネコである。すべての猫は哺乳類である。')
        session.応答('資料「例」から「太郎は哺乳類である」を判断して')
        結果 = session.応答('述語別名を「ネコ/1=猫」にして')
        self.assertEqual(結果.結果.データ['報告']['状態'], '支持')
        restored = 監査改善会話セッション.復元(session.保存文字列())
        結果 = restored.応答('短く説明して')
        self.assertIn('ネコ', 結果.本文)
        結果 = restored.応答('述語別名を「なし」にして')
        self.assertEqual(結果.結果.データ['報告']['状態'], '未確定')

    def test_新しい目的へ定義を無断で引き継がない(self):
        session = 監査改善会話セッション('語彙')
        session.応答('命題資料「例」を登録：太郎はネコである。')
        session.応答('資料「例」から「太郎は猫である」を判断して')
        session.応答('述語別名を「ネコ/1=猫」にして')
        結果 = session.応答('資料「例」から「太郎は猫である」を判断して')
        self.assertEqual(結果.結果.データ['報告']['状態'], '未確定')


def 規則(index, left, right):
    return {'識別子': str(index), '前件': left, '後件': right, '出典': '開発用規則'}


def 単純全列挙(request):
    """本体の閉包・枝刈り・式鍵を共有しない、小さい基底文字列用の参照計算。"""
    def reverse(value):
        return value[3:-1] if value.startswith('否定(') else '否定(' + value + ')'
    def closure(hypotheses):
        known = {r['命題'] for r in request['事実']} | set(hypotheses)
        while True:
            after = known | {r['後件'] for r in request['規則'] if set(r['前件']) <= known}
            if after == known:
                break
            known = after
        return known
    goal = set(request['観測'])
    found = []
    for size in range(min(request.get('最大仮説数', 3), len(request['仮説候補'])) + 1):
        for combo in combinations(request['仮説候補'], size):
            h = frozenset(combo); known = closure(h)
            if goal <= known and not any(reverse(k) in known for k in known):
                if not any(old <= h for old in found):
                    found.append(h)
    return set(found)


class 探索削減試験(unittest.TestCase):
    def request(self):
        return {'事実': [], '規則': [規則('r', ['H0'], 'Q')], '観測': ['Q'],
                '仮説候補': ['H' + str(i) for i in range(16)], '最大仮説数': 6, '最大試行数': 4096}

    def test_14893組を関連外証明で削減する(self):
        request = self.request(); report = 仮説を検討(request)
        self.assertTrue(report['探索完了'])
        self.assertEqual(report['探索範囲']['対象組合せ数'], 14893)
        self.assertEqual(report['件数']['評価'], 2)
        self.assertEqual(report['件数']['関連外による省略'], 14891)
        self.assertEqual([c['仮説'] for c in report['候補']], [['H0']])
        self.assertTrue(仮説報告を検査(report))

    def test_全候補が関連しても極小性で削減する(self):
        request = self.request()
        request['規則'] = [規則(i, ['H' + str(i)], 'Q') for i in range(16)]
        report = 仮説を検討(request)
        self.assertEqual(len(report['候補']), 16)
        self.assertEqual(report['件数']['評価'], 17)
        self.assertEqual(report['件数']['極小性による省略'], 14876)
        self.assertEqual(report['件数']['関連外による省略'], 0)

    def test_予算不足で部分解を成功扱いしない(self):
        request = self.request(); request['最大試行数'] = 1
        with self.assertRaises(ValueError):
            仮説を検討(request)

    def test_関連外の規則を削除して矛盾を隠さない(self):
        request = self.request()
        request['規則'] += [規則('conflict1', ['H0'], 'Z'), 規則('conflict2', ['H0'], '否定(Z)')]
        report = 仮説を検討(request)
        self.assertEqual(report['候補'], [])
        self.assertTrue(report['探索完了'])

    def test_連言条件と循環を保持(self):
        request = {'事実': [], '規則': [規則('a', ['A'], 'B'), 規則('b', ['B'], 'A'),
                   規則('c', ['A', 'C'], 'Q')], '観測': ['Q'], '仮説候補': ['B', 'C', 'Z'], '最大仮説数': 3}
        report = 仮説を検討(request)
        self.assertEqual({frozenset(r['仮説']) for r in report['候補']}, 単純全列挙(request))

    def test_独立した小規模全列挙と80規則集合を照合(self):
        generator = random.Random(250913)
        names = ['A', 'B', 'C', 'D', 'E', 'Q']
        for case in range(80):
            rules = [規則(i, generator.sample(names[:-1], generator.randint(1, 2)), generator.choice(names))
                     for i in range(9)]
            if case % 3 == 0:
                rules.append(規則('negative', ['A'], '否定(C)'))
            request = {'事実': [], '規則': rules, '観測': ['Q'],
                       '仮説候補': names[:-1], '最大仮説数': 3}
            with self.subTest(case=case):
                report = 仮説を検討(request)
                self.assertEqual({frozenset(r['仮説']) for r in report['候補']}, 単純全列挙(request))
                self.assertEqual(sum(report['件数'][k] for k in ('評価', '極小性による省略', '関連外による省略')),
                                 report['探索範囲']['対象組合せ数'])


if __name__ == '__main__':
    unittest.main()

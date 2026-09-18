"""v6の格役割・活用・条件方向・例外採用。人工記載を世界知識へ昇格しない。"""
from copy import deepcopy
from dataclasses import replace
import random
import unittest
from unittest.mock import patch
from minidora.HDS運用.関係構文化 import 関係文を読む, 関係文を構成, 関係式を表現
from minidora.HDS運用.関係言語 import 関係文を読む as v5文を読む
from minidora.HDS運用.関係依頼 import 関係依頼を読む
from minidora.HDS運用.関係読解 import 関係資料を読む, 関係資料を検査, 関係要求を検査, 不足調査が必要
from minidora.HDS運用.関係内容 import 関係回答を照合, 関係回答を検査, 関係回答を再表現, _生成
from minidora.製品版.型 import 能力結果

規則 = '装置Aが有効なら稼働する（ただし、装置Aが故障している場合を除く）'
問い = '装置Aが稼働する'


def 要求(質問=問い):
    return 関係依頼を読む({'原文': '資料「手順」から' + 質問 + 'かどうか説明して'})['要求']


def 読解(本文, 質問=問い):
    return 関係資料を読む({'手順': 能力結果(True, 本文)}, 要求(質問))


def 判定(本文, 質問=問い):
    return 読解(本文, 質問)['資料群']['手順']['判定']['判定']


class 格役割試験(unittest.TestCase):
    def 同形(self, *文群):
        群 = [関係文を読む(文)[0].鍵() for 文 in 文群]
        self.assertEqual(len(set(群)), 1, 文群)

    def test_目的語と相手の語順だけを正準化(self):
        self.同形('担当Aが担当Bに書類を送る', '担当Aは書類を担当Bに送ります')
        式, _, 変換 = 関係文を読む('担当Aは担当Bに書類を送る')
        self.assertEqual([項.名前 for 項 in 式.項], ['担当A', '書類', '担当B'])
        self.assertEqual(式.述語, '格動作[を,に]:送る')
        self.assertTrue(any('格役割:' in 項 for 項 in 変換))

    def test_主語と目的語を交換しない(self):
        self.assertNotEqual(関係文を読む('装置Aが装置Bを確認する')[0].鍵(), 関係文を読む('装置Bが装置Aを確認する')[0].鍵())

    def test_同じ語彙でも格を交換しない(self):
        self.assertNotEqual(関係文を読む('担当Aは書類を担当Bに送る')[0].鍵(), 関係文を読む('担当Aは担当Bを書類に送る')[0].鍵())

    def test_へとにの語義を勝手に同一化しない(self):
        self.assertNotEqual(関係文を読む('装置Aは倉庫へ移動する')[0].鍵(), 関係文を読む('装置Aは倉庫に移動する')[0].鍵())

    def test_三格の並べ替えと表現を照合(self):
        self.同形('担当Aは担当Bから荷物を倉庫へ運ぶ', '担当Aは倉庫へ荷物を担当Bから運びます')
        文 = '担当Aは荷物を倉庫へ担当Bから運ぶ'
        self.assertEqual(関係式を表現(関係文を読む(文)[0]), 文)

    def test_新しい対象名とサ変動作を正解表なしで合成(self):
        rng = random.Random(631)
        for _ in range(20):
            a, b = '機器' + str(rng.randrange(100000)), '素材' + str(rng.randrange(100000))
            文 = a + 'は' + b + 'を特殊処理する'
            self.assertEqual(関係式を表現(関係文を読む(文)[0]), 文)

    def test_重複格を黙って上書きしない(self):
        for 文 in ('担当Aは書類を荷物を確認する', '担当Aは担当Bに担当Cに送る'):
            with self.subTest(文=文), self.assertRaises(ValueError):
                関係文を読む(文)

    def test_役割の上限を越えて項を捨てない(self):
        with self.assertRaises(ValueError):
            関係文を読む('担当Aは書類を担当Bに倉庫から車で送る')

    def test_目的語の指示語を主語へ勝手に接続しない(self):
        for 指示 in ('それ', 'これ', '前者', '後者', '同装置', '同対象', '彼', '彼女', 'あなた'):
            with self.subTest(指示=指示), self.assertRaises(ValueError):
                関係文を読む('担当Aは' + 指示 + 'を確認する', 先行主体='装置A')

    def test_主語の既存局所照応は継続(self):
        式, 主体, _ = 関係文を読む('それは書類を確認する', 先行主体='装置A')
        self.assertEqual(式.項[0].名前, '装置A')
        self.assertEqual(主体, '装置A')

    def test_未知の動詞活用を推測しない(self):
        for 文 in ('装置Aは書類を未知ります', '担当Aは書類を読むかもしれない', '担当Aは書類を読んでください'):
            with self.subTest(文=文), self.assertRaises(ValueError):
                関係文を読む(文)

    def test_修飾や未消費の目的を捨てない(self):
        for 文 in ('担当Aは書類をすぐに読む', '担当Aは書類を読んで送る', '担当Aは書類を読む、投稿して'):
            with self.subTest(文=文), self.assertRaises(ValueError):
                関係文を読む(文)

    def test_旧読解器の対応範囲を無言変更しない(self):
        with self.assertRaises(ValueError):
            v5文を読む('担当Aは書類を読む')
        self.assertEqual(v5文を読む('装置Aは稼働する')[0].鍵(), 関係文を読む('装置Aは稼働する')[0].鍵())


class 活用作用域試験(unittest.TestCase):
    def test_一般動詞の丁寧形と普通形(self):
        for 普通, 丁寧 in (('書く', '書きます'), ('読む', '読みます'), ('待つ', '待ちます'), ('選ぶ', '選びます'),
                           ('送る', '送ります'), ('調べる', '調べます'), ('閉じる', '閉じます'), ('行く', '行きます'),
                           ('受け取る', '受け取ります'), ('減る', '減ります')):
            with self.subTest(普通=普通):
                self.assertEqual(関係文を読む('担当Aは' + 普通)[0].鍵(), 関係文を読む('担当Aは' + 丁寧)[0].鍵())

    def test_明示否定を別の正形から導く(self):
        for 否定, 丁寧 in (('読まない', '読みません'), ('書かない', '書きません'), ('調べない', '調べません'), ('減らない', '減りません')):
            with self.subTest(否定=否定):
                a = 関係文を読む('担当Aは' + 否定)[0]
                b = 関係文を読む('担当Aは' + 丁寧)[0]
                self.assertEqual(a.鍵(), b.鍵())
                self.assertEqual(a.種別, '否定')

    def test_過去形と過去否定(self):
        for 普通, 丁寧, 否定 in (('読んだ', '読みました', '読まなかった'), ('書いた', '書きました', '書かなかった'),
                                 ('行った', '行きました', '行かなかった'), ('調べた', '調べました', '調べなかった')):
            with self.subTest(普通=普通):
                a = 関係文を読む('担当Aは' + 普通)[0]
                self.assertEqual(a.鍵(), 関係文を読む('担当Aは' + 丁寧)[0].鍵())
                self.assertEqual(a.鍵(), 関係文を読む('担当Aは' + 否定)[0].子[0].鍵())

    def test_進行と過去と実行可能性を現在動作に潰さない(self):
        群 = [関係文を読む('担当Aは書類を' + 語)[0].鍵() for 語 in ('読む', '読んだ', '読んでいる')]
        self.assertEqual(len(set(群)), 3)
        self.assertEqual(関係文を読む('担当Aは書類を読んでいます')[0].鍵(), 群[2])
        self.assertNotEqual(関係文を読む('装置Aは素材を処理する')[0].鍵(), 関係文を読む('装置Aは素材を処理できる')[0].鍵())

    def test_括弧内でも新しい格動作を扱う(self):
        a = 関係文を読む('担当Aは書類を読む')[0]
        self.assertEqual(a.鍵(), 関係文を読む('（担当Aは書類を読みます）')[0].鍵())
        self.assertEqual(a.鍵(), 関係文を読む('否定（担当Aは書類を読む）')[0].子[0].鍵())

    def test_括弧へ外側の指示先を流し込まない(self):
        with self.assertRaises(ValueError):
            関係文を読む('（同対象は書類を読む）', 先行主体='担当A')

    def test_引用内容を外側の事実にしない(self):
        s = '担当Aは「担当Bが書類を読む」と述べた'
        self.assertEqual(判定(s, '担当Bが書類を読む'), '未確定')
        self.assertEqual(判定(s, s), '支持')

    def test_時点と様相を混ぜない(self):
        for s in ('2025年では（担当Aは書類を読む）', '可能性として（担当Aは書類を読む）'):
            with self.subTest(s=s):
                self.assertEqual(判定(s, '担当Aは書類を読む'), '未確定')
                self.assertEqual(判定(s, s), '支持')

    def test_原文長と不可視文字と深さを検査(self):
        for 文 in ('装置Aは読む' * 1000, '装置\u202eAは読む', '（' * 30 + '装置Aは読む' + '）' * 30):
            with self.subTest(先頭=文[:25]), self.assertRaises(ValueError):
                関係文を読む(文)


class 条件方向試験(unittest.TestCase):
    def test_格役割を後続条件が実際に消費する(self):
        s = '担当Aは担当Bに書類を送ります。担当Aが書類を担当Bに送るなら、担当Bは書類を読む。'
        self.assertEqual(判定(s, '担当Bは書類を読む'), '支持')
        self.assertEqual(判定(s, '担当Aは書類を読む'), '未確定')

    def test_目的語が違えば条件を満たさない(self):
        s = '担当Aは荷物を確認する。担当Aが書類を確認するなら、装置Aは稼働する。'
        self.assertEqual(判定(s), '未確定')

    def test_必要条件だけで後件を成立させない(self):
        r = '「装置Aは有効である」は「装置Aは稼働する」の必要条件である。'
        self.assertEqual(判定(r + '装置Aは有効である。'), '未確定')
        self.assertEqual(判定(r + '装置Aは稼働する。', '装置Aは有効である'), '支持')

    def test_必要な事柄を普通の文章から構成(self):
        r = '装置Aが稼働するためには、担当Aが書類を確認することが必要です。'
        self.assertEqual(判定(r + '担当Aは書類を確認する。'), '未確定')
        self.assertEqual(判定(r + '装置Aは稼働する。', '担当Aは書類を確認する'), '支持')

    def test_十分条件は逆向きを保証しない(self):
        r = '「装置Aは有効である」は「装置Aは稼働する」の十分条件です。'
        self.assertEqual(判定(r + '装置Aは有効である。'), '支持')
        self.assertEqual(判定(r + '装置Aは稼働する。', '装置Aは有効である'), '未確定')

    def test_必要十分の明示があるときだけ両方向(self):
        r = '「装置Aは有効である」は「装置Aは稼働する」の必要十分条件です。'
        self.assertEqual(判定(r + '装置Aは有効である。'), '支持')
        self.assertEqual(判定(r + '装置Aは稼働する。', '装置Aは有効である'), '支持')

    def test_条件自体を前件又は後件の事実にしない(self):
        r = '担当Aが書類を読んだ場合、装置Aは稼働する。'
        self.assertEqual(判定(r), '未確定')
        self.assertEqual(判定(r, '担当Aは書類を読んだ'), '未確定')

    def test_過去の条件を現在の動作で代用しない(self):
        r = '担当Aが書類を読んだ場合、装置Aは稼働する。'
        self.assertEqual(判定(r + '担当Aは書類を読む。'), '未確定')
        self.assertEqual(判定(r + '担当Aは書類を読みました。'), '支持')

    def test_連言と選言の混在を勝手に優先順位づけしない(self):
        with self.assertRaises(ValueError):
            関係文を読む('担当Aは読むかつ担当Bは読むまたは担当Cは読む')


class 明示例外試験(unittest.TestCase):
    def test_例外を独立した否定条件として構成(self):
        式, _, _, 例外 = 関係文を構成(規則)
        self.assertEqual(式.種別, '含意')
        self.assertEqual(式.子[0].子[1].子[0].鍵(), 例外.鍵())
        self.assertEqual(例外.述語, '故障している')

    def test_例外不明のまま通常規則を適用しない(self):
        x = 読解('装置Aは有効です。' + 規則)['資料群']['手順']
        self.assertEqual(x['判定']['判定'], '未確定')
        self.assertFalse(x['限定隔離'])
        self.assertFalse(x['例外監査'][0]['採用'])
        self.assertEqual(len(x['不足候補']), 1)

    def test_非例外を明示支持した場合だけ適用する(self):
        self.assertEqual(判定('装置Aは有効です。装置Aは故障していません。' + 規則), '支持')

    def test_例外があることから後件の否定を作らない(self):
        s = '装置Aは有効です。装置Aは故障しています。' + 規則
        self.assertEqual(判定(s), '未確定')
        self.assertEqual(判定(s, '装置Aは稼働しない'), '未確定')

    def test_例外と非例外の矛盾では採用しない(self):
        s = '装置Aは有効です。装置Aは故障しています。装置Aは故障していません。' + 規則
        x = 読解(s)['資料群']['手順']
        self.assertEqual(x['判定']['判定'], '未確定')
        self.assertEqual(x['例外監査'][0]['独立判定']['判定'], '矛盾')
        self.assertFalse(x['例外監査'][0]['採用'])

    def test_別の直接根拠まで消さない(self):
        s = '装置Aは稼働する。装置Aは有効です。' + 規則
        x = 読解(s)
        self.assertEqual(x['資料群']['手順']['判定']['判定'], '支持')
        self.assertFalse(x['資料群']['手順']['例外監査'][0]['採用'])
        self.assertTrue(不足調査が必要(x))

    def test_通常条件の複数段導出から非例外を得る(self):
        s = '装置Aは有効です。装置Aは検査済です。装置Aが検査済なら、正常である。装置Aが正常なら、故障していない。' + 規則
        self.assertEqual(判定(s), '支持')

    def test_例外付き規則の相互支持だけでは採用しない(self):
        s = '装置Aは有効です。' + 規則 + '。装置Aが有効なら故障していない（ただし、装置Aが稼働しない場合を除く）。'
        x = 読解(s)['資料群']['手順']
        self.assertEqual(x['判定']['判定'], '未確定')
        self.assertTrue(all(not 行['採用'] for 行 in x['例外監査']))

    def test_規則自身が例外を成立させたら撤回(self):
        s = '装置Aは有効です。装置Aは故障していません。' + 規則 + '。装置Aが稼働するなら、故障している。'
        x = 読解(s)['資料群']['手順']
        self.assertEqual(x['判定']['判定'], '未確定')
        self.assertFalse(x['例外監査'][0]['採用'])
        self.assertIn('自己又は相互阻害', x['例外監査'][0]['理由'])
        self.assertEqual(x['例外監査'][0]['最終判定']['判定'], '反証')

    def test_相互阻害で順序依存や振動を起こさない(self):
        s = ['装置Aは有効です', '装置Bは有効です', '装置Aは故障していません', '装置Bは故障していません',
             規則, 規則.replace('装置A', '装置B'), '装置Aが稼働するなら装置Bは故障している', '装置Bが稼働するなら装置Aは故障している']
        for 群 in (s, list(reversed(s))):
            x = 読解('。'.join(群))['資料群']['手順']
            self.assertEqual(x['判定']['判定'], '未確定')
            self.assertTrue(all(not 行['採用'] for 行 in x['例外監査']))
            self.assertTrue(all('自己又は相互阻害' in 行['理由'] for 行 in x['例外監査']))

    def test_原文の例外範囲と未採用理由を説明へ残す(self):
        s = '装置Aは有効です。' + 規則
        x = 読解(s)
        for 行 in x['資料群']['手順']['読解']:
            a, b = 行['範囲']
            self.assertEqual(行['原文'], s[a:b])
        y = 関係回答を照合(x, _生成(x, '文章'), 形式='文章')
        self.assertIn(規則, y.本文)
        self.assertIn('規則採否：未採用', y.本文)
        self.assertTrue(関係回答を検査(y))
        self.assertTrue(関係回答を検査(関係回答を再表現(y, '引用')))

    def test_不明な作用域を既知注記で隠さない(self):
        s = '装置Aは有効です。装置Aは故障していません。' + 規則 + '。ただし例外あり。'
        x = 読解(s)['資料群']['手順']
        self.assertTrue(x['限定隔離'])
        self.assertEqual(x['判定']['判定'], '未確定')
        self.assertEqual(x['採用記載'], [])

    def test_別文の例外を勝手に直前だけへ限定しない(self):
        x = 読解('装置Aは稼働する。ただし、装置Aが故障している場合を除く。')['資料群']['手順']
        self.assertTrue(x['限定隔離'])
        self.assertEqual(x['判定']['判定'], '未確定')

    def test_条件のない断定への例外を未対応として残す(self):
        x = 読解('装置Aは稼働する（ただし、装置Aが故障している場合を除く）')['資料群']['手順']
        self.assertTrue(x['限定隔離'])
        self.assertEqual(x['判定']['判定'], '未確定')

    def test_入れ子や引用の例外を外側の規則にしない(self):
        for 文 in ('否定（' + 規則 + '）', '担当Aは「' + 規則 + '」と述べた'):
            with self.subTest(文=文), self.assertRaises(ValueError):
                関係文を読む(文)

    def test_例外の時点を現在へ潰さない(self):
        s = '装置Aは有効です。2025年では（装置Aは故障していない）。' + 規則
        self.assertEqual(判定(s), '未確定')

    def test_例外規則の件数上限(self):
        with self.assertRaisesRegex(ValueError, '八件'):
            読解('。'.join(規則.replace('装置A', '装置' + str(i)) for i in range(9)))

    def test_例外監査の改変を再構成で拒否(self):
        x = 読解('装置Aは有効です。' + 規則)
        x['資料群']['手順']['例外監査'][0]['採用'] = True
        self.assertFalse(関係資料を検査(x))

    def test_採用記載の改変を再構成で拒否(self):
        x = 読解('装置Aは有効です。' + 規則)
        x['資料群']['手順']['採用記載'].append('記載1')
        self.assertFalse(関係資料を検査(x))

    def test_総推論予算を越えた途中結果を採用しない(self):
        from minidora.命題推論 import 命題推論器
        元 = 命題推論器.判定
        def 超過(self, 式):
            結果 = 元(self, 式)
            結果['操作数'] = 100001
            return 結果
        with patch.object(命題推論器, '判定', 超過), self.assertRaisesRegex(ValueError, '総推論'):
            読解('装置Aは有効です。' + 規則)

    def test_保存要求と読解版の対応を検査(self):
        x = 読解('装置Aは稼働する。')
        self.assertEqual(x['版'], 'HDS関係読解-v2')
        x['版'] = 'HDS関係読解-v1'
        self.assertFalse(関係資料を検査(x))
        r = 要求(); r['版'] = 'HDS関係説明要求-v999'
        with self.assertRaises(ValueError):
            関係要求を検査(r)

    def test_旧要求の読解を新しい意味で上書きしない(self):
        r = 要求(); r['版'] = 'HDS関係説明要求-v1'
        x = 関係資料を読む({'手順': 能力結果(True, '装置Aは稼働する。担当Aは書類を読む。')}, r)
        self.assertEqual(x['版'], 'HDS関係読解-v1')
        self.assertEqual(len(x['資料群']['手順']['残差']), 1)
        self.assertNotIn('例外監査', x['資料群']['手順'])
        self.assertTrue(関係資料を検査(x))


class 追加境界試験(unittest.TestCase):
    def test_撤回時に生じた矛盾の根拠を最終集合と別に保持(self):
        s = '装置Aは有効です。装置Aは故障していません。' + 規則 + '。装置Aが稼働するなら、故障している。'
        x = 読解(s)
        監査 = x['資料群']['手順']['例外監査'][0]
        self.assertEqual(監査['独立判定']['判定'], '反証')
        self.assertEqual(監査['最終判定']['判定'], '反証')
        self.assertEqual(監査['撤回判定']['判定']['判定'], '矛盾')
        self.assertIsNotNone(監査['撤回判定']['判定']['支持'])
        self.assertIsNotNone(監査['撤回判定']['判定']['反証'])
        self.assertIn(監査['規則記載'], 監査['撤回判定']['採用記載'])
        self.assertNotIn(監査['規則記載'], x['資料群']['手順']['採用記載'])
        self.assertTrue(関係資料を検査(x))

    def test_例外の連言の内部にも未対応作用を混入させない(self):
        for 文 in ('装置Aは有効であるかつ（装置Aは稼働するなら装置Aは故障する）',
                  '装置Aは有効であるかつ（担当Aは「装置Aは稼働する」と述べた）',
                  '装置Aは有効であるかつ（すべてのxについて（接続(x,装置A)））'):
            with self.subTest(文=文), self.assertRaisesRegex(ValueError, '例外は量化'):
                関係文を構成('装置Aが有効なら稼働する（ただし、' + 文 + '場合を除く）')

    def test_新しい格項で未対応のひらがな修飾を名前にしない(self):
        for 文 in ('担当Aは大きな書類を読む', '担当Aは書類を静かに読む',
                  '担当Aは書類を読みながら送る', '担当Aは赤い車で送る'):
            with self.subTest(文=文), self.assertRaises(ValueError):
                関係文を読む(文)

    def test_否定名詞述語のがとはを二重主体にしない(self):
        for 語尾 in ('ではない', 'ではありません'):
            with self.subTest(語尾=語尾):
                a = 関係文を読む('装置Aが正常' + 語尾)[0]
                b = 関係文を読む('装置Aは正常' + 語尾)[0]
                self.assertEqual(a.鍵(), b.鍵())
                self.assertEqual(a.種別, '否定')

    def test_例外の否定を例外なしへ読み替えない(self):
        規 = '装置Aが有効なら稼働する（ただし、装置Aが正常ではない場合を除く）'
        self.assertEqual(判定('装置Aは有効です。' + 規), '未確定')
        self.assertEqual(判定('装置Aは有効です。装置Aは正常です。' + 規), '支持')
        self.assertEqual(判定('装置Aは有効です。装置Aは正常ではない。' + 規), '未確定')

    def test_例外の連言を一つの例外として検査(self):
        規 = '装置Aが有効なら稼働する（ただし、装置Aは故障しているかつ装置Bは停止する場合を除く）'
        self.assertEqual(判定('装置Aは有効です。装置Aは故障していません。' + 規), '支持')
        self.assertEqual(判定('装置Aは有効です。装置Aは故障している。装置Bは停止する。' + 規), '未確定')

    def test_未対応例外や改変監査は説明の成功へすり替えない(self):
        x = 読解('装置Aは有効です。' + 規則)
        y = 関係回答を照合(x, _生成(x, '文章'), 形式='文章')
        y.データ['構造']['資料群']['手順']['例外監査'][0]['独立判定']['判定'] = '反証'
        self.assertFalse(関係回答を検査(y))


if __name__ == '__main__':
    unittest.main()

"""固定mainの実v5保存物で、旧意味契約の維持と明示再作用を区別する。"""
from copy import deepcopy
from hashlib import sha256
from pathlib import Path
from unittest.mock import patch
import gzip
import json
import unittest
from minidora.HDS運用 import HDS運用セッション, 旧保存を移行, 運用版
from minidora.HDS運用.値 import 開封, 封緘, 結果を復元
from minidora.HDS運用.関係内容 import 関係回答を検査

資料根 = Path(__file__).parent / '資料' / 'HDS旧保存'


def 原本(名='v5'):
    return gzip.decompress((資料根 / (名 + '.json.gz')).read_bytes()).decode()


def 保存文字(状態):
    return json.dumps(封緘(状態), ensure_ascii=False)


class 旧v5移行試験(unittest.TestCase):
    def test_原本と圧縮物の実指紋と取得由来(self):
        由来 = json.loads((資料根 / '由来_v5.json').read_text(encoding='utf-8'))
        self.assertEqual(由来['commit'], '49949048d6c20d991caf81025f97b9204505907c')
        self.assertEqual(由来['tree'], '38caf0aed103d51a567707fdd0bf64eead8a4691')
        for 名 in ('v5', 'v5_移行済'):
            self.assertEqual(sha256(原本(名).encode()).hexdigest(), 由来['fixture'][名]['原本SHA256'])
            self.assertEqual(sha256((資料根 / (名 + '.json.gz')).read_bytes()).hexdigest(), 由来['fixture'][名]['圧縮SHA256'])
            self.assertEqual(開封(json.loads(原本(名)))['目録'], 由来['目録'])

    def test_旧関係回答を旧読解で正確に再検査する(self):
        状態 = 開封(json.loads(原本()))
        結果 = 結果を復元(状態['前回結果'])
        self.assertEqual(結果.データ['構造']['版'], 'HDS関係読解-v1')
        self.assertTrue(関係回答を検査(結果))
        self.assertEqual(結果.データ['構造']['資料群']['手順']['残差'][0]['原文'], '担当者は報告書を読む')

    def test_旧原本と形成手順と依存履歴を保持し採用を失効(self):
        raw = 原本(); old = 開封(json.loads(raw)); s = 旧保存を移行(raw)
        new = 開封(json.loads(s.保存()))
        self.assertTrue(old['形成手順']); self.assertEqual(new['形成手順'], {})
        self.assertEqual(new['版'], 運用版); self.assertTrue(運用版.endswith('-v6'))
        self.assertEqual(new['移行履歴'][0]['原本'], raw)
        for key in ('資料', '旧資料', '前回結果', '前回目的', '前回依存', '発話', '経験'):
            self.assertEqual(new[key], old[key], key)
        self.assertFalse(new['焦点有効']); self.assertFalse(s.状態()['前回有効'])
        self.assertEqual(開封(json.loads(HDS運用セッション.復元(s.保存()).保存())), new)

    def test_v3からv4からv5の入れ子原本を全て保持(self):
        old = 開封(json.loads(原本('v5_移行済')))
        s = 旧保存を移行(原本('v5_移行済')); new = 開封(json.loads(s.保存()))
        v5 = 開封(json.loads(new['移行履歴'][0]['原本']))
        self.assertEqual(v5, old)
        self.assertEqual(v5['移行履歴'][0]['旧版'], 'HDS-MINIDORA-全体運用-v4')
        v4 = 開封(json.loads(v5['移行履歴'][0]['原本']))
        self.assertEqual(v4['移行履歴'][0]['旧版'], 'HDS-MINIDORA-全体運用-v3')
        HDS運用セッション.復元(s.保存())

    def test_通常復元は旧v5を暗黙変換しない(self):
        with self.assertRaises(ValueError): HDS運用セッション.復元(原本())

    def test_旧目録と権限の獲得は拒否する(self):
        old = 開封(json.loads(原本())); old['目録'] = '0' * 64
        with self.assertRaises(ValueError): 旧保存を移行(保存文字(old))
        with self.assertRaisesRegex(ValueError, '権限'): 旧保存を移行(原本(), 外部読取許可=True)

    def test_移行で旧手順や外部の作用は実行しない(self):
        with patch.object(HDS運用セッション, '応答', side_effect=AssertionError('実行禁止')):
            s = 旧保存を移行(原本())
        self.assertFalse(s.状態()['前回有効'])

    def test_v5当時にない移行を外側再封緘でも拒否(self):
        for 版 in ('v5', 'v6'):
            old = 開封(json.loads(原本('v5_移行済')))
            old['移行履歴'][0]['旧版'] = 'HDS-MINIDORA-全体運用-' + 版
            with self.subTest(版=版), self.assertRaisesRegex(ValueError, 'v5当時'):
                旧保存を移行(保存文字(old))

    def test_入れ子の指紋改変を外側再封緘でも拒否(self):
        old = 開封(json.loads(原本('v5_移行済')))
        old['移行履歴'][0]['原本SHA256'] = '0' * 64
        with self.assertRaises(ValueError): 旧保存を移行(保存文字(old))

    def test_旧関係構造だけ新読解版へ書換えても受理しない(self):
        old = 開封(json.loads(原本()))
        結果 = 結果を復元(old['前回結果'])
        結果.データ['構造']['版'] = 'HDS関係読解-v2'
        self.assertFalse(関係回答を検査(結果))

    def test_明示再計算だけで現行意味契約へ接続する(self):
        raw = 原本(); old = 開封(json.loads(raw)); s = 旧保存を移行(raw)
        self.assertFalse(s.応答('文章にして').成立)
        r = s.応答('再計算して')
        self.assertTrue(r.成立, r.本文); self.assertEqual(r.状態, 'COMMIT')
        new = 開封(json.loads(s.保存()))
        self.assertEqual(old['前回目的']['要求']['版'], 'HDS関係説明要求-v1')
        self.assertEqual(new['前回目的']['要求']['版'], 'HDS関係説明要求-v2')
        self.assertEqual(new['移行履歴'][0]['原本'], raw)
        結果 = 結果を復元(new['前回結果'])
        self.assertTrue(関係回答を検査(結果))
        self.assertEqual(結果.データ['構造']['資料群']['手順']['残差'], [])
        self.assertTrue(HDS運用セッション.復元(s.保存()).状態()['前回有効'])


if __name__ == '__main__': unittest.main()

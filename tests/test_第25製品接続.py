"""通常製品の実依存による接続試験。部分配布では明示SKIPし、代役を作らない。"""
from pathlib import Path
import ast
import unittest
from unittest.mock import patch

ROOT=Path(__file__).resolve().parents[1]


class 製品接続構造試験(unittest.TestCase):
    def test_通常入口の明示無効化と既定外部禁止を保持(self):
        tree=ast.parse((ROOT/'src/minidora/製品版/製品チャット.py').read_text(encoding='utf-8'))
        cls=next(n for n in tree.body if isinstance(n,ast.ClassDef) and n.name=='製品ミニドラ')
        init=next(n for n in cls.body if isinstance(n,ast.FunctionDef) and n.name=='__init__')
        defaults={a.arg:ast.literal_eval(v) for a,v in zip(init.args.kwonlyargs,init.args.kw_defaults)}
        self.assertTrue(defaults['監査改善']);self.assertFalse(defaults['汎用外部読取許可'])
        source=ast.unparse(tree)
        self.assertIn('監査改善=self._監査改善有効',source)
        self.assertIn('追加会話の焦点を離す()',source)


class 製品接続実試験(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        # 完全リポジトリがある場合のimport失敗はSKIPに変換しない。
        if not (ROOT/'src/minidora/hds_compiler.py').is_file():
            raise unittest.SkipTest('固定取得した部分構成。全製品依存なし。GitHub完全リポジトリCIで動的受入を行う')
        from minidora.製品版.製品チャット import 製品ミニドラ
        cls.製品型=製品ミニドラ

    def setUp(self):
        self.product=self.製品型()
        # 外部検索やネットワークに退避したら失敗する。能力や意味処理は全て実物。
        self.guard=patch('socket.create_connection',side_effect=AssertionError('外部読取を明示許可していない'))
        self.guard.start();self.addCleanup(self.guard.stop)

    def send(self,text,session='第25製品'):
        return self.product.応答(text,セッションID=session)

    def registered(self):
        r=self.send('命題資料「例」を登録：P。PならばQ。')
        self.assertEqual(r.状態,'合格',r.本文);self.assertEqual(r.経路,'汎用会話')

    def test_既定製品で資料から実三工程を完遂(self):
        self.registered()
        r=self.send('資料「例」に基づいて「Q」を判断してくれる？、短く説明して')
        self.assertEqual(r.状態,'合格',r.本文);self.assertIn('支持',r.本文)
        trace=r.メタデータ['汎用追跡']
        self.assertIn('HDS保持',trace)
        self.assertEqual(len(trace['監査改善']['工程作用']),3)

    def test_通常の挨拶と計算を奪わない(self):
        for raw in ('こんにちは','2+3'):
            r=self.send(raw)
            self.assertEqual(r.状態,'合格',r.本文);self.assertNotEqual(r.経路,'汎用会話')

    def test_別話題の後で追加能力の省略目的を使わない(self):
        self.registered();self.send('資料「例」から「Q」を判断して')
        self.send('こんにちは')
        r=self.send('もう少し短く説明して')
        self.assertNotEqual(r.経路,'汎用会話')
        self.assertEqual(self.send('資料「例」から「Q」を判断して').状態,'合格')

    def test_旧経路へ明示的に戻せる(self):
        self.product=self.製品型(監査改善=False)
        self.assertNotEqual(self.send('命題資料「例」を登録：P。').経路,'汎用会話')

    def test_選択後の失敗をCoreで補完しない(self):
        self.registered()
        r=self.send('資料「例」から「Q」を判断して、否定を無視して')
        self.assertNotEqual(r.状態,'合格');self.assertEqual(r.経路,'汎用会話')
        self.assertNotIn('支持',r.本文)

    def test_セッションをまたいで資料を利用しない(self):
        self.registered()
        r=self.send('資料「例」から「Q」を判断して',session='別セッション')
        self.assertNotEqual(r.状態,'合格')

    def test_初期化により追加資料を消す(self):
        self.registered();self.send('資料「例」から「Q」を判断して')
        self.assertEqual(self.send('会話を初期化して').状態,'合格')
        r=self.send('資料「例」から「Q」を判断して')
        self.assertNotEqual(r.状態,'合格')

    def test_仮説と介入へも既定入口から到達(self):
        for register,query in (
            ('仮説資料「天候」を登録：\n規則：RainならばWet\n候補：Rain',
             '資料「天候」で観測「Wet」を説明する仮説を検討して'),
            ('介入資料「連鎖」を登録：\n外生：U=真\n構造：A=U\n構造：B=A',
             '資料「連鎖」で「A=偽」に介入した結果を比較して')):
            self.assertEqual(self.send(register).状態,'合格')
            r=self.send(query)
            self.assertEqual(r.状態,'合格',r.本文);self.assertEqual(r.経路,'汎用会話')

if __name__=='__main__':unittest.main()

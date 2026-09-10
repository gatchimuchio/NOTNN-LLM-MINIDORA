"""構造文書の選択値を、実公開HDSと既存会話へ渡す。型・内容を別扱いする。"""
import unittest

from minidora.構造化文書 import 構造化文書を読む
from minidora.構造化文書操作 import 文書を処理
from minidora.文脈要求 import 文脈付き要求セッション


class 構造文書HDS接続試験(unittest.TestCase):
    def setUp(self):
        self.session=文脈付き要求セッション('構造文書-HDS')

    def material(self,n=731):
        r=構造化文書を読む('{"本文":"売上は'+str(n)+'です。費用は75です。","別欄":999}','JSON')
        r=文書を処理(r,'JSON選択',{'位置':'/本文'})
        return 文書を処理(r,'値取出',{'型':'文字列'})

    def test_選択した本文だけを実HDSへ渡す(self):
        r=self.session.応答('本文から数字を抽出して',{'本文':self.material()})
        self.assertTrue(r.成立,r.理由)
        self.assertEqual(r.出力[0][1].本文,'731、75')

    def test_次ターン照応が選択後の成果を使う(self):
        a=self.session.応答('本文を1行で要約して',{'本文':self.material()})
        self.assertTrue(a.成立,a.理由)
        b=self.session.応答('それから数字を抽出して')
        self.assertTrue(b.成立,b.理由)
        self.assertEqual(b.出力[0][1].本文,'731')

    def test_値の変更が既存Compiler結果へ到達(self):
        r=self.session.応答('本文から数字を抽出して',{'本文':self.material(222)})
        self.assertTrue(r.成立,r.理由)
        self.assertEqual(r.出力[0][1].本文,'222、75')

    def test_欠落位置の不成立を成功素材にしない(self):
        doc=構造化文書を読む('{"別欄":999}','JSON')
        material=文書を処理(doc,'JSON選択',{'位置':'/本文'})
        r=self.session.応答('本文から数字を抽出して',{'本文':material})
        self.assertFalse(r.成立)
        self.assertEqual(r.出力,())

    def test_CSV選択を日本語素材へ渡す(self):
        r=構造化文書を読む('本文,別欄\n値は731です。,999\n','CSV')
        for op,opts in [('形式変換',{'出力':'JSON','行表現':'対象'}),('JSON選択',{'位置':'/0/本文'}),('値取出',{'型':'文字列'})]:
            r=文書を処理(r,op,opts)
            self.assertTrue(r.成立,r.保留理由)
        out=self.session.応答('本文から数字を抽出して',{'本文':r})
        self.assertTrue(out.成立,out.理由)
        self.assertEqual(out.出力[0][1].本文,'731')


if __name__=='__main__':
    unittest.main()

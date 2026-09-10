"""編集済み本文を実公開HDSの会話処理に渡す接続試験。"""
import unittest

from minidora.文章作成 import 文章を取り込む, 保護範囲
from minidora.文章編集 import 文章を編集, 文章修正, 編集箇所を特定
from minidora.文脈要求 import 文脈付き要求セッション


class 文章HDS接続試験(unittest.TestCase):
    def setUp(self):
        self.session=文脈付き要求セッション('文章-HDS')

    def material(self,n=731):
        raw=文章を取り込む(f'旧名の値は{n}です。費用は75です。')
        proposal=編集箇所を特定(raw,'旧名','新名')
        return 文章を編集(raw,proposal['起点SHA256'],tuple(文章修正(**x) for x in proposal['修正']))

    def test_編集後の本文を実Compilerへ渡す(self):
        material=self.material();self.assertTrue(material.成立)
        r=self.session.応答('本文から数字を抽出して',{'本文':material})
        self.assertTrue(r.成立,r.理由);self.assertEqual(r.出力[0][1].本文,'731、75')

    def test_次turn照応が編集後の成果を使う(self):
        r=self.session.応答('本文を1行で要約して',{'本文':self.material()})
        self.assertTrue(r.成立,r.理由)
        r=self.session.応答('それから数字を抽出して')
        self.assertTrue(r.成立,r.理由);self.assertEqual(r.出力[0][1].本文,'731')

    def test_素材摂動がHDS結果にも到達(self):
        r=self.session.応答('本文から数字を抽出して',{'本文':self.material(222)})
        self.assertTrue(r.成立,r.理由);self.assertEqual(r.出力[0][1].本文,'222、75')

    def test_編集不成立の結果をHDS素材へ昇格しない(self):
        d=文章を取り込む('値120です。',(保護範囲('値',1,4,'120'),))
        failed=文章を編集(d,d.データ['記録SHA256'],(文章修正('改変',1,4,'120','999','試験'),))
        self.assertFalse(failed.成立)
        r=self.session.応答('本文から数字を抽出して',{'本文':failed})
        self.assertFalse(r.成立);self.assertEqual(r.出力,())

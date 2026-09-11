"""構造化能力の成功成果と日英文書依頼を同じ会話へ接続。実公開HDSを使用する。"""
from pathlib import Path
import runpy
import unittest
from minidora.統合実行 import 統合セッション
from minidora.製品版.型 import 能力結果
from test_統合実行 import 一工程, 数学計画


class 統合HDS試験(unittest.TestCase):
    def setUp(self):
        self.s=統合セッション('統合HDS')
        self.data={'本文':能力結果(True,'売上は731です。費用は75です。利益は45です。')}

    def ok(self,r):
        self.assertTrue(r.成立,(r.理由,r.解釈,r.実行))
        return r

    def test_日本語依頼を実HDSから共通実行器へ(self):
        r=self.ok(self.s.応答('本文から数字を抽出して',self.data))
        self.assertEqual(r.本文,'731、75、45')
        self.assertEqual(r.解釈['解釈'].HDS保持.原文,'本文から数字を抽出して')

    def test_数学成果を次ターンのそれで使う(self):
        self.ok(self.s.計画実行(*数学計画()))
        r=self.ok(self.s.応答('それから数字を抽出して'))
        self.assertEqual(r.本文,'27')

    def test_英文依頼も同じ会話成果へ接続(self):
        self.ok(self.s.応答('Summarize the text in exactly 1 line.',self.data,入力言語='en'))
        r=self.ok(self.s.応答('Extract numbers from it.',入力言語='en'))
        self.assertEqual(r.本文,'731')
        self.assertEqual(r.解釈['翻訳'].データ['入力']['本文'],'Extract numbers from it.')

    def test_失敗した依頼で最後の採用成果を上書きしない(self):
        self.ok(self.s.応答('本文を1行で要約して',self.data))
        before=self.s.保存文脈()
        failed=self.s.応答('本文から数字を抽出して。ただし正数だけにして',self.data)
        self.assertFalse(failed.成立)
        self.assertEqual(before,self.s.保存文脈())
        self.assertEqual(self.ok(self.s.応答('それから数字を抽出して')).本文,'731')

    def test_複数出力のそれは勝手に選ばない(self):
        root=Path(__file__).resolve().parents[1]
        maker=runpy.run_path(str(root/'tools/文章作成編集デモ.py'))['用意']
        self.ok(self.s.計画実行(*maker()))
        r=self.s.応答('それから数字を抽出して')
        self.assertFalse(r.成立)
        self.assertEqual(r.起点,r.更新後)

    def test_複数出力の番号を明示すれば解決する(self):
        root=Path(__file__).resolve().parents[1]
        maker=runpy.run_path(str(root/'tools/文章作成編集デモ.py'))['用意']
        self.ok(self.s.計画実行(*maker()))
        r=self.ok(self.s.応答('前の2番から数字を抽出して'))
        self.assertEqual(r.本文,'120')

    def test_20項目の文書依頼が切断なしで完了(self):
        data={'本文':能力結果(True,'。'.join('項目'+str(i) for i in range(20))+'。')}
        r=self.ok(self.s.応答('本文を箇条書きにして',data))
        self.assertEqual(len(r.本文.splitlines()),20)

    def test_厳密行数不達は採用しない(self):
        r=self.s.応答('Summarize the text in exactly 2 lines.',{'本文':能力結果(True,'一文だけです。')},入力言語='en')
        self.assertFalse(r.成立)
        self.assertEqual(r.起点,r.更新後)

    def test_別セッションと初期化後は参照を補完しない(self):
        self.ok(self.s.計画実行(*数学計画()))
        self.assertFalse(統合セッション('統合HDS').応答('それから数字を抽出して').成立)
        self.s.初期化()
        self.assertFalse(self.s.応答('それから数字を抽出して').成立)

    def test_任意数学自由文は構造化計画へ黙って置換しない(self):
        r=self.s.応答('この方程式をいい感じに解いて',{'式':能力結果(True,'x+1=3')})
        self.assertFalse(r.成立)
        self.assertEqual(r.起点,r.更新後)

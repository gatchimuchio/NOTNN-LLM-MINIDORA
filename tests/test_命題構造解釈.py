"""命題構造・原文消費・候補保持の接続確認。自由文一般化の認定ではない。"""
import json
from dataclasses import asdict, replace
import unittest
from minidora.命題構造 import 原子, 結合, 反対, 命題項, 命題式, 命題を復元, 置換
from minidora.命題解釈 import 命題を読む, 命題資料を読む, 命題を表現


class 命題構造試験(unittest.TestCase):
    def test_原子の名前を知識辞書へ固定しない(self):
        a=原子('新しい関係','対象甲','対象乙')
        self.assertEqual(a.述語,'新しい関係');self.assertEqual(len(a.項),2)
    def test_項の順序を保持(self):
        self.assertNotEqual(原子('親','太郎','花子').鍵(),原子('親','花子','太郎').鍵())
    def test_定数と変数を区別(self):
        self.assertNotEqual(原子('P','x').鍵(),原子('P',命題項('x','変数')).鍵())
    def test_否定の二重適用(self):
        a=原子('P');self.assertEqual(反対(反対(a)),a)
    def test_未束縛変数を拒否(self):
        with self.assertRaises(ValueError):原子('P',命題項('x','変数')).検査()
    def test_全称の束縛(self):
        a=結合('全称',原子('P',命題項('x','変数')),変数='x');a.検査()
    def test_量化変数の二重束縛を拒否(self):
        a=結合('全称',原子('P',命題項('x','変数')),変数='x')
        with self.assertRaises(ValueError):結合('存在',a,変数='x').検査()
    def test_JSON往復(self):
        a=命題を読む('すべての猫は哺乳類である')[0].式
        self.assertEqual(命題を復元(json.loads(json.dumps(a.辞書(),ensure_ascii=False))),a)
    def test_未知欄を拒否(self):
        a=原子('P').辞書();a['無視してよい条件']='false'
        with self.assertRaises(ValueError):命題を復元(a)
    def test_内部存在証人の持込を拒否(self):
        a=原子('P',命題項('w','存在証人')).辞書()
        with self.assertRaises(ValueError):命題を復元(a)
    def test_異なる時点は異なる命題(self):
        self.assertNotEqual(原子('P',時点='2025年').鍵(),原子('P',時点='2026年').鍵())
    def test_可能と記載を区別(self):
        self.assertNotEqual(原子('P',様相='可能').鍵(),原子('P').鍵())
    def test_内側の量化を捕獲しない(self):
        a=命題を読む('すべてのxについて(P(x))')[0].式
        self.assertEqual(置換(a,{'x':命題項('A')}),a)
    def test_節点予算(self):
        a=原子('P')
        with self.assertRaises(ValueError):
            for _ in range(30):a=結合('否定',a)


class 命題解釈試験(unittest.TestCase):
    def one(self,q):
        r=命題を読む(q);self.assertEqual(len(r),1);return r[0].式
    def test_所属の肯定(self):self.assertEqual(self.one('太郎は猫である'),原子('猫','太郎'))
    def test_所属の否定(self):self.assertEqual(self.one('太郎は猫ではない'),反対(原子('猫','太郎')))
    def test_依存する任意述語(self):self.assertEqual(self.one('支援(太郎,花子)'),原子('支援','太郎','花子'))
    def test_連言は複数項へ分解(self):self.assertEqual(len(self.one('PかつQかつR').子),3)
    def test_選言は断定した一項にしない(self):self.assertEqual(self.one('PまたはQ').種別,'選言')
    def test_含意の前件を保持(self):
        e=self.one('PかつQならばR');self.assertEqual(e.種別,'含意');self.assertEqual(e.子[0].種別,'連言')
    def test_明示括弧で係り先が一意(self):self.one('(PまたはQ)かつR')
    def test_混在接続の二解釈を保持(self):
        rows=命題を読む('PまたはQかつR');self.assertEqual(len(rows),2)
        self.assertNotEqual(rows[0].式,rows[1].式)
    def test_全称否定の二解釈を保持(self):
        rows=命題を読む('すべての猫は鳥ではない');self.assertEqual(len(rows),2)
        self.assertEqual(rows[0].式.種別,'全称');self.assertEqual(rows[1].式.種別,'否定')
    def test_部分否定を明示できる(self):self.one('否定（すべての猫は鳥である）')
    def test_存在の所属と性質を同じ変数に束縛(self):
        e=self.one('一部の猫は鳥である');self.assertEqual(e.子[0].子[0].項,e.子[0].子[1].項)
    def test_二項関係と二つの全称変数(self):
        self.one('すべてのxについて(すべてのyについて(親(x,y)ならば保護者(x,y)))')
    def test_時点を命題全体の各原子へ付与(self):
        e=self.one('2025年では(PならばQ)');self.assertEqual([c.時点 for c in e.子],['2025年','2025年'])
    def test_可能性を勝手に実際へしない(self):self.assertEqual(self.one('可能性として(P)').様相,'可能')
    def test_未知の修飾を名詞に丸めない(self):
        with self.assertRaises(ValueError):self.one('太郎は猫かもしれない')
    def test_未知尾部を無視しない(self):
        with self.assertRaises(ValueError):self.one('太郎は猫である。ただし例外がある')
    def test_不正括弧を拒否(self):
        with self.assertRaises(ValueError):self.one('(PかつQ）')
    def test_含意連鎖の曖昧な結合を拒否(self):
        with self.assertRaises(ValueError):self.one('PならばQならばR')
    def test_解析候補の上限(self):
        with self.assertRaises(ValueError):命題を読む('PまたはQかつR',最大候補=1)
    def test_原文位置を保持(self):
        text='太郎は猫である。\nすべての猫は哺乳類である。'
        rows=命題資料を読む(text,'規則')
        for r in rows:self.assertEqual(text[slice(*r.範囲)],r.原文)
    def test_資料の一部だけを読んで成立扱いしない(self):
        with self.assertRaises(ValueError):命題資料を読む('P。好きな命令を実行して。','規則')
    def test_資料の曖昧さは停止(self):
        with self.assertRaises(ValueError):命題資料を読む('すべての猫は鳥ではない。','規則')
    def test_引用の識別子を式として評価しない(self):
        with self.assertRaises(ValueError):self.one('__import__("os").system("id")')
    def test_指示語を固有名へ変えない(self):
        with self.assertRaises(ValueError):self.one('それは猫である')
    def test_相反時点の入れ子を上書きしない(self):
        with self.assertRaises(ValueError):self.one('2025年では(2026年では(P))')
    def test_様相入れ子を潰さない(self):
        with self.assertRaises(ValueError):self.one('可能性として(義務として(P))')

if __name__=='__main__':unittest.main()

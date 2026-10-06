from unittest import TestCase
from dataclasses import replace
from pathlib import Path
import tempfile,json
from minidora.HDS駆動コア import HDS駆動コア
from minidora.参照 import 参照記録,参照全保持を統合
from minidora.統合駆動_v2.適応記憶 import HDS適応記憶,_経験,_作用文脈
from minidora.コア.継続保存 import _符号化,_復号,_型登録

class 継続保存試験(TestCase):
    def setUp(self):
        self.一時=tempfile.TemporaryDirectory();self.addCleanup(self.一時.cleanup)
        self.場所=Path(self.一時.name)/'core.json';self.中核=HDS駆動コア()
    def test_参照の現版旧版を復元する(self):
        旧=参照記録('r','対象','旧本文','出典','供給器')
        self.中核._継続参照記憶=参照全保持を統合((旧,),(replace(旧,内容='新本文'),))
        前=self.中核.継続状態署名
        self.中核.継続状態を保存(self.場所,リポジトリ版='r1',完了問題番号=8)
        新=HDS駆動コア();番号=新.継続状態を復元(self.場所,リポジトリ版='r1')
        self.assertEqual(番号,8);self.assertEqual(新.継続状態署名,前)
        self.assertEqual(新.継続参照記憶[0].旧版[0].内容,'旧本文')
    def test_別版へ無言復元しない(self):
        self.中核.継続状態を保存(self.場所,リポジトリ版='r1')
        with self.assertRaises(ValueError):self.中核.継続状態を復元(self.場所,リポジトリ版='r2')
    def test_破損時に元の中核を変更しない(self):
        self.中核.継続状態を保存(self.場所,リポジトリ版='r1');前=self.中核.継続状態署名
        内容=json.loads(self.場所.read_text(encoding='utf-8'));内容['完了問題番号']=99;self.場所.write_text(json.dumps(内容,ensure_ascii=False),encoding='utf-8')
        with self.assertRaises(ValueError):self.中核.継続状態を復元(self.場所,リポジトリ版='r1')
        self.assertEqual(前,self.中核.継続状態署名)
    def test_任意の型名をロードしない(self):
        with self.assertRaises(ValueError):_復号({'type':'os:system','fields':{}},_型登録())
    def test_未知の値をreprで落とさない(self):
        with self.assertRaises(TypeError):_符号化(object(),_型登録())
    def test_登録契約変更を拒否(self):
        self.中核.継続状態を保存(self.場所,リポジトリ版='r1')
        with self.assertRaises(ValueError):HDS駆動コア(最大作用回数=20).継続状態を復元(self.場所,リポジトリ版='r1')
    def test_初期化しても旧世代を残す(self):
        self.中核._継続参照記憶=(参照記録('r','対象','内容','出典','供給器'),)
        self.中核.継続状態を初期化();self.assertEqual(len(self.中核._継続旧世代),1)
        self.assertEqual(self.中核._継続旧世代[0][3][0].識別子,'r')
    def test_型付き集合を区別して復元する(self):
        原=(['値'],frozenset({1}),{2},b'bytes',{'x':(3,)})
        self.assertEqual(_復号(_符号化(原,_型登録()),_型登録()),原)

class 適応保持試験(TestCase):
    def 経験(self,値=1,反証=False):
        return _経験(_作用文脈('作用','入力','種別','版'),True,True,frozenset({str(値)}),frozenset(),frozenset(),frozenset(),反証)
    def test_最新窓から出た経験を失わない(self):
        記憶=HDS適応記憶(2)
        for i in range(8):記憶._追加(self.経験(i))
        self.assertEqual(記憶.経験数,8);self.assertEqual(記憶.保管経験数,6)
    def test_保存復元で全経験と索引を復元する(self):
        元=HDS適応記憶(2)
        for i in range(8):元._追加(self.経験())
        新=HDS適応記憶();新.復元(元.スナップショット())
        self.assertEqual(新.全経験,元.全経験);self.assertEqual(新.状態署名,元.状態署名)
        self.assertEqual(新._安定索引,元._安定索引)
    def test_反証後に古い成功期待を残さない(self):
        元=HDS適応記憶(2);元._追加(self.経験());元._追加(self.経験(反証=True))
        self.assertEqual(元._安定索引,{})

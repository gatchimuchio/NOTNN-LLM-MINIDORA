from types import SimpleNamespace
from unittest import TestCase
from unittest.mock import patch

from minidora.HDS実行主体 import (
    HDS作用供給器, HDS実行状態, HDS関数作用, HDS作用結果, HDS作用状態,
)
from minidora.統合駆動_v2.計画 import HDS作用仕様
from minidora.駆動系.取得 import 作用供給を取得, 作用機会を取得
from minidora.駆動系.変換 import 作用を変換


class 入力不変最適化試験(TestCase):
    def test_未宣言供給器は隔離コピー上で構成する(self):
        可変=[]
        状態=HDS実行状態(成果=(("値",可変),))
        def 構成(入力状態):
            dict(入力状態.成果)["値"].append("変更")
            return ()
        主体=SimpleNamespace(作用供給器=(HDS作用供給器("外部",構成),),作用群=())
        政策=SimpleNamespace(最大内部生成=8)
        with self.assertRaises(ValueError):
            作用供給を取得(主体,状態,政策)
        self.assertEqual(可変,[])

    def test_入力不変保証供給器は全状態コピーを省略する(self):
        状態=HDS実行状態()
        主体=SimpleNamespace(作用供給器=(HDS作用供給器("内部",lambda s:(),入力不変保証=True),),作用群=())
        政策=SimpleNamespace(最大内部生成=8)
        with patch("minidora.駆動系.取得.deepcopy",side_effect=AssertionError("deepcopy禁止")):
            self.assertEqual(作用供給を取得(主体,状態,政策),())

    def test_未宣言作用は入力を隔離する(self):
        可変=[]
        状態=HDS実行状態(成果=(("値",可変),))
        def 実行(入力状態):
            dict(入力状態.成果)["値"].append("変更")
            return HDS作用結果(HDS作用状態.成立)
        作用=HDS関数作用("外部",実行)
        選択=作用.機会(状態)
        結果=作用を変換(作用,選択,状態)
        self.assertNotEqual(結果.状態,HDS作用状態.成立)
        self.assertEqual(可変,[])

    def test_入力不変保証作用は機会と実行で全状態コピーを省略する(self):
        状態=HDS実行状態()
        仕様=HDS作用仕様("内部",入力不変保証=True)
        作用=HDS関数作用("内部",lambda s:HDS作用結果(HDS作用状態.成立),計画仕様=仕様)
        with patch("minidora.駆動系.取得.deepcopy",side_effect=AssertionError("機会deepcopy禁止")):
            self.assertIsNotNone(作用機会を取得(作用,状態))
        with patch("minidora.駆動系.変換.deepcopy",side_effect=AssertionError("実行deepcopy禁止")):
            self.assertEqual(作用を変換(作用,SimpleNamespace(),状態).状態,HDS作用状態.成立)

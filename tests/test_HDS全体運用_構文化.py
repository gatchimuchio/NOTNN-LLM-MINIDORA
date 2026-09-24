"""現行構文化の正本を保ち、Legacy局所接続の責任境界を明示的に検査する。"""
from dataclasses import replace
import unittest
from minidora.HDS運用.構文化接続 import 運用構文化器, 局所接続を構成
from minidora.HDS運用 import HDS運用セッション
from minidora.HDS中間表現 import HDS座標, 値状態
from minidora.HDS目的射影 import _HDS照合


class 構文化責任接続試験(unittest.TestCase):
    def test_中核正本では監査副産物を局所ビューへ要求しない(self):
        接続 = 運用構文化器(); 局所 = 接続.コンパイル("2+3")
        self.assertEqual(接続.原IR.座標, 局所.座標)
        self.assertFalse(接続.責任対応)
        self.assertEqual(接続.コア入力.原文, 局所.原文)
        self.assertTrue(接続.コア入力.コア需要を検査())
        self.assertEqual(接続.原IR.残差, 局所.残差)
        self.assertEqual(接続.原IR.関係, 局所.関係)
        _HDS照合(局所, (), (), ())

    def test_旧監査座標は明示入力時だけ責任分離する(self):
        接続 = 運用構文化器(); 接続.コンパイル("2+3")
        原 = 接続.原IR
        監査 = HDS座標(
            "archv1:999", "監査.構造", "v1", 値状態.確定,
            由来="公開HDS 構文化器 構造 v1",
        )
        局所, 責任 = 局所接続を構成(replace(原, 座標=(*原.座標, 監査)))
        self.assertNotIn(監査, 局所.座標)
        self.assertEqual(len(責任), 1)
        self.assertFalse(責任[0]["解消済み認定"])
        self.assertEqual(原.原文, 局所.原文)

    def test_未解参照は消さず局所検査でも停止(self):
        接続 = 運用構文化器(); 局所 = 接続.コンパイル("それを計算して")
        self.assertTrue(局所.残差)
        self.assertEqual(局所.残差, 接続.原IR.残差)
        with self.assertRaises(ValueError):
            _HDS照合(局所, (), (), ())

    def test_未知の監査座標を一括免除しない(self):
        接続 = 運用構文化器(); 接続.コンパイル("2+3")
        原 = 接続.原IR
        追加 = HDS座標("archv1:999", "監査.未知要求", "特別な制限", 値状態.留保,
                      由来="公開HDS 構文化器 構造 v1")
        局所, _ = 局所接続を構成(replace(原, 座標=(*原.座標, 追加)))
        self.assertIn(追加, 局所.座標)
        with self.assertRaises(ValueError):
            _HDS照合(局所, (), (), ())

    def test_構文化器以外の由来では委譲メタデータへ分類しない(self):
        接続 = 運用構文化器(); 接続.コンパイル("2+3")
        原 = 接続.原IR
        点 = HDS座標("archv1:998", "監査.構造", "v1", 値状態.確定, 由来="利用者資料")
        局所, 責任 = 局所接続を構成(replace(原, 座標=(*原.座標, 点)))
        self.assertIn(点, 局所.座標)
        self.assertFalse(責任)

    def test_委譲以外の意味損失を消さない(self):
        接続 = 運用構文化器(); 接続.コンパイル("2+3")
        原 = 接続.原IR; 履歴 = list(原.意味作用履歴)
        履歴[-1] = replace(履歴[-1], 損失=(*履歴[-1].損失, "重要条件の未解釈"))
        局所, _ = 局所接続を構成(replace(原, 意味作用履歴=tuple(履歴)))
        with self.assertRaises(ValueError):
            _HDS照合(局所, (), (), ())

    def test_最終運用状態に全文と局所ビューの両方が残る(self):
        結果 = HDS運用セッション().応答("2+3")
        self.assertTrue(結果.成立, 結果.本文)
        記録 = dict(結果.HDS結果.状態.成果)["運用解釈"]["HDS"]
        self.assertEqual(記録["全文"]["座標"], 記録["局所作用ビュー"]["座標"])
        self.assertIn("責任対応", 記録)
        self.assertFalse(記録["責任対応"])

    def test_実際の否定条件をメタデータとして免除しない(self):
        結果 = HDS運用セッション().応答("2+3を計算しないで")
        self.assertFalse(結果.成立)
        self.assertFalse(結果.追跡["能力試行"])

"""v3最終文章照合の局所契約。通常生成と再生成を使い、製品/通信は使わない。"""
from copy import deepcopy
from hashlib import sha256
import base64
import json
import unittest
import zlib
from test_資料回答共有保存 import 資料回答共有接続試験
from minidora.HDS運用.内容構成 import _資料文章を照合, 資料文章を照合, 資料文章を検査
from minidora.HDS運用.資料回答共有保存 import (
    資料回答旧共有保存版, 資料回答第2共有保存版, 資料回答共有保存版,
    資料回答意味を読む, 資料回答意味を保存)
from minidora.HDS運用.資料回答 import 資料回答版
from minidora.HDS運用.値 import 結果を保存, 指紋


class 圧縮保存接続試験(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        資料回答共有接続試験.setUpClass()
        cls.構造 = 資料回答共有接続試験.構造
        cls.文章 = 資料回答共有接続試験.文章
        cls.旧 = 資料回答共有接続試験.旧
        cls.意味 = 資料回答共有接続試験.意味
        cls.新 = 資料文章を照合(cls.構造, cls.文章)

    def test_同じ意味の正当別圧縮frameを再圧縮差で拒否しない(self):
        成果 = deepcopy(self.新)
        保存 = 成果.データ["意味成果"]
        self.assertEqual(保存["版"], 資料回答共有保存版)
        元圧縮 = base64.b64decode(保存["圧縮本文"], validate=True)
        別圧縮 = zlib.compress(zlib.decompress(元圧縮), level=1)
        self.assertNotEqual(別圧縮, 元圧縮)
        保存.update(圧縮本文=base64.b64encode(別圧縮).decode("ascii"),
            圧縮バイト数=len(別圧縮), 圧縮SHA256=sha256(別圧縮).hexdigest())
        self.assertEqual(資料回答意味を読む(保存, 意味版=資料回答版), self.意味)
        原 = 指紋(結果を保存(成果))
        self.assertTrue(資料文章を検査(成果))
        self.assertEqual(指紋(結果を保存(成果)), 原)

    def test_正しく圧縮した異義でも実資料再生成と異なれば拒否(self):
        成果 = deepcopy(self.新)
        異義 = deepcopy(self.意味)
        異義["未使用記載"].append("原資料にない記載")
        成果.データ["意味成果"] = 資料回答意味を保存(異義, 意味版=資料回答版)
        原 = 指紋(結果を保存(成果))
        self.assertFalse(資料文章を検査(成果))
        self.assertEqual(指紋(結果を保存(成果)), 原)

    def test_圧縮印の改変と生成本文の改変を最終照合で拒否(self):
        for 対象 in ("圧縮印", "文章"):
            with self.subTest(対象=対象):
                成果 = deepcopy(self.新)
                if 対象 == "圧縮印":
                    成果.データ["意味成果"]["圧縮SHA256"] = "0" * 64
                else:
                    成果.データ["文章"]["内容"]["本文"] = "原資料にない回答"
                原 = 指紋(結果を保存(成果))
                self.assertFalse(資料文章を検査(成果))
                self.assertEqual(指紋(結果を保存(成果)), 原)

    def test_旧二版とplainは同版照合し保存を更新しない(self):
        for 版 in (False, 資料回答旧共有保存版, 資料回答第2共有保存版):
            with self.subTest(版=版):
                成果 = _資料文章を照合(self.構造, self.文章, 形式=None, 共有保存=版)
                原 = 指紋(結果を保存(成果))
                self.assertTrue(資料文章を検査(成果))
                self.assertEqual(指紋(結果を保存(成果)), 原)
                self.assertEqual(成果.データ["意味成果"]["版"], 版 if 版 else 資料回答版)

    def test_新保存の採否組位置と展開意味をplainと一致保持(self):
        原旧 = 結果を保存(self.旧)
        原新 = 結果を保存(self.新)
        self.assertEqual(原新["採否"], 原旧["採否"])
        self.assertEqual(原新["組位置"], 原旧["組位置"])
        展開 = deepcopy(原新)
        展開["内容"]["データ"]["意味成果"] = 資料回答意味を読む(self.新.データ["意味成果"], 意味版=資料回答版)
        self.assertEqual(展開, 原旧)


if __name__ == "__main__":
    unittest.main()

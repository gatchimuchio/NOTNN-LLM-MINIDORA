"""保存値の一回読取後も全源照合・旧版拒否を保つ有限対照。性能評価ではない。"""
import base64
from copy import deepcopy
from dataclasses import replace
from hashlib import sha256
import unittest
from unittest.mock import patch
import zlib

from minidora.HDS運用 import 内容構成 as 内容
from minidora.HDS運用 import 資料回答 as 回答
from minidora.HDS運用 import 資料回答共有保存 as 保存
from minidora.HDS運用.一般依頼 import 一般依頼を読む
from minidora.HDS運用.意味資料 import 資料意味を選ぶ
from minidora.HDS運用.値 import 結果を保存
from minidora.製品版.型 import 能力結果


def 構造を作る(本文):
    要求 = {"版": "HDS一般会話要求-v2", "対象": [], "主題": ["手押し車"], "操作": ["説明"],
            "形式": "文章", "範囲": "自動", "最大文字数": 24000, "問い": "手押し車の定義",
            "比較対象": [], "観点": [], "詳細": "標準", "提示本文": "", "関係焦点": ["定義"], "肯否": "未指定"}
    return 資料意味を選ぶ({"有限原資料" + "資料名" * 40: 能力結果(True, 本文)}, 要求)


class 資料文章一回再導出試験(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        本文 = "手押し車は荷物を運ぶ器具である。\n" + "\n".join(
            "荷台" + str(番) + "は付属部品である。" for 番 in range(45))
        cls.構造 = 構造を作る(本文)
        cls.文章 = 内容._文章(cls.構造)
        cls.成果 = 内容.資料文章を照合(cls.構造, cls.文章)
        cls.意味 = 保存.資料回答意味を読む(cls.成果.データ["意味成果"], 意味版=回答.資料回答版)
        if cls.成果.データ["意味成果"]["版"] != 保存.資料回答共有保存版:
            raise AssertionError("有限素材が圧縮保存境界を自然に越えていない")

    def test_全源と公開返値を保ち一読一再導出で成立(self):
        原 = deepcopy(結果を保存(self.成果))
        with patch.object(内容, "_圧縮保存を読む", wraps=保存._圧縮保存を読む) as 読取, \
             patch.object(回答, "回答意味を構成", wraps=回答.回答意味を構成) as 再導出:
            self.assertTrue(内容.資料文章を検査(self.成果))
        self.assertEqual(読取.call_count, 1)
        self.assertEqual(再導出.call_count, 1)
        self.assertEqual(結果を保存(self.成果), 原)
        self.assertIsNone(内容.資料文章の版を検査(self.成果))
        仕様, 意味 = 内容._内容仕様と意味を構成(self.構造)
        self.assertEqual(内容.内容仕様を構成(self.構造), 仕様)
        self.assertEqual(回答.会話内容仕様を構成(self.構造), 仕様)
        self.assertEqual(意味, self.意味)
        self.assertTrue(all(行["必須"] and 行["保護"] for 行 in 仕様["仕様"]["単位群"]))

    def test_有効な別圧縮列は原frameのまま照合(self):
        成果 = deepcopy(self.成果)
        frame = 成果.データ["意味成果"]
        元 = zlib.decompress(base64.b64decode(frame["圧縮本文"]))
        圧縮 = zlib.compress(元, level=1)
        frame.update(圧縮本文=base64.b64encode(圧縮).decode("ascii"),
                     圧縮SHA256=sha256(圧縮).hexdigest(), 圧縮バイト数=len(圧縮))
        原 = deepcopy(結果を保存(成果))
        self.assertNotEqual(frame["圧縮本文"], self.成果.データ["意味成果"]["圧縮本文"])
        self.assertTrue(内容.資料文章を検査(成果))
        self.assertEqual(結果を保存(成果), 原)

    def test_整合した再封緘でも使用記載の意味改変を拒否(self):
        改変 = deepcopy(self.意味)
        改変["使用記載"] = []
        成果 = deepcopy(self.成果)
        成果.データ["意味成果"] = 保存.資料回答意味を保存(改変, 意味版=回答.資料回答版)
        self.assertEqual(保存.資料回答意味を読む(成果.データ["意味成果"], 意味版=回答.資料回答版), 改変)
        self.assertFalse(内容.資料文章を検査(成果))

    def test_原印文章構造の改変を拒否し元成果を変えない(self):
        for 対象 in ("原印", "文章", "原資料"):
            成果 = deepcopy(self.成果)
            if 対象 == "原印": 成果.データ["意味成果"]["原正準SHA256"] = "0" * 64
            elif 対象 == "文章": 成果 = replace(成果, 本文=成果.本文 + "追加")
            else: next(iter(成果.データ["構造"]["資料群"].values()))["資料"]["内容"]["本文"] += "追加"
            原 = deepcopy(結果を保存(成果))
            with self.subTest(対象=対象):
                self.assertFalse(内容.資料文章を検査(成果))
                self.assertEqual(結果を保存(成果), 原)

    def test_旧意味版は全源再導出より先に拒否(self):
        成果 = deepcopy(self.成果)
        成果.データ["意味成果"]["意味版"] = "HDS資料回答内容-v16"
        with patch.object(内容, "_文章と意味を構成", side_effect=AssertionError("旧版の再生成")):
            self.assertFalse(内容.資料文章を検査(成果))
            with self.assertRaises(ValueError): 内容.資料文章の版を検査(成果)

    def test_非一般成果への一般圧縮frame付加を拒否(self):
        要求 = 一般依頼を読む({"原文": "資料「A」の保守について要点を整理して"})["要求"]
        構造 = 資料意味を選ぶ({"A": 能力結果(True, "保守は月に一回行う。")}, 要求)
        成果 = 内容.資料文章を照合(構造, 内容._文章(構造))
        self.assertTrue(内容.資料文章を検査(成果))
        成果.データ["意味成果"] = deepcopy(self.成果.データ["意味成果"])
        self.assertFalse(内容.資料文章を検査(成果))

    def test_再構成中に変わったcallerの成果は拒否(self):
        成果 = deepcopy(self.成果)
        再構成 = 内容._文章と意味を構成
        def 途中変更(*args, **kwargs):
            結果 = 再構成(*args, **kwargs)
            成果.データ["照合"] += "途中変更"
            return 結果
        with patch.object(内容, "_文章と意味を構成", side_effect=途中変更):
            self.assertFalse(内容.資料文章を検査(成果))

    def test_plainと旧共有二版は同じ保存形式で照合(self):
        for 版 in (None, 保存.資料回答旧共有保存版, 保存.資料回答第2共有保存版):
            成果 = deepcopy(self.成果)
            成果.データ["意味成果"] = deepcopy(self.意味) if 版 is None else 保存.資料回答意味を保存(
                self.意味, 意味版=回答.資料回答版, 保存版=版)
            原 = deepcopy(結果を保存(成果))
            with self.subTest(版=版):
                self.assertTrue(内容.資料文章を検査(成果))
                self.assertEqual(結果を保存(成果), 原)


if __name__ == "__main__":
    unittest.main()

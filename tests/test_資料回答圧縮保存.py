"""可逆保存の有限対照。人工JSONを使い意味生成・実製品は呼ばない。"""
import base64
from copy import deepcopy
from hashlib import sha256
import json
import random
import string
import unittest
from unittest.mock import patch
import zlib

from minidora.HDS運用.資料回答共有保存 import (
    資料回答共有保存版, 資料回答第2共有保存版, 資料回答旧共有保存版,
    資料回答意味を保存, 資料回答意味を読む,
)

_意味版 = "人工資料回答-v1"
_共有保存参照先 = "minidora.HDS運用.資料回答共有保存."


def _正準(値):
    return json.dumps(値, ensure_ascii=False, sort_keys=True,
                      separators=(",", ":"), allow_nan=False).encode("utf-8")


def _意味():
    所有 = {"資料ID": "人工所有一", "保存指紋": "a" * 64,
            "全記載ID": ["人工原記載:" + str(番) for 番 in range(2000)]}
    行群, 座標群 = [], []
    for 番 in range(30):
        座標 = {"座標ID": "人工座標:" + str(番), "原文範囲": [番, 番 + 1],
                "内容": {"原文": "未確定な限定もそのまま残す。", "型": None}}
        行群.append({"ID": "人工記載:" + str(番),
                     "資料作用": {"原資料": deepcopy(所有), "座標": [deepcopy(座標)]},
                     "不明": [None, "原記載の未読解"]})
        座標群.append(座標)
    return {"版": _意味版, "記載関係": 行群,
            "資料作用成果": {"原資料": [deepcopy(所有)], "座標": 座標群, "適用": {}},
            "未使用記載": ["人工記載:29"], "残差": {"不明条件": None},
            "型": [True, False, 1, 1.0, -0.0, None, "", "字"],
            "意味作用の独自反復": [{"状態": "未確定", "内容": "採用しない"}] * 20}


def _内部(保存):
    return json.loads(zlib.decompress(base64.b64decode(保存["圧縮本文"])))


def _詰め直す(保存, *, 対象=None, 原=None, 圧縮=None):
    保存 = deepcopy(保存)
    if 原 is None:
        原 = _正準(_内部(保存) if 対象 is None else 対象)
    if 圧縮 is None:
        圧縮 = zlib.compress(原, level=9)
    保存.update({"圧縮前SHA256": sha256(原).hexdigest(), "圧縮前バイト数": len(原),
                 "圧縮SHA256": sha256(圧縮).hexdigest(), "圧縮バイト数": len(圧縮),
                 "圧縮本文": base64.b64encode(圧縮).decode("ascii")})
    return 保存


class 資料回答圧縮保存試験(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.意味 = _意味()
        cls.原 = _正準(cls.意味)
        cls.保存 = 資料回答意味を保存(cls.意味, 意味版=_意味版)

    def 読む(self, 保存):
        return 資料回答意味を読む(保存, 意味版=_意味版)

    def test_新版は全原正準型未知残差を完全復元して圧縮する(self):
        self.assertEqual(self.保存["版"], 資料回答共有保存版)
        self.assertEqual(self.保存["圧縮対象"], "閉共有JSON-v1")
        self.assertEqual(self.保存["原正準SHA256"], sha256(self.原).hexdigest())
        self.assertEqual(self.保存["原正準バイト数"], len(self.原))
        self.assertLess(self.保存["圧縮バイト数"], 1_000_000)
        self.assertLess(len(_正準(self.保存)), 1_400_000)
        展開 = self.読む(self.保存)
        self.assertEqual(_正準(展開), self.原)
        for 新, 旧 in zip(展開["型"], self.意味["型"]):
            self.assertIs(type(新), type(旧))

    def test_入力保存と別箇所に可変参照を共有しない(self):
        保存原 = _正準(self.保存)
        展開 = self.読む(self.保存)
        展開["記載関係"][0]["資料作用"]["原資料"]["全記載ID"].clear()
        self.assertEqual(len(展開["記載関係"][1]["資料作用"]["原資料"]["全記載ID"]), 2000)
        self.assertEqual(_正準(self.意味), self.原)
        self.assertEqual(_正準(self.保存), 保存原)

    def test_別の正当圧縮streamを読み同版保存元のbyteを保持する(self):
        内部原 = _正準(_内部(self.保存))
        別圧縮 = zlib.compress(内部原, level=1)
        元 = _詰め直す(self.保存, 原=内部原, 圧縮=別圧縮)
        self.assertNotEqual(元["圧縮本文"], self.保存["圧縮本文"])
        self.assertEqual(_正準(self.読む(元)), self.原)
        保持 = 資料回答意味を保存(self.意味, 意味版=_意味版, 保存元=元)
        self.assertEqual(_正準(保持), _正準(元))
        保持["圧縮本文"] = "改変"
        self.assertNotEqual(保持["圧縮本文"], 元["圧縮本文"])
        異義 = deepcopy(self.意味)
        異義["残差"]["不明条件"] = "根拠にない補完"
        with self.assertRaisesRegex(ValueError, "原正準が不一致"):
            資料回答意味を保存(異義, 意味版=_意味版, 保存元=元)

    def test_v1v2同版schema原保存と宣言上限を維持する(self):
        for 版, 上限 in ((資料回答旧共有保存版, 16_000_000), (資料回答第2共有保存版, 32_000_000)):
            with self.subTest(版=版):
                旧 = 資料回答意味を保存(self.意味, 意味版=_意味版, 保存版=版)
                原保存 = _正準(旧)
                self.assertIn("共有値", 旧)
                self.assertNotIn("圧縮本文", 旧)
                展開 = self.読む(旧)
                self.assertEqual(_正準(展開), self.原)
                self.assertEqual(_正準(資料回答意味を保存(展開, 意味版=_意味版, 保存版=版)), 原保存)
                self.assertEqual(_正準(旧), 原保存)
                改変 = deepcopy(旧)
                改変["原正準バイト数"] = 上限 + 1
                with patch(_共有保存参照先 + "_箇所へ置く", side_effect=AssertionError("展開禁止")), self.assertRaises(ValueError):
                    self.読む(改変)
                with self.assertRaisesRegex(ValueError, "v3同版"):
                    資料回答意味を保存(self.意味, 意味版=_意味版, 保存版=版, 保存元=旧)

    def test_旧plainのtupleと32段を新境界へ狭めない(self):
        深部 = "端"
        for _ in range(31): 深部 = [深部]
        for 元 in ({"版": _意味版, "組": (1, [2])}, {"版": _意味版, "深部": 深部}):
            with self.subTest(欄=list(元)):
                保存 = 資料回答意味を保存(元, 意味版=_意味版)
                self.assertEqual(保存, 元)
                self.assertEqual(self.読む(保存), 元)
                if "組" in 元:
                    self.assertIs(type(保存["組"]), tuple)
                    self.assertIs(type(self.読む(保存)["組"]), tuple)
        with self.assertRaises(ValueError):
            資料回答意味を保存({"版": _意味版, "深部": [深部]}, 意味版=_意味版)

    def test_原深さ29は内部共有の追加階層を使わず圧縮できる(self):
        深部 = "原" * 200000
        for _ in range(28): 深部 = [深部]
        元 = {"版": _意味版, "深部": 深部}
        保存 = 資料回答意味を保存(元, 意味版=_意味版)
        self.assertEqual(保存["原深さ"], 29)
        self.assertEqual(保存["圧縮対象"], "原正準JSON")
        self.assertEqual(_正準(self.読む(保存)), _正準(元))

    def test_小量非有利と圧縮上限外はplainを保つ(self):
        小 = {"版": _意味版, "値": "小量"}
        self.assertEqual(資料回答意味を保存(小, 意味版=_意味版), 小)
        rng = random.Random(17)
        元 = {"版": _意味版, "値": "".join(rng.choices(string.ascii_letters + string.digits, k=620000))}
        self.assertEqual(_正準(資料回答意味を保存(元, 意味版=_意味版)), _正準(元))
        with patch(_共有保存参照先 + "_圧縮上限", 10):
            self.assertEqual(_正準(資料回答意味を保存(self.意味, 意味版=_意味版)), self.原)
        with patch(_共有保存参照先 + "_圧縮展開上限", 100):
            self.assertEqual(_正準(資料回答意味を保存(self.意味, 意味版=_意味版)), self.原)

    def test_非有限数外国型循環同ID異義を退避で隠さない(self):
        循環 = []; 循環.append(循環)
        for 値 in (float("nan"), float("inf"), b"raw", {1: "整数鍵"}, 循環):
            with self.subTest(型=type(値).__name__), self.assertRaises(ValueError):
                資料回答意味を保存({"版": _意味版, "値": 値}, 意味版=_意味版)
        for 種別 in ("所有", "座標"):
            元 = deepcopy(self.意味)
            if 種別 == "所有": 元["資料作用成果"]["原資料"][0]["保存指紋"] = "b" * 64
            else: 元["資料作用成果"]["座標"][0]["内容"]["型"] = "不正"
            with self.subTest(種別=種別), self.assertRaisesRegex(ValueError, "同ID異義"):
                資料回答意味を保存(元, 意味版=_意味版)
        with patch(_共有保存参照先 + "_圧縮展開上限", 10), self.assertRaises(ValueError):
            資料回答意味を保存({"版": _意味版, "先": "原" * 100, "後": float("nan")}, 意味版=_意味版)

    def test_frameの欄型版印量上限を解凍前に拒否する(self):
        変更 = [("新欄", True), ("意味版", "旧意味"), ("圧縮形式", "gzip"),
              ("圧縮対象", "任意IR"), ("原正準バイト数", True), ("原深さ", True),
              ("原正準バイト数", 128000001), ("原深さ", 30),
              ("圧縮前バイト数", 128000001), ("圧縮バイト数", 1000001),
              ("圧縮前バイト数", False), ("圧縮SHA256", "F" * 64)]
        for 欄, 値 in 変更:
            元 = deepcopy(self.保存); 元[欄] = 値
            with self.subTest(欄=欄, 値=値), patch(_共有保存参照先 + "zlib.decompressobj", side_effect=AssertionError("解凍禁止")), self.assertRaises(ValueError):
                self.読む(元)
        for 欄 in ("原正準SHA256", "圧縮前SHA256", "圧縮SHA256"):
            元 = deepcopy(self.保存); 元[欄] = "0" * 64
            with self.subTest(欄=欄), self.assertRaises(ValueError): self.読む(元)
        元 = deepcopy(self.保存); 元["原正準バイト数"] += 1
        with self.assertRaises(ValueError): self.読む(元)
        元 = deepcopy(self.保存); 元["原深さ"] += 1
        with self.assertRaises(ValueError): self.読む(元)

    def test_base64不正やframe過大量を解凍前に拒否する(self):
        for 本文 in ("!", "é", self.保存["圧縮本文"] + "\n", "A" * 1333337):
            元 = deepcopy(self.保存); 元["圧縮本文"] = 本文
            with self.subTest(文字数=len(本文)), patch(_共有保存参照先 + "zlib.decompressobj", side_effect=AssertionError("解凍禁止")), self.assertRaises(ValueError):
                self.読む(元)
        元 = deepcopy(self.保存); 元["圧縮本文"] = "A" * 1400000
        with patch(_共有保存参照先 + "zlib.decompressobj", side_effect=AssertionError("解凍禁止")), self.assertRaises(ValueError): self.読む(元)

    def test_junk連結stream不完全終端と宣言超過をJSON化前に拒否する(self):
        圧縮 = base64.b64decode(self.保存["圧縮本文"])
        内部原 = _正準(_内部(self.保存))
        for 不正 in (圧縮 + b"junk", 圧縮 + zlib.compress(b"{}"), 圧縮[:-1], b"bad zlib"):
            元 = _詰め直す(self.保存, 原=内部原, 圧縮=不正)
            with self.subTest(長さ=len(不正)), patch(_共有保存参照先 + "_厳密JSON", side_effect=AssertionError("JSON化禁止")), self.assertRaises(ValueError):
                self.読む(元)
        元 = deepcopy(self.保存); 元["圧縮前バイト数"] -= 100
        with patch(_共有保存参照先 + "_厳密JSON", side_effect=AssertionError("JSON化禁止")), self.assertRaises(ValueError): self.読む(元)
        元 = _詰め直す(self.保存, 原=b" " * 2000000)
        元["圧縮前バイト数"] = 20
        with patch(_共有保存参照先 + "_厳密JSON", side_effect=AssertionError("JSON化禁止")), self.assertRaises(ValueError): self.読む(元)

    def test_UTF8重複key非有限数非正準JSONと構文深さを拒否する(self):
        for 原 in (b"\xff", b'{"x":1,"x":2}', b'{"x":NaN}', b'{"x":Infinity}',
                  b'{"x":1e400}', b'{"x":"\\ud800"}', b'{ "x":1 }',
                  b"[" * 40 + b"0" + b"]" * 40):
            元 = _詰め直す(self.保存, 原=原)
            with self.subTest(原長=len(原)), self.assertRaises(ValueError): self.読む(元)

    def test_閉共有pool参照未知異義と再封緘順序を拒否する(self):
        内部 = _内部(self.保存)
        def pool重複(元): 元["共有値"].append(deepcopy(元["共有値"][0]))
        def 参照重複(元): 元["参照置換"].append(deepcopy(元["参照置換"][0]))
        def pool孤児(元): 元["参照置換"] = 元["参照置換"][1:]
        def pool参照(元): 元["参照置換"][0]["パス"] = ["共有値", 0, "値"]
        def 元印(元): 元["原正準SHA256"] = "0" * 64
        def 順序(元): 元["参照置換"].reverse()
        for 修理 in (pool重複, 参照重複, pool孤児, pool参照, 元印, 順序):
            元 = deepcopy(内部); 修理(元)
            with self.subTest(反例=修理.__name__), self.assertRaises(ValueError): self.読む(_詰め直す(self.保存, 対象=元))

    def test_閉共有の展開爆発を箇所複製前に拒否する(self):
        内部 = _内部(self.保存)
        所有 = next(行 for 行 in 内部["共有値"] if 行["種別"] == "所有")
        内部["本体"]["資料作用成果"]["原資料"] = [None] * 10000
        内部["参照置換"] = [行 for 行 in 内部["参照置換"] if 行["パス"][:2] != ["資料作用成果", "原資料"]]
        内部["参照置換"] += [{"パス": ["資料作用成果", "原資料", 番], "共有ID": 所有["共有ID"]} for 番 in range(10000)]
        元 = _詰め直す(self.保存, 対象=内部)
        with patch(_共有保存参照先 + "_箇所へ置く", side_effect=AssertionError("複製禁止")), self.assertRaisesRegex(ValueError, "展開バイト上限"):
            self.読む(元)

    def test_未知版を黙って新版へ変更しない(self):
        for 版 in ("HDS資料回答共有保存-v4", True, [資料回答共有保存版]):
            with self.subTest(版=版), self.assertRaises(ValueError):
                資料回答意味を保存(self.意味, 意味版=_意味版, 保存版=版)
        元 = deepcopy(self.保存); 元["版"] = "HDS資料回答共有保存-v4"
        with self.assertRaisesRegex(ValueError, "失効"): self.読む(元)
        self.assertEqual(_正準(self.意味), self.原)


if __name__ == "__main__":
    unittest.main()

"""明示保存版の有限境界を純粋交換値で検査する。実運用の成立は認定しない。"""
import base64
from copy import deepcopy
from hashlib import sha256
import json
import random
import unittest
from unittest.mock import patch
import zlib

from minidora.HDS運用.原記録 import (
    運用原記録, 原記録成果を復元, _結果を符号化, _符号の元長,
)
from minidora.HDS運用.値 import 結果を保存, 結果を復元, 指紋
from minidora.能力結果復元 import 能力結果を復元
from minidora.長文脈管理 import 長文脈庫, 文脈登録, 文脈選択要求
from minidora.製品版.型 import 能力結果, 参照資料


def 正準(値):
    return json.dumps(値, ensure_ascii=False, sort_keys=True, separators=(",", ":"), allow_nan=False).encode("utf-8")


def 同期(庫, 成果, **設定):
    return 庫.同期候補({"資料": {}, "原文": "一般の保存検査"}, None, 成果, {}, **設定)


def 成果行(庫):
    return 庫.保存()["庫"]["履歴"][-1]["追加"][0]


def 行の長さを持つ成果(長さ):
    元 = 能力結果(True, "", データ={"保存文字": ""})
    行 = {"識別子": "A", "内容": 結果を保存(元)["内容"], "種別": "成果", "依存": [],
          "固定": False, "順番": 1, "追加改訂": 1}
    return 能力結果(True, "", データ={"保存文字": "x" * (長さ - len(正準(行)))})


def 交換長を持つ成果(長さ):
    元 = 能力結果(True, "", データ={"保存文字": ""})
    return 能力結果(True, "", データ={"保存文字": "x" * (長さ - len(正準(結果を保存(元))))})


class 原記録有限契約試験(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.元 = 能力結果(True, "保存成果", 根拠=("元の範囲",),
                         参照=(参照資料("人工材料", "原資料", "有限検査", 本文="人工原文" * 25_000),),
                         データ={"原文": "x" * 550_000, "区間": (0, 550_000),
                                 "意味成果": {"版": "不透明な保存型", "符号列": "保持する文字", "原印": "a"}})
        cls.新 = 同期(運用原記録("有限新型"), cls.元)
        cls.行 = 成果行(cls.新)

    def test_一般既定の保存形式と初期hash及び選択上限は旧値(self):
        庫 = 長文脈庫("一般旧契約")
        self.assertEqual(庫.保存文字列(), 正準({"版": "MINIDORA-長文脈-v0.1", "セッションID": "一般旧契約",
                        "世代": 0, "上限": [4096, 16_000_000], "履歴": []}).decode("utf-8"))
        self.assertEqual(庫.起点().記録ハッシュ, "cfda4cdca34aaaf5fc74f7f51c9eb42ffd27f033cfe2863297a658f3c82bca59")
        self.assertEqual(長文脈庫.復元(庫.保存文字列()).保存文字列(), 庫.保存文字列())
        with self.assertRaises(ValueError):
            庫.選択(文脈選択要求(最大バイト数=1_000_001))

    def test_明示二百万版の形式と起点及び同版復元(self):
        庫 = 長文脈庫("一般明示", 最大単一記録バイト数=2_000_000)
        原 = json.loads(庫.保存文字列())
        self.assertEqual((原["版"], 原["上限"]), ("MINIDORA-長文脈-v0.2", [4096, 16_000_000, 2_000_000]))
        self.assertEqual(庫.起点().記録ハッシュ,
                         sha256(正準({"版": "MINIDORA-長文脈-v0.2", "初期状態": True})).hexdigest())
        self.assertEqual(長文脈庫.復元(庫.保存文字列()).保存文字列(), 庫.保存文字列())
        with self.assertRaises(ValueError):
            庫.選択(文脈選択要求(最大バイト数=1_000_001))
        for 値 in (True, 0, 999_999, 1_500_000, 2_000_001, "2000000"):
            with self.subTest(上限=値), self.assertRaises(ValueError):
                長文脈庫("不正上限", 最大単一記録バイト数=値)

    def test_保存版と単一上限の不一致を復元しない(self):
        新 = json.loads(長文脈庫("版境界", 最大単一記録バイト数=2_000_000).保存文字列())
        旧 = json.loads(長文脈庫("版境界").保存文字列())
        変更群 = []
        for 版, 上限 in ((新["版"], [4096, 16_000_000]), (旧["版"], 新["上限"]),
                         (新["版"], [4096, 16_000_000, 1_000_000]),
                         (新["版"], [4096, 16_000_000, True]), ("未知", 新["上限"])):
            変更群.append({**新, "版": 版, "上限": 上限})
        変更群.append({**新, "追加欄": 1})
        for 値 in 変更群:
            with self.subTest(変更=値["版"]), self.assertRaises(ValueError):
                長文脈庫.復元(正準(値).decode("utf-8"))

    def test_単一一百万と二百万の境界は原子的で旧既定を広げない(self):
        for 上限 in (1_000_000, 2_000_000):
            with self.subTest(上限=上限):
                庫 = 長文脈庫("単一境界", 最大単一記録バイト数=上限)
                庫.更新(庫.起点(), (文脈登録("A", 行の長さを持つ成果(上限), "成果"),))
                行 = json.loads(庫.保存文字列())["履歴"][0]["追加"][0]
                self.assertEqual(len(正準(行)), 上限)
                self.assertEqual(長文脈庫.復元(庫.保存文字列()).保存文字列(), 庫.保存文字列())
                空庫 = 長文脈庫("単一境界", 最大単一記録バイト数=上限)
                前 = 空庫.保存文字列()
                with self.assertRaisesRegex(ValueError, "単一記録サイズ上限"):
                    空庫.更新(空庫.起点(), (文脈登録("A", 行の長さを持つ成果(上限 + 1), "成果"),))
                self.assertEqual(空庫.保存文字列(), 前)

    def test_新運用は明示新庫と新可逆版を保存する(self):
        原 = self.新.保存()
        self.assertEqual(原["版"], "HDS運用原記録-v3")
        self.assertEqual(原["庫"]["上限"], [4096, 16_000_000, 2_000_000])
        self.assertEqual(self.行["内容"]["データ"]["運用結果"]["版"], "HDS原記録可逆保存-v2")
        self.assertEqual(正準(運用原記録.復元(原, "有限新型").保存()), 正準(原))

    def test_旧保存は無更新同bytesで旧実更新からv3へ昇格しない(self):
        旧v2 = 同期(運用原記録("旧保存", 保存版="HDS運用原記録-v2"), 能力結果(True, "旧成果")).保存()
        for 版 in ("HDS運用原記録-v1", "HDS運用原記録-v2"):
            原 = {**deepcopy(旧v2), "版": 版}
            復元 = 運用原記録.復元(原, "旧保存")
            self.assertEqual(正準(復元.保存()), 正準(原))
            新 = 同期(復元, self.元).保存()
            self.assertEqual(新["版"], "HDS運用原記録-v2")
            self.assertEqual(新["庫"]["版"], "MINIDORA-長文脈-v0.1")
            self.assertEqual(新["庫"]["上限"], [4096, 16_000_000])
            self.assertEqual(新["庫"]["履歴"][:-1], 原["庫"]["履歴"])
            self.assertEqual(新["庫"]["履歴"][-1]["追加"][0]["内容"]["データ"]["運用結果"]["版"], "HDS原記録可逆保存-v1")
            self.assertEqual(正準(復元.保存()), 正準(原))

    def test_旧符号の復元再保存と次更新は再圧縮しない(self):
        元 = 同期(運用原記録("旧符号", 保存版="HDS運用原記録-v2"), self.元)
        原 = 元.保存()
        with patch("minidora.HDS運用.原記録.zlib.compress", side_effect=AssertionError("旧符号の再圧縮")):
            復元 = 運用原記録.復元(原, "旧符号")
            self.assertEqual(正準(復元.保存()), 正準(原))
            新 = 同期(復元, 能力結果(True, "次の小成果"))
        self.assertEqual(新.保存()["庫"]["履歴"][:-1], 原["庫"]["履歴"])

    def test_旧原記録へ新庫や新可逆版を混入しない(self):
        for 版 in ("HDS運用原記録-v1", "HDS運用原記録-v2"):
            値 = {**self.新.保存(), "版": 版}
            with self.subTest(版=版), self.assertRaisesRegex(ValueError, "旧原記録版"):
                運用原記録.復元(値, "有限新型")
        旧庫 = 長文脈庫("旧符号境界")
        行 = self.行
        旧庫.更新(旧庫.起点(), (文脈登録("A", 能力結果を復元(行["内容"]), "成果"),))
        旧 = 運用原記録("旧符号境界", 保存版="HDS運用原記録-v2").保存()
        旧["庫"] = json.loads(旧庫.保存文字列())
        with self.assertRaisesRegex(ValueError, "旧原記録版"):
            運用原記録.復元(旧, "旧符号境界")

    def test_各可逆版の符号上限を復号前に拒否する(self):
        元 = self.行["内容"]["データ"]["運用結果"]
        for 版, 上限 in (("HDS原記録可逆保存-v1", 1_000_000), ("HDS原記録可逆保存-v2", 2_000_000)):
            値 = {**元, "版": 版, "符号列": "A" * 上限}
            self.assertEqual(_符号の元長(値), 元["原バイト数"])
            行 = deepcopy(self.行)
            行["内容"]["データ"]["運用結果"] = {**値, "符号列": "A" * (上限 + 1)}
            with self.subTest(版=版), patch("minidora.HDS運用.原記録.zlib.decompressobj") as 復号:
                with self.assertRaises(ValueError):
                    原記録成果を復元(行)
                復号.assert_not_called()

    def test_writerはreaderの旧符号上限を超す値を返さない(self):
        文字 = base64.b64encode(random.Random(421).randbytes(900_000)).decode("ascii")
        元 = 能力結果(True, "高密度な保存検査", データ={"文字": 文字, "反復": "x" * 300_000})
        原 = 結果を保存(元)
        新符号 = _結果を符号化(元)
        self.assertGreater(len(新符号["符号列"]), 1_000_000)
        self.assertLessEqual(len(新符号["符号列"]), 2_000_000)
        self.assertEqual(_符号の元長(新符号), len(正準(原)))
        self.assertEqual(_結果を符号化(元, 保存版="HDS原記録可逆保存-v1"), 原)
        新 = 同期(運用原記録("高密度新型"), 元)
        self.assertEqual(原記録成果を復元(成果行(新)), 原)
        self.assertLessEqual(len(正準(成果行(新))), 2_000_000)
        旧 = 運用原記録("高密度旧型", 保存版="HDS運用原記録-v2")
        前 = 旧.保存()
        with self.assertRaisesRegex(ValueError, "単一記録サイズ上限"):
            同期(旧, 元)
        self.assertEqual(旧.保存(), 前)

    def test_新可逆版も原復号十六百万を超えない(self):
        元 = 交換長を持つ成果(16_000_000)
        符号 = _結果を符号化(元)
        self.assertEqual(_符号の元長(符号), 16_000_000)
        with self.assertRaisesRegex(ValueError, "復号サイズ上限"):
            _結果を符号化(交換長を持つ成果(16_000_001))
        行 = deepcopy(self.行)
        行["内容"]["データ"]["運用結果"]["原バイト数"] = 16_000_001
        with patch("minidora.HDS運用.原記録.zlib.decompressobj") as 復号:
            with self.assertRaises(ValueError):
                原記録成果を復元(行)
            復号.assert_not_called()

    def test_新可逆版の印と終端及び非有限JSONを拒否する(self):
        原 = self.行["内容"]["データ"]["運用結果"]
        圧縮 = base64.b64decode(原["符号列"])
        変更群 = [dict(原, 原SHA256="0" * 64), dict(原, 符号列="%%%%"), dict(原, 不明欄=1)]
        for 列 in (圧縮[:-1], 圧縮 + b"junk", 圧縮 + zlib.compress(b"another")):
            変更群.append(dict(原, 符号列=base64.b64encode(列).decode("ascii")))
        本文 = b'{"x":NaN,"padding":"' + b'x' * 550_000 + b'"}'
        変更群.append(dict(原, 原バイト数=len(本文), 原SHA256=sha256(本文).hexdigest(),
                         符号列=base64.b64encode(zlib.compress(本文)).decode("ascii")))
        for 値 in 変更群:
            行 = deepcopy(self.行)
            行["内容"]["データ"]["運用結果"] = 値
            with self.subTest(原印=値["原SHA256"]), self.assertRaises(ValueError):
                原記録成果を復元(行)

    def test_新総原十六百万は失効歴と大きな設定も含め拒否(self):
        元 = 能力結果(True, "合計保存検査", データ={"原文": "x" * 8_100_000})
        庫 = 運用原記録("合計新型")
        庫.庫 = 長文脈庫(庫.ID, 最大保存バイト数=32_000_000, 最大単一記録バイト数=2_000_000)
        初回 = 同期(庫, 元)
        前 = 初回.保存()
        成果ID = 成果行(初回)["識別子"]
        with self.assertRaisesRegex(ValueError, "復号後保存サイズ上限"):
            同期(初回, 元, 失効成果ID=(成果ID,))
        self.assertEqual(正準(初回.保存()), 正準(前))
        旧 = 運用原記録("旧合計", 保存版="HDS運用原記録-v2")
        旧.庫 = 長文脈庫(旧.ID, 最大保存バイト数=32_000_000)
        self.assertEqual(運用原記録.復元(旧.保存(), 旧.ID).保存(), 旧.保存())

    def test_本文参照根拠組位置と不透明frameは全値同じ(self):
        原 = 原記録成果を復元(self.行)
        self.assertEqual(正準(原), 正準(結果を保存(self.元)))
        結果 = 結果を復元(原)
        self.assertEqual((結果.本文, 結果.参照, 結果.根拠, 結果.データ),
                         (self.元.本文, self.元.参照, self.元.根拠, self.元.データ))
        self.assertIsInstance(結果.データ["区間"], tuple)
        self.assertFalse(self.行["内容"]["データ"]["事実認定"])

    def test_新型も資料更新による失効と過去全文を保つ(self):
        元 = 同期(運用原記録("新失効"), self.元, 全資料範囲=True)
        行 = 成果行(元)
        資料 = {"種類": "資料", "本文": "一般の原資料", "データ": {}, "結果": 結果を保存(能力結果(True, "一般の原資料"))}
        資料["版"] = 指紋({鍵: 資料[鍵] for 鍵 in ("種類", "本文", "データ")})
        新 = 元.同期候補({"資料": {}, "原文": "資料更新"}, {"行為": "登録", "名前": "A", "資料": 資料}, None, {})
        過去 = 新.庫.原記録(行["識別子"])
        self.assertFalse(過去["現行"])
        self.assertEqual(原記録成果を復元(過去), 結果を保存(self.元))
        self.assertEqual(新.保存()["庫"]["履歴"][0], 元.保存()["庫"]["履歴"][0])

    def test_明示初期化も旧保存を新版へ移行しない(self):
        for 版, 次版, 庫版 in (("HDS運用原記録-v1", "HDS運用原記録-v2", "MINIDORA-長文脈-v0.1"),
                              ("HDS運用原記録-v2", "HDS運用原記録-v2", "MINIDORA-長文脈-v0.1"),
                              ("HDS運用原記録-v3", "HDS運用原記録-v3", "MINIDORA-長文脈-v0.2")):
            庫 = 運用原記録("明示初期化", 保存版=版)
            新 = 庫.同期候補({"資料": {}, "原文": "明示初期化"}, {"行為": "初期化"}, None, {})
            self.assertEqual((新.保存()["版"], 新.保存()["庫"]["版"]), (次版, 庫版))
            self.assertEqual(新.保存()["庫"]["履歴"], [])


if __name__ == "__main__":
    unittest.main()

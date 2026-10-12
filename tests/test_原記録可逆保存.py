"""可逆交換・原子的同期・保存所有の開発契約。実製品の初見受入ではない。"""
import base64
from copy import deepcopy
from hashlib import sha256
import json
import random
import unittest
from unittest.mock import patch
import zlib

from minidora.HDS運用.原記録 import 運用原記録, 原記録成果を復元
from minidora.HDS運用.値 import 結果を保存, 結果を復元, 封緘, 開封
from minidora.能力結果復元 import 能力結果を復元
from minidora.長文脈管理 import 長文脈庫, 文脈登録, 文脈選択要求
from minidora.製品版.型 import 能力結果, 参照資料


def 正準バイト(値):
    return json.dumps(値, ensure_ascii=False, sort_keys=True, separators=(",", ":"), allow_nan=False).encode("utf-8")


def 大きな成果():
    原文 = "開発用の元資料。" * 18_000
    return 能力結果(True, "開発用成果。", 根拠=("原資料の区間",),
                   参照=(参照資料("開発元資料", "原材料", "開発対照", 本文=原文),),
                   データ={"原文": 原文, "証明": (原文, {"区間": (0, len(原文))})})


def 同期(庫, 成果):
    return 庫.同期候補({"資料": {}, "原文": "開発用の元依頼"}, None, 成果, {})


def 成果行(庫):
    return 庫.保存()["庫"]["履歴"][-1]["追加"][0]


def 符号を変更(記録, 本文):
    結果 = deepcopy(記録)
    値 = 結果["内容"]["データ"]["運用結果"]
    値.update(原バイト数=len(本文), 原SHA256=sha256(本文).hexdigest(),
             符号列=base64.b64encode(zlib.compress(本文, level=9)).decode("ascii"))
    return 結果


def 履歴を再構成(原保存, 変更):
    """履歴ハッシュを作り直しても、内部契約の違反を見逃さない対照。"""
    保存 = deepcopy(原保存)
    庫 = 長文脈庫(保存["庫"]["セッションID"], 最大記録数=保存["庫"]["上限"][0],
                 最大保存バイト数=保存["庫"]["上限"][1])
    for 事象 in 保存["庫"]["履歴"]:
        追加 = []
        for 元 in 事象["追加"]:
            行 = deepcopy(元)
            変更(行)
            追加.append(文脈登録(行["識別子"], 能力結果を復元(行["内容"]), 行["種別"],
                                  tuple(行["依存"]), 行["固定"]))
        庫.更新(庫.起点(), tuple(追加), 失効ID=tuple(事象["失効ID"]), 理由=事象["理由"])
    保存["庫"] = json.loads(庫.保存文字列())
    return 保存


class 可逆保存試験(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.元 = 大きな成果()
        cls.同期済 = 同期(運用原記録("可逆開発"), cls.元)
        cls.行 = 成果行(cls.同期済)

    def test_単一行の上限内で全文と組位置と根拠を往復(self):
        self.assertGreater(len(正準バイト(結果を保存(self.元))), 1_000_000)
        self.assertLess(len(正準バイト(self.行)), 1_000_000)
        原 = 原記録成果を復元(self.行)
        self.assertEqual(原, 結果を保存(self.元))
        復元 = 結果を復元(原)
        self.assertEqual(復元.データ, self.元.データ)
        self.assertEqual(復元.参照, self.元.参照)
        self.assertEqual(復元.根拠, self.元.根拠)
        self.assertIsInstance(復元.データ["証明"], tuple)
        self.assertIsInstance(復元.データ["証明"][1]["区間"], tuple)
        self.assertFalse(self.行["内容"]["データ"]["事実認定"])

    def test_五十万バイトまでの成果は従来交換値のまま(self):
        土台 = 能力結果(True, "小さい成果", データ={"本文": ""})
        空の長さ = len(正準バイト(結果を保存(土台)))
        for 長さ, 圧縮 in ((500_000, False), (500_001, True)):
            値 = 能力結果(True, "小さい成果", データ={"本文": "x" * (長さ - 空の長さ)})
            self.assertEqual(len(正準バイト(結果を保存(値))), 長さ)
            行 = 成果行(同期(運用原記録("境界"), 値))
            self.assertEqual("符号化" in 行["内容"]["データ"]["運用結果"], 圧縮)
            self.assertEqual(原記録成果を復元(行), 結果を保存(値))

    def test_縮まない成果を符号の付加量で記録上限へ到達させない(self):
        原文 = base64.b64encode(random.Random(31).randbytes(400_000)).decode("ascii")
        成果 = 能力結果(True, "元成果", データ={"原文": 原文})
        元 = 結果を保存(成果)
        self.assertGreater(len(正準バイト(元)), 500_000)
        行 = 成果行(同期(運用原記録("不圧縮開発"), 成果))
        self.assertEqual(行["内容"]["データ"]["運用結果"], 元)
        self.assertEqual(原記録成果を復元(行), 元)

    def test_旧v1は無更新の保存と履歴を変えず実同期からv2(self):
        原 = 同期(運用原記録("旧開発", 保存版="HDS運用原記録-v2"), 能力結果(True, "旧成果")).保存()
        原["版"] = "HDS運用原記録-v1"
        復元 = 運用原記録.復元(deepcopy(原), "旧開発")
        self.assertEqual(正準バイト(復元.保存()), 正準バイト(原))
        新 = 同期(復元, self.元).保存()
        self.assertEqual(新["版"], "HDS運用原記録-v2")
        self.assertEqual(新["庫"]["履歴"][:-1], 原["庫"]["履歴"])
        self.assertEqual(復元.保存(), 原)
        混入 = 同期(運用原記録("可逆開発", 保存版="HDS運用原記録-v2"), self.元).保存()
        混入["版"] = "HDS運用原記録-v1"
        with self.assertRaisesRegex(ValueError, "旧原記録版"):
            運用原記録.復元(混入, "可逆開発")

    def test_符号の版型長さ印と未知欄を拒否(self):
        for 欄, 値 in (("版", "未知"), ("符号化", "未知"), ("原バイト数", True),
                       ("原バイト数", 16_000_001), ("原SHA256", "0" * 64),
                       ("符号列", "%%%%"), ("未知欄", 1)):
            変更 = deepcopy(self.行)
            変更["内容"]["データ"]["運用結果"][欄] = 値
            with self.subTest(欄=欄), self.assertRaises(ValueError):
                原記録成果を復元(変更)

    def test_短い宣言長で大きな復号を作らず上限宣言も先に拒否(self):
        変更 = deepcopy(self.行)
        変更["内容"]["データ"]["運用結果"]["原バイト数"] = 500_001
        with self.assertRaises(ValueError):
            原記録成果を復元(変更)
        変更["内容"]["データ"]["運用結果"]["原バイト数"] = 16_000_001
        with patch("minidora.HDS運用.原記録.zlib.decompressobj") as 復号:
            with self.assertRaises(ValueError):
                原記録成果を復元(変更)
            復号.assert_not_called()

    def test_圧縮列の切断と余剰及び二つ目の圧縮列を拒否(self):
        符号 = self.行["内容"]["データ"]["運用結果"]
        元列 = base64.b64decode(符号["符号列"])
        for 列 in (元列[:-1], 元列 + b"extra", 元列 + zlib.compress(b"another")):
            変更 = deepcopy(self.行)
            変更["内容"]["データ"]["運用結果"]["符号列"] = base64.b64encode(列).decode("ascii")
            with self.subTest(末尾=len(列)), self.assertRaises(ValueError):
                原記録成果を復元(変更)

    def test_印を合わせても非正準JSONと不成立交換値は拒否(self):
        元 = 結果を保存(self.元)
        非正準 = json.dumps(元, ensure_ascii=False, sort_keys=True, indent=1).encode("utf-8")
        不成立 = deepcopy(元)
        不成立["採否"] = "保留"
        for 本文 in (非正準, 正準バイト(不成立)):
            with self.subTest(長さ=len(本文)), self.assertRaises(ValueError):
                原記録成果を復元(符号を変更(self.行, 本文))

    def test_履歴を再封緘しても過去符号成果と外側本体の改変は拒否(self):
        原 = 同期(self.同期済, 能力結果(True, "次の小さい成果")).保存()
        def 改変(行):
            if 行["内容"]["データ"].get("運用結果", {}).get("符号化"):
                行["内容"]["データ"]["運用結果"]["原SHA256"] = "0" * 64
        with self.assertRaises(ValueError):
            運用原記録.復元(履歴を再構成(原, 改変), "可逆開発")
        for 欄, 値 in (("本文", "別の成果"), ("参照", [])):
            def 改変(行):
                if 行["内容"]["データ"].get("運用結果", {}).get("符号化"):
                    行["内容"][欄] = 値
            with self.subTest(欄=欄), self.assertRaises(ValueError):
                運用原記録.復元(履歴を再構成(原, 改変), "可逆開発")

    def test_元保存容量を超える多数成果は圧縮しても原子的に拒否(self):
        庫 = 運用原記録("容量開発")
        庫.庫 = 長文脈庫(庫.ID, 最大保存バイト数=900_000)
        成果 = 能力結果(True, "成果", データ={"原文": "x" * 600_000})
        初回 = 同期(庫, 成果)
        前 = 初回.保存()
        with self.assertRaisesRegex(ValueError, "復号後保存サイズ上限"):
            同期(初回, 成果)
        self.assertEqual(初回.保存(), 前)
        原 = deepcopy(前)
        行 = 成果行(初回)
        原庫 = 長文脈庫.復元(json.dumps(原["庫"], ensure_ascii=False))
        原庫.更新(原庫.起点(), (文脈登録("別成果", 能力結果を復元(行["内容"]), "成果"),))
        原["庫"] = json.loads(原庫.保存文字列()); 原["連番"] += 1
        with self.assertRaisesRegex(ValueError, "復号後保存サイズ上限"):
            運用原記録.復元(原, 庫.ID)

    def test_圧縮成果も全資料変更で失効し過去全文は残る(self):
        元 = 運用原記録("失効開発")
        依頼 = {"資料": {}, "原文": "全資料の開発要求"}
        初回 = 元.同期候補(依頼, None, self.元, {}, 全資料範囲=True)
        成果ID = 成果行(初回)["識別子"]
        from minidora.HDS運用.値 import 指紋
        資料結果 = 能力結果(True, "原資料")
        資料 = {"種類": "資料", "本文": "原資料", "データ": {}, "結果": 結果を保存(資料結果)}
        資料["版"] = 指紋({鍵: 資料[鍵] for 鍵 in ("種類", "本文", "データ")})
        更新 = {"行為": "登録", "名前": "A", "資料": 資料}
        新 = 初回.同期候補(依頼, 更新, None, {})
        行 = 新.庫.原記録(成果ID)
        self.assertFalse(行["現行"])
        self.assertEqual(原記録成果を復元(行), 結果を保存(self.元))
        self.assertFalse(新.庫.選択(文脈選択要求((成果ID,), (), 0)).成立)
        with self.assertRaisesRegex(ValueError, "所有セッション"):
            運用原記録.復元(新.保存(), "別所有")


class セッション可逆成果試験(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        # 意味部品で生成した原交換値を持つ人工保存対照。HDS新規採用を宣言しない。
        from minidora.HDS運用.セッション import HDS運用セッション
        from minidora.HDS運用.意味資料 import 資料意味を選ぶ
        from minidora.HDS運用.内容構成 import _文章, 資料文章を照合
        本文 = "試料甲とは熱の移動を抑える容器である。\n" * 1_200
        要求 = {"版": "HDS一般会話要求-v2", "対象": [], "主題": ["試料甲"], "操作": ["説明"],
                "形式": "文章", "範囲": "自動", "最大文字数": 24000, "問い": "試料甲とは何ですか",
                "比較対象": [], "観点": [], "詳細": "標準", "提示本文": 本文,
                "関係焦点": ["定義"], "肯否": "未指定"}
        構造 = 資料意味を選ぶ({"提示本文": 能力結果(True, 本文)}, 要求)
        回答 = 資料文章を照合(構造, _文章(構造))
        会話 = HDS運用セッション("可逆状態開発", 手順形成=False)
        会話._前回目的 = {"方式": "一般資料", "要求": 要求}
        会話._前回結果 = 結果を保存(回答)
        会話._焦点有効 = True
        会話._原記録 = 会話._原記録.同期候補({"資料": {}, "原文": 要求["問い"]}, None, 回答, {})
        会話.目録.原記録庫 = 会話._原記録.庫
        cls.保存 = 会話.保存()
        cls.型 = HDS運用セッション
        cls.成果 = 回答

    def test_可逆成果を同セッションの保存復元で照合する(self):
        状態 = 開封(json.loads(self.保存))
        行 = 状態["原記録"]["庫"]["履歴"][-1]["追加"][0]
        self.assertIn("符号化", 行["内容"]["データ"]["運用結果"])
        復元 = self.型.復元(self.保存)
        self.assertTrue(復元.状態()["前回有効"])
        self.assertEqual(復元._前回結果, 結果を保存(self.成果))
        self.assertEqual(json.loads(復元.保存()), json.loads(self.保存))

    def test_採用成果だけ別セッションに移すと可逆保存でも拒否(self):
        元 = 開封(json.loads(self.保存))
        別 = 開封(json.loads(self.型("別状態開発", 手順形成=False).保存()))
        for 欄 in ("前回目的", "前回結果", "前回依存", "焦点有効"):
            別[欄] = deepcopy(元[欄])
        with self.assertRaisesRegex(ValueError, "同セッションの採用原記録"):
            self.型.復元(json.dumps(封緘(別), ensure_ascii=False))


if __name__ == "__main__":
    unittest.main()

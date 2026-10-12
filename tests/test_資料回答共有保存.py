"""保存表だけを変える有限対照。実製品・外部取得の成功は判定しない。"""
from copy import deepcopy
from hashlib import sha256
import json
import unittest
from unittest.mock import patch

from minidora.HDS運用.資料回答共有保存 import (
    資料回答共有保存版, 資料回答第2共有保存版, 資料回答旧共有保存版, 資料回答意味を保存, 資料回答意味を読む,
)
from minidora.HDS運用.内容構成 import (
    _文章, _資料文章を照合, 資料文章を照合, 資料文章を検査,
)
from minidora.HDS運用.資料回答 import 資料回答版
from minidora.HDS運用.意味資料 import 資料意味を選ぶ
from minidora.HDS運用.会話回答束 import _保持を照合
from minidora.HDS運用.値 import 結果を保存, 結果を復元
from minidora.製品版.型 import 能力結果


def _正準(値):
    return json.dumps(値, ensure_ascii=False, sort_keys=True,
                      separators=(",", ":"), allow_nan=False).encode("utf-8")


def _v2保存(意味, *, 意味版, 保存版=資料回答第2共有保存版):
    """旧表の試験は新defaultと区別してv2を明示する。"""
    return 資料回答意味を保存(意味, 意味版=意味版, 保存版=保存版)


def _意味():
    所有 = {"資料ID": "資料一", "保存指紋": "a" * 64, "本文指紋": "b" * 64,
            "本文長": 19074, "全記載指紋": "c" * 64,
            "全記載ID": ["資料一:原文記載:" + str(番号) for 番号 in range(1200)]}
    行群, 座標群 = [], []
    for 番号 in range(40):
        座標 = {"座標ID": "座標:" + str(番号), "内容": {"原文": "未読解条件も残す。", "型": None},
                "原文範囲": [番号, 番号 + 1], "値状態": "確定"}
        行群.append({"ID": "記載:" + str(番号), "資料作用": {"原資料": deepcopy(所有), "座標": [deepcopy(座標)]}})
        座標群.append(座標)
    return {"版": 資料回答版, "記載関係": 行群,
            "資料作用成果": {"原資料": [deepcopy(所有)], "座標": 座標群,
                             "適用": {"条件一": {"原資料": deepcopy(所有), "候補": ["記載:1"]}}},
            "意味": {"命題": [], "留保": ["未知条件"]}, "使用記載": ["記載:0"],
            "未使用記載": ["記載:" + str(番号) for 番号 in range(1, 40)],
            "未確定限定": [{"記載ID": "記載:1", "理由": "作用域未確定"}],
            "演算": [{"数量": {"数": 3, "単位": "項目"}, "条件": None, "否定": False}],
            "型対照": [True, 1, 1.0, -0.0, None, ""]}


class 資料回答共有保存試験(unittest.TestCase):
    def setUp(self):
        self.意味 = _意味()
        self.保存 = _v2保存(self.意味, 意味版=資料回答版)
        self.assertEqual(self.保存["版"], 資料回答第2共有保存版)

    def 読む(self, 保存):
        return 資料回答意味を読む(保存, 意味版=資料回答版)

    def test_全文正準型順序残差と未使用を完全復元して量を減らす(self):
        原 = _正準(self.意味)
        self.assertGreater(len(原), 500_000)
        self.assertLess(len(_正準(self.保存)), len(原) // 3)
        self.assertEqual(self.保存["原正準SHA256"], sha256(原).hexdigest())
        self.assertEqual(self.保存["原正準バイト数"], len(原))
        展開 = self.読む(self.保存)
        self.assertEqual(_正準(展開), 原)
        self.assertEqual(_v2保存(展開, 意味版=資料回答版), self.保存)
        for 番号, 旧値 in enumerate(self.意味["型対照"]):
            self.assertIs(type(展開["型対照"][番号]), type(旧値))

    def test_呼出前後と別箇所へ可変参照を共有しない(self):
        原, 保存原 = _正準(self.意味), _正準(self.保存)
        展開 = self.読む(self.保存)
        展開["記載関係"][0]["資料作用"]["原資料"]["全記載ID"].clear()
        self.assertEqual(_正準(self.意味), 原)
        self.assertEqual(_正準(self.保存), 保存原)
        self.assertEqual(len(展開["記載関係"][1]["資料作用"]["原資料"]["全記載ID"]), 1200)
        self.assertEqual(_正準(self.読む(self.保存)), 原)

    def test_小さいplainとsingletonは原版原JSONのまま(self):
        小 = deepcopy(self.意味)
        小["記載関係"] = []
        小["資料作用成果"] = {"原資料": [], "座標": [], "適用": {}}
        for 元 in (小, {"版": 資料回答版, "任意原文": "原" * 200000}):
            保存 = _v2保存(元, 意味版=資料回答版)
            self.assertEqual(_正準(保存), _正準(元))
            self.assertEqual(_正準(self.読む(保存)), _正準(元))

    def test_同ID異義は所有も座標も共有禁止(self):
        for 種類 in ("所有", "座標"):
            元 = deepcopy(self.意味)
            if 種類 == "所有":
                元["資料作用成果"]["原資料"][0]["本文長"] += 1
            else:
                元["資料作用成果"]["座標"][0]["値状態"] = "未確定"
            with self.subTest(種類=種類), self.assertRaisesRegex(ValueError, "同ID異義"):
                _v2保存(元, 意味版=資料回答版)

    def test_意味版の失効をplainと共有で先に拒否(self):
        for 元 in (deepcopy(self.意味), deepcopy(self.保存)):
            if 元["版"] == 資料回答第2共有保存版:
                元["意味版"] = "旧意味"
            else:
                元["版"] = "旧意味"
            with self.subTest(版=元["版"]), self.assertRaises(ValueError):
                self.読む(元)

    def test_保存欄印長型pool重複とunusedを拒否(self):
        def 欄追加(元): 元["新権限"] = True
        def 印改変(元): 元["原正準SHA256"] = "0" * 64
        def 長改変(元): 元["原正準バイト数"] += 1
        def 型改変(元): 元["原正準バイト数"] = True
        def 値改変(元): 元["共有値"][0]["値"]["不正"] = "追記"
        def pool重複(元): 元["共有値"].append(deepcopy(元["共有値"][0]))
        def unused(元):
            名 = 元["共有値"][0]["共有ID"]
            元["参照置換"] = [行 for 行 in 元["参照置換"] if 行["共有ID"] != 名]
        for 修理 in (欄追加, 印改変, 長改変, 型改変, 値改変, pool重複, unused):
            元 = deepcopy(self.保存)
            修理(元)
            with self.subTest(反例=修理.__name__), self.assertRaises(ValueError):
                self.読む(元)

    def test_参照の型欠落重複閉じたパスplaceholderを拒否(self):
        def 重複(元): 元["参照置換"].append(deepcopy(元["参照置換"][0]))
        def 欠落(元): 元["参照置換"][0]["共有ID"] = "存在しない"
        def 外部(元): 元["参照置換"][0]["パス"] = ["意味", "命題"]
        def bool位置(元): 元["参照置換"][0]["パス"][1] = True
        def 非null(元):
            親 = 元["本体"]
            道 = 元["参照置換"][0]["パス"]
            for 鍵 in 道[:-1]: 親 = 親[鍵]
            親[道[-1]] = {}
        for 修理 in (重複, 欠落, 外部, bool位置, 非null):
            元 = deepcopy(self.保存)
            修理(元)
            with self.subTest(反例=修理.__name__), self.assertRaises(ValueError):
                self.読む(元)

    def test_poolと参照順序を再封緘しても拒否(self):
        for 欄 in ("共有値", "参照置換"):
            元 = deepcopy(self.保存)
            元[欄].reverse()
            with self.subTest(欄=欄), self.assertRaisesRegex(ValueError, "非正準"):
                self.読む(元)

    def test_非有限外国型循環を拒否(self):
        循環 = []
        循環.append(循環)
        for 値 in (float("nan"), float("inf"), b"raw", 循環, {1: "整数鍵"}):
            元 = {"版": 資料回答版, "原文": 値}
            with self.subTest(型=type(値).__name__), self.assertRaises(ValueError):
                _v2保存(元, 意味版=資料回答版)

    def test_悪性参照の展開爆発を複製前に拒否(self):
        元 = deepcopy(self.保存)
        所有 = next(行 for 行 in 元["共有値"] if 行["種別"] == "所有")
        # リテラル表は小さいが、同じ所有を2000回展開するとv2の32MBを超える。
        元["本体"]["資料作用成果"]["原資料"] = [None] * 2000
        元["参照置換"] = [行 for 行 in 元["参照置換"] if 行["パス"][:2] != ["資料作用成果", "原資料"]]
        元["参照置換"] += [{"パス": ["資料作用成果", "原資料", 番], "共有ID": 所有["共有ID"]} for 番 in range(2000)]
        with patch("minidora.HDS運用.資料回答共有保存._箇所へ置く", side_effect=AssertionError("展開してはいけない")):
            with self.assertRaisesRegex(ValueError, "展開バイト上限"):
                self.読む(元)

    def test_保存全体深さは既存32以内_追加階層で狭めない(self):
        元 = deepcopy(self.意味)
        深部 = "端"
        for _ in range(28): 深部 = [深部]
        元["深部"] = 深部  # 元の意味が深さ29ならwrapper化せずplain。
        保存 = _v2保存(元, 意味版=資料回答版)
        self.assertEqual(_正準(保存), _正準(元))
        元["深部"] = [深部]
        self.assertEqual(_正準(_v2保存(元, 意味版=資料回答版)), _正準(元))
        self.assertEqual(_正準(self.読む(元)), _正準(元))
        for _ in range(3): 元["深部"] = [元["深部"]]
        with self.assertRaisesRegex(ValueError, "入れ子|深さ"):
            _v2保存(元, 意味版=資料回答版)

    def test_表の深さ内でも参照先の展開深さ超過を複製前に拒否(self):
        元 = deepcopy(self.保存)
        所有 = next(行 for 行 in 元["共有値"] if 行["種別"] == "所有")
        旧ID = 所有["共有ID"]
        深部 = "端"
        for _ in range(25): 深部 = [深部]
        所有["値"]["深部"] = 深部
        所有["共有ID"] = "所有:" + sha256("所有".encode("utf-8") + b"\x00" + _正準(所有["値"])).hexdigest()
        for 行 in 元["参照置換"]:
            if 行["共有ID"] == 旧ID: 行["共有ID"] = 所有["共有ID"]
        with patch("minidora.HDS運用.資料回答共有保存._箇所へ置く", side_effect=AssertionError("展開してはいけない")):
            with self.assertRaisesRegex(ValueError, "展開深さ"):
                self.読む(元)

    def test_共有範囲外のplainだけは既存境界と組位置を保つ(self):
        元 = {"版": 資料回答版, "原文": "原" * 5_400_000, "組": (1, [2])}
        self.assertEqual(_v2保存(元, 意味版=資料回答版), 元)
        self.assertIs(type(_v2保存(元, 意味版=資料回答版)["組"]), tuple)
        self.assertEqual(self.読む(元), 元)
        self.assertIs(type(self.読む(元)["組"]), tuple)
        # 境界到達後の不正値をtypedな境界外fallbackで隠さない。
        元["末尾"] = float("nan")
        with self.assertRaises(ValueError):
            _v2保存(元, 意味版=資料回答版)

    def test_旧v1を同じ版で読み原保存byteを再封緘しない(self):
        旧 = _v2保存(self.意味, 意味版=資料回答版, 保存版=資料回答旧共有保存版)
        原 = _正準(旧)
        self.assertEqual(旧["版"], 資料回答旧共有保存版)
        展開 = self.読む(旧)
        self.assertEqual(_正準(展開), _正準(self.意味))
        self.assertEqual(_正準(旧), 原)
        self.assertEqual(_正準(_v2保存(展開, 意味版=資料回答版, 保存版=資料回答旧共有保存版)), 原)
        self.assertEqual(_v2保存(展開, 意味版=資料回答版)["版"], 資料回答第2共有保存版)

    def test_v2は16MB超の重複意味を共有し旧v1境界を変更しない(self):
        元 = deepcopy(self.意味)
        行 = 元["記載関係"][0]
        元["記載関係"] = [{"ID": "規模:" + str(番), "資料作用": 行["資料作用"]} for 番 in range(603)]
        原 = _正準(元)
        self.assertGreater(len(原), 16_000_000)
        self.assertLess(len(原), 32_000_000)
        旧 = _v2保存(元, 意味版=資料回答版, 保存版=資料回答旧共有保存版)
        self.assertEqual(_正準(旧), 原)
        新 = _v2保存(元, 意味版=資料回答版)
        self.assertEqual(新["版"], 資料回答第2共有保存版)
        self.assertLess(len(_正準(新)), 2_000_000)
        self.assertEqual(_正準(self.読む(新)), 原)
        旧版偽装 = deepcopy(新)
        旧版偽装["版"] = 資料回答旧共有保存版
        with patch("minidora.HDS運用.資料回答共有保存._箇所へ置く", side_effect=AssertionError("展開してはいけない")):
            with self.assertRaises(ValueError):
                self.読む(旧版偽装)

    def test_版別の宣言上限とpoolへの相互参照は展開前拒否(self):
        for 版, 上限 in ((資料回答旧共有保存版, 16_000_000), (資料回答第2共有保存版, 32_000_000)):
            元 = _v2保存(self.意味, 意味版=資料回答版, 保存版=版)
            元["原正準バイト数"] = 上限 + 1
            with self.subTest(版=版), patch("minidora.HDS運用.資料回答共有保存._箇所へ置く", side_effect=AssertionError("展開してはいけない")):
                with self.assertRaises(ValueError): self.読む(元)
        元 = deepcopy(self.保存)
        元["参照置換"][0]["パス"] = ["共有値", 1, "値"]
        with patch("minidora.HDS運用.資料回答共有保存._箇所へ置く", side_effect=AssertionError("展開してはいけない")):
            with self.assertRaisesRegex(ValueError, "参照パス"):
                self.読む(元)

    def test_未対応保存版は無言で現版へ更新しない(self):
        for 版 in ("HDS資料回答共有保存-v4", True, [資料回答第2共有保存版]):
            with self.subTest(版=版), self.assertRaises(ValueError):
                _v2保存(self.意味, 意味版=資料回答版, 保存版=版)
        元 = deepcopy(self.保存)
        元["版"] = "HDS資料回答共有保存-v4"
        with self.assertRaisesRegex(ValueError, "失効"):
            self.読む(元)


class 資料回答共有接続試験(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        本文 = "測定器丙は表示装置である。" + "\n".join(
            "装置" + str(番) + "は付属装置である。" for 番 in range(45))
        要求 = {"版": "HDS一般会話要求-v2", "対象": [], "主題": ["測定器丙"],
                "操作": ["要約"], "形式": "文章", "範囲": "自動", "最大文字数": 24000,
                "問い": "測定器丙の説明", "比較対象": [], "観点": [], "詳細": "標準",
                "提示本文": 本文, "関係焦点": [], "肯否": "未指定"}
        cls.構造 = 資料意味を選ぶ({"有限素材" + "資料名" * 40: 能力結果(True, 本文)}, 要求)
        cls.文章 = _文章(cls.構造)
        cls.旧 = _資料文章を照合(cls.構造, cls.文章, 形式=None, 共有保存=False)
        cls.意味 = deepcopy(cls.旧.データ["意味成果"])

    def test_plainの検査は原保存を再封緘しない(self):
        原 = _正準(結果を保存(self.旧))
        self.assertTrue(資料文章を検査(self.旧))
        self.assertEqual(_正準(結果を保存(self.旧)), 原)

    def test_共有各版の資料文章は同版で再生成し原保存を保持(self):
        for 版 in (資料回答旧共有保存版, 資料回答第2共有保存版, 資料回答共有保存版):
            with self.subTest(版=版):
                成果 = _資料文章を照合(self.構造, self.文章, 形式=None, 共有保存=版)
                self.assertEqual(成果.データ["意味成果"]["版"], 版)
                原 = _正準(結果を保存(成果))
                self.assertTrue(資料文章を検査(成果))
                self.assertEqual(_正準(結果を保存(成果)), 原)

    def test_共有接続は採否tuple原資料文章と意味をすべて保持(self):
        with patch("minidora.HDS運用.資料回答.回答意味を構成", return_value=deepcopy(self.意味)):
            旧 = _資料文章を照合(self.構造, self.文章, 形式=None, 共有保存=False)
            新 = 資料文章を照合(self.構造, self.文章)
            self.assertEqual(新.データ["意味成果"]["版"], 資料回答共有保存版)
            self.assertTrue(資料文章を検査(旧))
            self.assertTrue(資料文章を検査(新))
            原旧 = 結果を保存(旧)
            原新 = 結果を保存(新)
            self.assertEqual(原新["採否"], 原旧["採否"])
            self.assertEqual(原新["組位置"], 原旧["組位置"])
            展開 = deepcopy(原新)
            展開["内容"]["データ"]["意味成果"] = 資料回答意味を読む(新.データ["意味成果"], 意味版=資料回答版)
            self.assertEqual(_正準(展開), _正準(原旧))
            self.assertEqual(結果を保存(結果を復元(原新)), 原新)
            self.assertEqual(_保持を照合({"保持": []}, 新), _保持を照合({"保持": []}, 旧))

    def test_正準共有表を改変再封緘しても原資料からの再生成が拒否(self):
        with patch("minidora.HDS運用.資料回答.回答意味を構成", return_value=deepcopy(self.意味)):
            新 = 資料文章を照合(self.構造, self.文章)
            改変意味 = 資料回答意味を読む(新.データ["意味成果"], 意味版=資料回答版)
            改変意味["未使用記載"].append("根拠にない記載")
            新.データ["意味成果"] = 資料回答意味を保存(改変意味, 意味版=資料回答版)
            原 = _正準(結果を保存(新))
            self.assertFalse(資料文章を検査(新))
            self.assertEqual(_正準(結果を保存(新)), 原)


if __name__ == "__main__":
    unittest.main()

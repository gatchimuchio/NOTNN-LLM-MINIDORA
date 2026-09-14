from __future__ import annotations

from dataclasses import dataclass
from types import SimpleNamespace
import unittest

from minidora.候補生成 import 仮説候補を生成, 自動仮説要求
from minidora.有限仮説探索 import 仮説を検討
from minidora.意味定義 import 単項計算定義を読む, 定義適用要求を読む, 定義を実行
from minidora.模型閉包 import 模型終端を判定, 模型閉包状態
from minidora.計算実行器 import 計算実行器


@dataclass(frozen=True)
class _寄与:
    関係名: str
    差: int
    根拠: tuple[str, ...] = ()


@dataclass(frozen=True)
class _差:
    候補ID: str
    寄与: tuple[_寄与, ...]


class _結果:
    def __init__(self, diffs, winner=None, refs=True):
        self.候補差 = tuple(diffs)
        self.参照最有力候補ID = winner
        self.文脈 = SimpleNamespace(参照状態=(object(),) if refs else ())

    def 参照候補辞書(self):
        prefixes = ("参照関係寄与", "候補共同参照", "候補共同再照合")
        return {
            row.候補ID: sum(item.差 for item in row.寄与 if item.関係名.startswith(prefixes))
            for row in self.候補差
        }


class Core閉包試験(unittest.TestCase):
    def test_一意な正の参照差はCore自身で成立(self):
        result = _結果(
            (
                _差("A", (_寄与("参照関係寄与", 2, ("支持",)),)),
                _差("B", (_寄与("参照関係寄与", 0),)),
            ),
            winner="A",
        )
        closed = 模型終端を判定(result)
        self.assertTrue(closed.成立)
        self.assertEqual(closed.回答候補ID, "A")

    def test_正の参照差が同率なら競合(self):
        result = _結果(
            (
                _差("A", (_寄与("参照関係寄与", 1),)),
                _差("B", (_寄与("参照関係寄与", 1),)),
            )
        )
        self.assertEqual(模型終端を判定(result).状態, 模型閉包状態.競合)

    def test_参照なしは参照不足(self):
        result = _結果((_差("A", ()), _差("B", ())), refs=False)
        self.assertEqual(模型終端を判定(result).状態, 模型閉包状態.参照不足)

    def test_入力境界未成立を候補差で上書きしない(self):
        result = _結果(
            (
                _差("A", (_寄与("入力境界未成立", 0, ("INCOMPLETE_INPUT_STATE",)),)),
                _差("B", ()),
            )
        )
        self.assertEqual(模型終端を判定(result).状態, 模型閉包状態.入力意味不足)

    def test_支持反証併存は矛盾残差(self):
        result = _結果(
            (
                _差("A", (_寄与("参照関係寄与", 0, ("参照矛盾:支持と反証が併存",)),)),
                _差("B", ()),
            )
        )
        self.assertEqual(模型終端を判定(result).状態, 模型閉包状態.矛盾)


class Core候補生成試験(unittest.TestCase):
    def test_規則祖先から不足前提を候補生成し既存探索へ接続(self):
        request = {
            "事実": [{"識別子": "f1", "命題": "A", "出典": "資料"}],
            "規則": [
                {"識別子": "r1", "前件": ["A", "B"], "後件": "C", "出典": "資料"},
                {"識別子": "r2", "前件": ["C"], "後件": "D", "出典": "資料"},
            ],
            "観測": ["D"],
        }
        generated = 仮説候補を生成(request)
        self.assertEqual(generated.候補, ("B",))
        auto_request, _ = 自動仮説要求(request)
        report = 仮説を検討(auto_request)
        self.assertEqual(report["状態"], "説明候補あり")
        self.assertEqual(report["候補"][0]["仮説"], ["B"])

    def test_観測そのものを自己説明仮説にしない(self):
        generated = 仮説候補を生成({"事実": [], "規則": [], "観測": ["X"]})
        self.assertEqual(generated.候補, ())
        self.assertTrue(any(item.種別 == "自己説明禁止" for item in generated.残差))

    def test_規則循環を無限探索せず残差化(self):
        request = {
            "事実": [],
            "規則": [
                {"前件": ["B"], "後件": "A"},
                {"前件": ["A"], "後件": "B"},
            ],
            "観測": ["A"],
        }
        generated = 仮説候補を生成(request)
        self.assertTrue(any(item.種別 == "規則循環" for item in generated.残差))


class Core意味定義試験(unittest.TestCase):
    def test_新語定義を既存計算IRへ降下して即時適用(self):
        definition = 単項計算定義を読む("「うぽ」は二倍して1を足すという意味。")
        name, value = 定義適用要求を読む("7をうぽした結果は？")
        self.assertEqual((name, value), ("うぽ", 7))
        result = 定義を実行(definition, value, 計算実行器())
        self.assertEqual(result.出力, 15)
        self.assertEqual(tuple(item.作用.value for item in result.履歴), ("乗算", "加算"))

    def test_定義名に依存しない(self):
        definition = 単項計算定義を読む("「ふが」は3倍して4を引くという意味")
        self.assertEqual(定義を実行(definition, 5, 計算実行器()).出力, 11)

    def test_部分解釈した定義を成立させない(self):
        with self.assertRaisesRegex(ValueError, "未解釈残差"):
            単項計算定義を読む("「x」は二倍して魔法を使って1を足すという意味")


if __name__ == "__main__":
    unittest.main()

"""人工通信で同じ候補列の有限継続を検査する。知識性能には数えない。"""
from copy import deepcopy
from dataclasses import replace
import json
import unittest

from minidora.知識取得 import 知識取得器, 知識取得要求, _記録印
from minidora.知識取得継続 import 継続束を読む, 継続進展を検査, 継続不成立を検査
from minidora.取得実行制御 import 共有取得制御, 公開取得上限
from minidora.公開本文取得 import 本文を復号
from minidora.製品版.型 import 参照資料
from minidora.文脈命題接続 import 取得本文を資料化
from minidora.能力合成 import _結果辞書
from minidora.応答構成 import 能力結果を復元
from minidora.HDS運用.一般接続 import 取得資料を復元


基点 = "https://example.com/"


class 人工検索:
    def __init__(self, 件数=2):
        self.回数 = []
        self.件数 = 件数

    def 制御を束縛(self, 制御):
        return self

    def 検索(self, 語, limit=5):
        self.回数.append(語)
        return tuple(参照資料(str(i), "試料甲", "人工候補", 基点 + str(i),
                         本文="試料甲とは誤ったスニペット999。") for i in range(self.件数))[:limit]


class 人工本文:
    def __init__(self, 本文群=None):
        self.本文群 = 本文群 or ["試料甲の方式は断熱収納。", "試料甲とは熱の移動を抑える容器である。"]
        self.回数 = []

    def 制御を束縛(self, 制御):
        return self

    def 取得(self, URL):
        self.回数.append(URL)
        return 本文を復号(URL, (URL,), {"content-type": "text/plain; charset=utf-8"},
                     self.本文群[int(URL.rsplit("/", 1)[-1])].encode())


def 準備(本文群=None, 上限=None):
    本文 = 人工本文(本文群)
    検索 = 人工検索(len(本文.本文群))
    制御 = 共有取得制御(上限 or 公開取得上限(最大検索回数=1))
    取得 = 知識取得器(検索, 本文).制御を束縛(制御)
    要求 = 知識取得要求("試料甲", ("試料甲",), 最大候補数=6, 最大取得数=6, 最大資料数=3)
    前 = 取得.実行(要求, 外部読取許可=True)
    return 検索, 本文, 制御, 取得, 要求, 前


class 継続試験(unittest.TestCase):
    def test_JSON交換後のHTMLが継続と両資料経路へ渡る(self):
        _, _, _, 取得, 要求, 前 = 準備()
        交換 = 能力結果を復元(json.loads(json.dumps(_結果辞書(前), ensure_ascii=False)))
        self.assertEqual(交換.データ["資料"][0]["抽出頁範囲"], [])
        元記録 = deepcopy(交換.データ)
        self.assertEqual(継続束を読む(交換), 前.データ["継続束"])
        self.assertEqual(取得本文を資料化(交換)[0][0].本文, 前.参照[0].本文)
        self.assertEqual(next(iter(取得資料を復元(交換).values())).本文, 前.参照[0].本文)
        次 = 取得.継続(要求, 交換, 外部読取許可=True)
        self.assertTrue(次.成立, 次.保留理由)
        self.assertTrue(継続進展を検査(交換, 次, 要求))
        self.assertEqual(交換.データ, 元記録)

    def test_旧HTMLの頁欄省略を元記録変更なしに読める(self):
        _, _, _, _, _, 前 = 準備()
        d = json.loads(json.dumps(前.データ, ensure_ascii=False))
        del d["資料"][0]["抽出頁範囲"]
        d["記録SHA256"] = _記録印({k: v for k, v in d.items() if k != "記録SHA256"})
        旧 = replace(前, データ=d)
        元記録 = deepcopy(d)
        継続束を読む(旧)
        取得本文を資料化(旧)
        取得資料を復元(旧)
        self.assertEqual(旧.データ, 元記録)
        self.assertNotIn("抽出頁範囲", 旧.データ["資料"][0])

    def test_JSON交換したPDFの頁対応を復元する(self):
        from minidora.公開PDF抽出 import PDF抽出版
        class 頁本文(人工本文):
            def 取得(self, URL):
                doc = super().取得(URL)
                return replace(doc, 内容種別="application/pdf", 文字コード=PDF抽出版,
                               抽出頁範囲=((1, 0, len(doc.本文)),))
        要求 = 知識取得要求("試料甲", ("試料甲",), 最大資料数=1)
        前 = 知識取得器(人工検索(1), 頁本文()).実行(要求, 外部読取許可=True)
        self.assertTrue(前.成立, 前.保留理由)
        交換 = 能力結果を復元(json.loads(json.dumps(_結果辞書(前), ensure_ascii=False)))
        self.assertEqual(交換.データ["資料"][0]["抽出頁範囲"], [[1, 0, len(前.参照[0].本文)]])
        継続束を読む(交換)
        self.assertEqual(取得本文を資料化(交換)[0][0].本文, 前.参照[0].本文)
        未解釈 = deepcopy(交換.データ)
        未解釈["資料"][0]["除外要素"] = ["PDF文字以外は未解釈"]
        未解釈["記録SHA256"] = _記録印({k: v for k, v in 未解釈.items() if k != "記録SHA256"})
        for 資料化 in (取得本文を資料化, 取得資料を復元):
            with self.subTest(資料化=資料化), self.assertRaisesRegex(ValueError, "取得意味欠落"):
                資料化(replace(交換, データ=未解釈))
        for 頁 in (None, "123", [[True, 0, len(前.参照[0].本文)]], [[1, 1, len(前.参照[0].本文)]], [[1, 0, 1]]):
            with self.subTest(頁=頁):
                d = deepcopy(交換.データ)
                d["資料"][0]["抽出頁範囲"] = 頁
                d["記録SHA256"] = _記録印({k: v for k, v in d.items() if k != "記録SHA256"})
                with self.assertRaises(ValueError):
                    継続束を読む(replace(交換, データ=d))
        d = deepcopy(交換.データ)
        del d["資料"][0]["抽出頁範囲"]
        d["記録SHA256"] = _記録印({k: v for k, v in d.items() if k != "記録SHA256"})
        with self.assertRaises(ValueError):
            継続束を読む(replace(交換, データ=d))

    def test_頁の復元で未解釈要素を採用可能にしない(self):
        _, _, _, _, _, 前 = 準備()
        d = json.loads(json.dumps(前.データ, ensure_ascii=False))
        d["資料"][0]["除外要素"] = ["PDF文字以外は未解釈"]
        d["記録SHA256"] = _記録印({k: v for k, v in d.items() if k != "記録SHA256"})
        with self.assertRaisesRegex(ValueError, "取得意味欠落"):
            取得本文を資料化(replace(前, データ=d))

    def test_同じ検索の次本文だけを追加し候補を再計上しない(self):
        検索, 本文, 制御, 取得, 要求, 前 = 準備()
        self.assertEqual(前.データ["継続束"]["消費位置"], 1)
        次 = 取得.継続(要求, 前, 外部読取許可=True)
        self.assertTrue(次.成立, 次.保留理由)
        self.assertTrue(継続進展を検査(前, 次, 要求))
        self.assertEqual(検索.回数, ["試料甲"])
        self.assertEqual(本文.回数, [基点 + "0", 基点 + "1"])
        self.assertEqual(制御.記録()["使用"]["検索回数"], 1)
        self.assertEqual(制御.記録()["使用"]["候補数"], 2)
        self.assertEqual(制御.記録()["使用"]["本文取得数"], 2)
        self.assertNotIn("999", 次.本文)
        self.assertEqual(次.参照[:1], 前.参照)
        self.assertEqual(次.データ["資料数"], 2)
        self.assertEqual(次.データ["継続束"]["親記録SHA256"], 前.データ["記録SHA256"])

    def test_候補を尽くしたら旧本文だけで成立しない(self):
        検索, 本文, _, 取得, 要求, 前 = 準備(["試料甲の方式は断熱収納。"])
        次 = 取得.継続(要求, 前, 外部読取許可=True)
        self.assertFalse(次.成立)
        self.assertIn("未消費候補", 次.保留理由)
        self.assertEqual(len(検索.回数), 1)
        self.assertEqual(len(本文.回数), 1)

    def test_累積取得数と同じ共有資源上限を維持する(self):
        _, 本文, 制御, 取得, 要求, 前 = 準備(上限=公開取得上限(最大検索回数=1, 最大本文取得数=1))
        次 = 取得.継続(要求, 前, 外部読取許可=True)
        self.assertFalse(次.成立)
        self.assertIn("本文取得数上限", 次.保留理由)
        self.assertEqual(len(本文.回数), 1)
        self.assertEqual(制御.記録()["使用"]["本文取得数"], 1)
        新制御 = 共有取得制御(制御.上限)
        for 名, 数 in 制御.記録()["使用"].items():
            if 数: 新制御.消費(名, 数)
        戻し = 取得.制御を束縛(新制御).継続(要求, 前, 外部読取許可=True)
        self.assertFalse(戻し.成立)
        self.assertEqual(len(本文.回数), 1)

    def test_元要求と上限変更を拒否する(self):
        _, 本文, _, 取得, 要求, 前 = 準備()
        for 変更 in (replace(要求, 検索語="別の主題"), replace(要求, 最大資料数=4)):
            with self.subTest(変更=変更):
                self.assertFalse(取得.継続(変更, 前, 外部読取許可=True).成立)
        self.assertEqual(len(本文.回数), 1)

    def test_同じ使用数で余力がある新制御でも期限を新造させない(self):
        _, 本文, 制御, 取得, 要求, 前 = 準備(上限=公開取得上限(最大検索回数=1, 最大本文取得数=2))
        新制御 = 共有取得制御(制御.上限)
        for 名, 数 in 制御.記録()["使用"].items():
            if 数: 新制御.消費(名, 数)
        self.assertEqual(制御.記録()["使用"], 新制御.記録()["使用"])
        self.assertEqual(新制御.残量("本文取得数"), 1)
        次 = 取得.制御を束縛(新制御).継続(要求, 前, 外部読取許可=True)
        self.assertFalse(次.成立)
        self.assertEqual(len(本文.回数), 1)

    def test_候補位置と本文と抜粋の改変を拒否する(self):
        _, _, _, _, 要求, 前 = 準備()
        for 変更 in ("位置", "候補", "抜粋", "本文"):
            with self.subTest(変更=変更):
                d = deepcopy(前.データ)
                r = 前
                if 変更 == "位置": d["継続束"]["消費位置"] = 0
                elif 変更 == "候補": d["継続束"]["候補"][1]["URL"] = "http://localhost/a"
                elif 変更 == "抜粋": d["抜粋"][0]["本文"] = "改変"
                else: r = replace(前, 参照=(replace(前.参照[0], 本文="改変"),))
                d["記録SHA256"] = _記録印({k: v for k, v in d.items() if k != "記録SHA256"})
                with self.assertRaises((ValueError, KeyError)):
                    継続束を読む(replace(r, データ=d), 要求)

    def test_同じ本文やURLで進展を水増ししない(self):
        検索, 本文, _, 取得, 要求, 前 = 準備(["試料甲の方式は断熱収納。"] * 2)
        次 = 取得.継続(要求, 前, 外部読取許可=True)
        self.assertFalse(次.成立)
        self.assertEqual(次.データ["資料数"], 1)
        self.assertEqual(len(検索.回数), 1)
        self.assertEqual(len(本文.回数), 2)
        with self.assertRaises(ValueError):
            継続進展を検査(前, 前, 要求)

    def test_不成立の候補原順序と実重複だけを認める(self):
        _, _, _, 取得, 要求, 前 = 準備(["試料甲の方式は断熱収納。"] * 3)
        次 = 取得.継続(要求, 前, 外部読取許可=True)
        self.assertTrue(継続不成立を検査(前, 次, 要求))
        for 改変 in ("逆順", "未取得を重複扱い"):
            with self.subTest(改変=改変):
                d = deepcopy(次.データ)
                始 = len(前.データ["試行"])
                if 改変 == "逆順":
                    d["試行"][始:] = list(reversed(d["試行"][始:]))
                    d["継続束"]["試行済みURL"][1:] = list(reversed(d["継続束"]["試行済みURL"][1:]))
                else:
                    d["試行"][始]["作用"] = "重複URL"
                    d["継続束"]["試行済みURL"].remove(d["試行"][始]["URL"])
                    d["本文取得数"] -= 1
                d["記録SHA256"] = _記録印({k: v for k, v in d.items() if k != "記録SHA256"})
                with self.assertRaisesRegex(ValueError, "原候補順序・実重複"):
                    継続不成立を検査(前, replace(次, データ=d), 要求)

    def test_実重複だけの消費は本文取得ゼロで不成立を保持する(self):
        class 重複検索(人工検索):
            def 検索(self, 語, limit=5):
                return super().検索(語, limit=1) * 3
        本文 = 人工本文(["試料甲の方式は断熱収納。"])
        取得 = 知識取得器(重複検索(), 本文)
        要求 = 知識取得要求("試料甲", ("試料甲",), 最大資料数=3)
        前 = 取得.実行(要求, 外部読取許可=True)
        次 = 取得.継続(要求, 前, 外部読取許可=True)
        self.assertFalse(次.成立)
        self.assertEqual(次.本文, "")
        self.assertEqual((前.データ["本文取得数"], 次.データ["本文取得数"]), (1, 1))
        self.assertEqual(len(本文.回数), 1)
        self.assertTrue(継続不成立を検査(前, 次, 要求))
        with self.assertRaises(ValueError):
            継続束を読む(次, 要求)

    def test_停止判定の故障自由文を保存せず通信せず保留する(self):
        _, 本文, _, 取得, 要求, 前 = 準備()
        def 故障():
            raise RuntimeError("故障メッセージを外へ出さない")
        次 = 取得.継続(要求, 前, 外部読取許可=True, 停止要求=故障)
        self.assertFalse(次.成立)
        self.assertEqual(len(本文.回数), 1)
        self.assertNotIn("故障メッセージ", 次.保留理由)
        self.assertEqual(次.データ, {})

    def test_停止を本文取得後にも確認して採用しない(self):
        _, 本文, _, 取得, 要求, 前 = 準備()
        次 = 取得.継続(要求, 前, 外部読取許可=True, 停止要求=lambda: len(本文.回数) > 1)
        self.assertFalse(次.成立)
        self.assertEqual(次.保留理由, "停止要求")
        self.assertEqual(次.データ["資料数"], 1)

    def test_既存の命題取得も版付き追加欄を検証して読める(self):
        _, _, _, _, _, 前 = 準備()
        群, 名前 = 取得本文を資料化(前)
        self.assertEqual(群[0].本文, 前.参照[0].本文)
        self.assertEqual(名前, [前.参照[0].識別子])
        with self.assertRaises(ValueError):
            取得本文を資料化(replace(前, データ={**前.データ, "未知欄": 1}))


if __name__ == "__main__":
    unittest.main()

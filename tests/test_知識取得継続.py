"""人工通信で同じ候補列の有限継続を検査する。知識性能には数えない。"""
from copy import deepcopy
from dataclasses import replace
import unittest

from minidora.知識取得 import 知識取得器, 知識取得要求, _記録印
from minidora.知識取得継続 import 継続束を読む, 継続進展を検査
from minidora.取得実行制御 import 共有取得制御, 公開取得上限
from minidora.公開本文取得 import 本文を復号
from minidora.製品版.型 import 参照資料
from minidora.文脈命題接続 import 取得本文を資料化


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

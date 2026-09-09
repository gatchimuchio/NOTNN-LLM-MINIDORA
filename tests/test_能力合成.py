"""合成器の契約試験。試験用能力は制御境界の検査用で、Core代替ではない。"""
from copy import deepcopy
from dataclasses import replace
from datetime import datetime, timezone
import math
import unittest

from minidora.能力合成 import (
    能力合成器, 登録能力, 合成工程, 合成計画, 素材参照,
)
from minidora.製品版.能力契約 import 能力文脈
from minidora.製品版.型 import 能力結果, 参照資料


class 試験能力:
    版 = "契約試験-v1"
    優先度 = 0

    def __init__(self, 名前="複写", 処理=None, 判定値=1.0):
        self.名前 = 名前
        self.処理 = 処理 or (lambda c: 能力結果(True, c.直前応答))
        self.判定値 = 判定値
        self.呼出 = []
        self.判定呼出 = []

    def 判定(self, c):
        self.判定呼出.append(deepcopy(c))
        return self.判定値(c) if callable(self.判定値) else self.判定値

    def 実行(self, c):
        self.呼出.append(deepcopy(c))
        return self.処理(c)


def 工程(ID="結果", 候補=("複写",), 入力=(素材参照("入力", "素材"),), **kwargs):
    return 合成工程(ID, 候補, "指示", 入力, **kwargs)


def 初期():
    return {"指示": 能力結果(True, "明示指示"),
            "素材": 能力結果(True, "入力本文", データ={"値": [1, 2]})}


class 能力合成契約試験(unittest.TestCase):
    def setUp(self):
        self.m = 試験能力()
        self.runner = 能力合成器((登録能力(self.m),))
        self.p = 合成計画((工程(),), ("結果",))
        self.d = 初期()

    def 検査(self, 結果, 状態):
        self.assertEqual(結果.状態, 状態, 結果.理由)
        self.assertEqual(結果.成立, 状態 == "合格")
        self.assertTrue(結果.監査整合())
        if 状態 != "合格":
            self.assertEqual(結果.出力, ())

    def test_単工程(self):
        r = self.runner.実行(self.p, self.d)
        self.検査(r, "合格")
        self.assertEqual(r.出力[0][1].本文, "入力本文")
        self.assertEqual((r.試行数, r.実行数), (1, 1))

    def test_逆順宣言も依存順に実行(self):
        p = 合成計画((工程("後", 入力=(素材参照("工程", "前"),)), 工程("前")), ("後",))
        r = self.runner.実行(p, self.d)
        self.検査(r, "合格")
        self.assertEqual([x.工程 for x in r.履歴], ["前", "後"])

    def test_分岐合流と素材由来分離(self):
        self.d["別素材"] = 能力結果(True, "別の本文")
        p = 合成計画((工程("a"), 工程("b", 入力=(素材参照("入力", "別素材"),)),
                      工程("c", 入力=(素材参照("工程", "a"), 素材参照("工程", "b")))), ("c",))
        r = self.runner.実行(p, self.d)
        self.検査(r, "合格")
        self.assertEqual(r.出力[0][1].本文, "入力本文\n\n別の本文")
        self.assertEqual([x["参照"]["識別子"] for x in self.m.呼出[-1].補助["合成入力"]], ["a", "b"])

    def test_複数出力の指定順保持(self):
        p = 合成計画((工程("a"), 工程("b")), ("b", "a"))
        r = self.runner.実行(p, self.d)
        self.検査(r, "合格")
        self.assertEqual([k for k, _ in r.出力], ["b", "a"])

    def test_未知能力は全工程実行前に保留(self):
        p = 合成計画((工程("a"), 工程("b", ("未実装",), (素材参照("工程", "a"),))), ("b",))
        r = self.runner.実行(p, self.d)
        self.検査(r, "保留")
        self.assertEqual(self.m.呼出, [])
        self.assertEqual(self.m.判定呼出, [])

    def test_未使用代替候補も未登録なら保留(self):
        p = 合成計画((工程(候補=("複写", "未登録")),), ("結果",))
        self.検査(self.runner.実行(p, self.d), "保留")
        self.assertEqual(self.m.呼出, [])

    def test_入力参照欠落(self):
        del self.d["素材"]
        self.検査(self.runner.実行(self.p, self.d), "保留")
        self.assertEqual(self.m.呼出, [])

    def test_指示Data欠落(self):
        del self.d["指示"]
        self.検査(self.runner.実行(self.p, self.d), "保留")

    def test_設定Data欠落(self):
        p = 合成計画((工程(設定参照="未提供設定"),), ("結果",))
        self.検査(self.runner.実行(p, self.d), "保留")

    def test_入力Data未成立(self):
        for k in ("素材", "指示"):
            with self.subTest(k=k):
                d = 初期()
                d[k] = 能力結果(False, "値らしい文字列", 保留理由="未確定")
                self.検査(self.runner.実行(self.p, d), "保留")
        self.assertEqual(self.m.呼出, [])

    def test_工程参照欠落(self):
        p = 合成計画((工程(入力=(素材参照("工程", "なし"),)),), ("結果",))
        self.検査(self.runner.実行(p, self.d), "失敗")

    def test_自己参照循環(self):
        p = 合成計画((工程(入力=(素材参照("工程", "結果"),)),), ("結果",))
        self.検査(self.runner.実行(p, self.d), "失敗")
        self.assertEqual(self.m.判定呼出, [])

    def test_多工程循環(self):
        p = 合成計画((工程("a", 入力=(素材参照("工程", "b"),)),
                      工程("b", 入力=(素材参照("工程", "a"),))), ("a",))
        r = self.runner.実行(p, self.d)
        self.検査(r, "失敗")
        self.assertIn("依存循環", r.理由)
        self.assertEqual(self.m.呼出, [])

    def test_孤立工程を黙って実行しない(self):
        p = 合成計画((工程("採用"), 工程("孤立")), ("採用",))
        self.検査(self.runner.実行(p, self.d), "失敗")
        self.assertEqual(self.m.呼出, [])

    def test_工程重複(self):
        p = 合成計画((工程(), 工程()), ("結果",))
        self.検査(self.runner.実行(p, self.d), "失敗")

    def test_不正計画集合(self):
        bad = [None, {}, 合成計画((), ()), 合成計画((工程(),), ()),
               合成計画((工程(),), ("なし",)), 合成計画((工程(),), ("結果", "結果")),
               合成計画([工程()], ("結果",)), 合成計画((工程(候補=()),), ("結果",)),
               合成計画((工程(候補=("複写", "複写")),), ("結果",)),
               合成計画((工程(入力=(素材参照("未知領域", "素材"),)),), ("結果",)),
               合成計画((工程(入力=[素材参照("入力", "素材")]),), ("結果",))]
        for p in bad:
            with self.subTest(p=p):
                self.検査(self.runner.実行(p, self.d), "失敗")
        self.assertEqual(self.m.呼出, [])

    def test_不正Data集合(self):
        bad = [None, {"素材": "str"}, {1: 能力結果(True, "text")},
               {"素材": 能力結果(1, "text")}, {"素材": 能力結果(True, 3)},
               {"素材": 能力結果(True, "text", 根拠=["list"])},
               {"素材": 能力結果(True, "text", データ={1: "key"})},
               {"素材": 能力結果(True, "text", データ={"n": math.nan})},
               {"素材": 能力結果(True, "text", データ={"n": math.inf})},
               {"素材": 能力結果(True, "text", データ={"obj": object()})}]
        for d in bad:
            with self.subTest(d=d):
                self.検査(self.runner.実行(self.p, d), "失敗")
        self.assertEqual(self.m.呼出, [])

    def test_循環Dataは失敗として返す(self):
        d = {}
        d["cycle"] = d
        self.d["素材"] = 能力結果(True, "x", データ=d)
        self.検査(self.runner.実行(self.p, self.d), "失敗")

    def test_不正文脈集合(self):
        for c in ["bad", 能力文脈("", ""), 能力文脈("", "s", 履歴=(("user",),)),
                  能力文脈("", "s", 補助=[]), 能力文脈("", "s", 補助={"x": math.nan})]:
            with self.subTest(c=c):
                self.検査(self.runner.実行(self.p, self.d, 文脈=c), "失敗")

    def test_非該当時は実行せず明示代替(self):
        a = 試験能力("第一", 判定値=0)
        runner = 能力合成器((登録能力(a), 登録能力(self.m)))
        p = 合成計画((工程(候補=("第一", "複写")),), ("結果",))
        r = runner.実行(p, self.d)
        self.検査(r, "合格")
        self.assertEqual((r.試行数, r.実行数), (2, 1))
        self.assertEqual(a.呼出, [])

    def test_不成立時の明示代替(self):
        a = 試験能力("第一", lambda c: 能力結果(False, "仮値", 保留理由="不成立"))
        runner = 能力合成器((登録能力(a), 登録能力(self.m)))
        p = 合成計画((工程(候補=("第一", "複写")),), ("結果",))
        r = runner.実行(p, self.d)
        self.検査(r, "合格")
        self.assertEqual((r.試行数, r.実行数), (2, 2))
        self.assertEqual([x.状態 for x in r.履歴], ["保留", "合格"])

    def test_登録だけでは暗黙代替しない(self):
        a = 試験能力("第一", lambda c: 能力結果(False, "仮値"))
        runner = 能力合成器((登録能力(a), 登録能力(self.m)))
        p = 合成計画((工程(候補=("第一",)),), ("結果",))
        self.検査(runner.実行(p, self.d), "保留")
        self.assertEqual(self.m.呼出, [])

    def test_例外時の明示代替と記録(self):
        def fail(c):
            raise RuntimeError("例外内の機密文字列")
        a = 試験能力("例外", fail)
        runner = 能力合成器((登録能力(a), 登録能力(self.m)))
        p = 合成計画((工程(候補=("例外", "複写")),), ("結果",))
        r = runner.実行(p, self.d)
        self.検査(r, "合格")
        self.assertEqual(r.履歴[0].状態, "失敗")
        self.assertNotIn("機密文字列", r.履歴[0].理由)

    def test_不正判定値は実行しない(self):
        for score in (True, -1, 2, math.nan, math.inf, "1", None):
            with self.subTest(score=score):
                m = 試験能力(判定値=score)
                r = 能力合成器((登録能力(m),)).実行(self.p, self.d)
                self.検査(r, "失敗")
                self.assertEqual(m.呼出, [])

    def test_不正能力結果を昇格しない(self):
        for result in (None, "answer", 能力結果(1, "文字"),
                       能力結果(True, "文字", データ={"v": math.nan})):
            with self.subTest(result=result):
                m = 試験能力(処理=lambda c, v=result: v)
                self.検査(能力合成器((登録能力(m),)).実行(self.p, self.d), "失敗")

    def test_部分成功を最終成功にしない(self):
        bad = 試験能力("保留", lambda c: 能力結果(False, "未採用"))
        runner = 能力合成器((登録能力(self.m), 登録能力(bad)))
        p = 合成計画((工程("a"), 工程("b", ("保留",), (素材参照("工程", "a"),))), ("a", "b"))
        r = runner.実行(p, self.d)
        self.検査(r, "保留")
        self.assertEqual([k for k, _ in r.中間結果], ["a"])

    def test_外部読取は既定で禁止(self):
        # 実ネットワークではなく、許可境界のみを検査する試験用能力。
        runner = 能力合成器((登録能力(self.m, 外部読取=True),))
        self.検査(runner.実行(self.p, self.d), "保留")
        self.assertEqual(self.m.判定呼出, [])
        self.検査(runner.実行(self.p, self.d, 外部読取許可=True), "合格")

    def test_外部読取許可の文字列を真として扱わない(self):
        self.検査(self.runner.実行(self.p, self.d, 外部読取許可="false"), "失敗")
        self.assertEqual(self.m.呼出, [])

    def test_工程数上限(self):
        runner = 能力合成器((登録能力(self.m),), 最大工程数=1)
        p = 合成計画((工程("a"), 工程("b")), ("a", "b"))
        self.検査(runner.実行(p, self.d), "失敗")
        self.assertEqual(self.m.呼出, [])

    def test_試行上限で部分出力を隔離(self):
        runner = 能力合成器((登録能力(self.m),), 最大試行数=1)
        p = 合成計画((工程("a"), 工程("b", 入力=(素材参照("工程", "a"),))), ("b",))
        r = runner.実行(p, self.d)
        self.検査(r, "保留")
        self.assertEqual(r.理由, "能力試行数上限")
        self.assertEqual(r.実行数, 1)

    def test_入力サイズ上限は呼出前(self):
        runner = 能力合成器((登録能力(self.m),), 資料バイト上限=800)
        self.d["素材"] = 能力結果(True, "大" * 1000)
        self.検査(runner.実行(self.p, self.d), "失敗")
        self.assertEqual(self.m.呼出, [])

    def test_出力サイズ上限(self):
        m = 試験能力(処理=lambda c: 能力結果(True, "a" * 30_000))
        runner = 能力合成器((登録能力(m),), 資料バイト上限=10_000)
        self.検査(runner.実行(self.p, self.d), "失敗")

    def test_開始前中止(self):
        r = self.runner.実行(self.p, self.d, 停止要求=lambda: True)
        self.検査(r, "中止")
        self.assertEqual(self.m.呼出, [])

    def test_実行途中の中止は戻り値を採用しない(self):
        stop = [False]
        def run(c):
            stop[0] = True
            return 能力結果(True, "未採用結果")
        m = 試験能力(処理=run)
        r = 能力合成器((登録能力(m),)).実行(self.p, self.d, 停止要求=lambda: stop[0])
        self.検査(r, "中止")
        self.assertEqual(r.中間結果, ())
        self.assertEqual(r.実行数, 1)

    def test_判定途中の中止は実行しない(self):
        stop = [False]
        def judge(c):
            stop[0] = True
            return 1
        m = 試験能力(判定値=judge)
        r = 能力合成器((登録能力(m),)).実行(self.p, self.d, 停止要求=lambda: stop[0])
        self.検査(r, "中止")
        self.assertEqual(m.呼出, [])

    def test_停止判定故障から代替実行へ進まない(self):
        calls = [0]
        def stop():
            calls[0] += 1
            if calls[0] >= 3:
                raise RuntimeError("停止判定器故障")
            return False
        second = 試験能力("代替")
        runner = 能力合成器((登録能力(self.m), 登録能力(second)))
        p = 合成計画((工程(候補=("複写", "代替")),), ("結果",))
        self.検査(runner.実行(p, self.d, 停止要求=stop), "失敗")
        self.assertEqual(self.m.呼出, [])
        self.assertEqual(second.呼出, [])

    def test_停止要求の不正型(self):
        self.検査(self.runner.実行(self.p, self.d, 停止要求=lambda: "false"), "失敗")
        self.assertEqual(self.m.呼出, [])

    def test_文脈やDataを呼出先が変更しても原本不変(self):
        def mutate(c):
            c.補助["利用者設定"]["v"].append(9)
            c.補助["合成入力"][0]["結果"]["データ"]["値"].append(99)
            return 能力結果(True, c.直前応答)
        m = 試験能力(処理=mutate)
        base = 能力文脈("原指示", "s", "旧応答", 履歴=(("user", "旧入力"),), 補助={"利用者設定": {"v": [1]}})
        before = deepcopy((self.d, base))
        r = 能力合成器((登録能力(m),)).実行(self.p, self.d, 文脈=base)
        self.検査(r, "合格")
        self.assertEqual((self.d, base), before)

    def test_判定の変異を実行へ渡さない(self):
        def judge(c):
            c.補助["合成設定"]["v"] = "汚染"
            return 1
        m = 試験能力(判定値=judge, 処理=lambda c: 能力結果(True, str(c.補助["合成設定"])))
        r = 能力合成器((登録能力(m),)).実行(self.p, self.d)
        self.検査(r, "合格")
        self.assertEqual(r.出力[0][1].本文, "{}")

    def test_後段の変更で中間結果が書き換わらない(self):
        first = 試験能力("生成", lambda c: 能力結果(True, "a", データ={"配列": [7]}))
        def mutate(c):
            c.補助["合成入力"][0]["結果"]["データ"]["配列"].append(9)
            return 能力結果(True, "b")
        second = 試験能力("変更", mutate)
        p = 合成計画((工程("a", ("生成",)), 工程("b", ("変更",), (素材参照("工程", "a"),))), ("b",))
        r = 能力合成器((登録能力(first), 登録能力(second))).実行(p, self.d)
        self.検査(r, "合格")
        self.assertEqual(dict(r.中間結果)["a"].データ, {"配列": [7]})

    def test_能力が返したオブジェクトの事後変更から分離(self):
        value = 能力結果(True, "a", データ={"配列": [1]})
        m = 試験能力(処理=lambda c: value)
        r = 能力合成器((登録能力(m),)).実行(self.p, self.d)
        value.データ["配列"].append(2)
        self.assertEqual(r.出力[0][1].データ, {"配列": [1]})
        self.assertTrue(r.監査整合())

    def test_素材未指定で旧会話本文を暗黙使用しない(self):
        p = 合成計画((工程(入力=()),), ("結果",))
        base = 能力文脈("旧指示", "s", "秘密の旧本文")
        r = self.runner.実行(p, self.d, 文脈=base)
        self.検査(r, "合格")
        self.assertEqual(r.出力[0][1].本文, "")

    def test_セッション分離(self):
        m = 試験能力(処理=lambda c: 能力結果(True, c.セッションID))
        runner = 能力合成器((登録能力(m),))
        a = runner.実行(self.p, self.d, 文脈=能力文脈("", "a"))
        b = runner.実行(self.p, self.d, 文脈=能力文脈("", "b"))
        self.assertEqual((a.出力[0][1].本文, b.出力[0][1].本文), ("a", "b"))

    def test_参照来歴保持と重複排除(self):
        ref = 参照資料("原典", "題名", "供給元", 公開時刻=datetime(2026, 1, 1, tzinfo=timezone.utc))
        self.d["素材"] = 能力結果(True, "引用本文", 参照=(ref, ref))
        r = self.runner.実行(self.p, self.d)
        self.検査(r, "合格")
        self.assertEqual(r.出力[0][1].参照, (ref,))

    def test_同名参照の内容衝突を黙って上書きしない(self):
        self.d["素材"] = 能力結果(True, "原文", 参照=(参照資料("id", "題", "元", 本文="旧"),))
        m = 試験能力(処理=lambda c: 能力結果(True, "新値", 参照=(参照資料("id", "題", "元", 本文="新"),)))
        self.検査(能力合成器((登録能力(m),)).実行(self.p, self.d), "失敗")

    def test_異なる出典の異なる主張は両方保持(self):
        refs = (参照資料("a", "資料A", "出典A", 本文="値10"), 参照資料("b", "資料B", "出典B", 本文="値20"))
        self.d["素材"] = 能力結果(True, "二つの主張", 参照=refs)
        r = self.runner.実行(self.p, self.d)
        self.検査(r, "合格")
        self.assertEqual(r.出力[0][1].参照, refs)

    def test_同一入力計画の決定的記録(self):
        a = self.runner.実行(self.p, self.d)
        b = self.runner.実行(self.p, self.d)
        self.assertEqual(a, b)

    def test_入力摂動は記録と結果へ到達(self):
        a = self.runner.実行(self.p, self.d)
        self.d["素材"] = 能力結果(True, "別の入力")
        b = self.runner.実行(self.p, self.d)
        self.assertNotEqual(a.出力, b.出力)
        self.assertNotEqual(a.開始ハッシュ, b.開始ハッシュ)
        self.assertNotEqual(a.ルートハッシュ, b.ルートハッシュ)

    def test_記録改変検出(self):
        r = self.runner.実行(self.p, self.d)
        changed = replace(r, 履歴=(replace(r.履歴[0], 状態="失敗"),))
        self.assertFalse(changed.監査整合())
        self.assertFalse(replace(r, 状態="保留").監査整合())
        r.出力[0][1].データ["改変"] = True
        self.assertFalse(r.監査整合())

    def test_能力名版の変更を認識(self):
        self.m.版 = "変更後"
        self.検査(self.runner.実行(self.p, self.d), "失敗")
        self.assertEqual(self.m.呼出, [])

    def test_実行中版変更の結果は採用しない(self):
        def mutate(c):
            self.m.版 = "別版"
            return 能力結果(True, "値")
        self.m.処理 = mutate
        self.検査(self.runner.実行(self.p, self.d), "失敗")

    def test_登録や上限の不正は構築時に拒否(self):
        with self.assertRaises(ValueError):
            能力合成器((登録能力(self.m), 登録能力(self.m)))
        for value in (0, -1, True, 1.5):
            with self.subTest(value=value), self.assertRaises(ValueError):
                能力合成器((), 最大工程数=value)
        with self.assertRaises(ValueError):
            能力合成器((登録能力(self.m, 外部読取="false"),))


if __name__ == "__main__":
    unittest.main()

"""目的分解・後戻り・状態分離・予算の契約試験。試験能力をCore実証とは呼ばない。"""
from copy import deepcopy
from dataclasses import asdict, replace
from itertools import product
import json
import unittest

from minidora.多段解決 import (問題素材, 解決目的, 解法, 多段問題, 多段問題を復元,
                               多段解決器)
from minidora.多段解決接続 import 解決補助能力群
from minidora.能力合成 import 登録能力
from minidora.製品版.型 import 能力結果, 参照資料


class 試験能力:
    版 = "試験-v1"
    優先度 = 0
    def __init__(self, 名前="処理", 関数=None):
        self.名前 = 名前
        self.関数 = 関数 or (lambda c: 能力結果(True, c.直前応答))
        self.呼出 = []
    def 判定(self, c):
        return 1.0
    def 実行(self, c):
        self.呼出.append(deepcopy(c))
        return self.関数(c)


def 目的(name="g", check="成果検査", setting="非空"):
    return 解決目的(name, check, "指示", setting)


def 手順(name="m", goal="g", children=(), module="素材引継ぎ", inputs=None, priority=0):
    if inputs is None:
        inputs = tuple(問題素材("目的", key) for key in children) or (問題素材("入力", "素材"),)
    return 解法(name, goal, children, module, "指示", inputs, 優先度=priority)


def 入力():
    return {"素材": 能力結果(True, "原資料", データ={"配列": [1]}),
            "指示": 能力結果(True, "宣言された処理"),
            "非空": 能力結果(True, "", データ={"種別": "非空"})}


def 実行器(*modules):
    return 多段解決器((*解決補助能力群(), *(登録能力(m) for m in modules)), 純粋作用確認=True)


class 多段解決契約試験(unittest.TestCase):
    def setUp(self):
        self.p = 多段問題(("g",), (目的(),), (手順(),))
        self.d = 入力()
        self.engine = 実行器()

    def check(self, result, state):
        self.assertEqual(result.状態, state, result.理由)
        self.assertTrue(result.整合確認())
        if state != "合格":
            self.assertEqual((result.出力, result.中間結果, result.採用経路), ((), (), ()))

    def test_一つの目的を検証まで通す(self):
        r = self.engine.実行(self.p, self.d)
        self.check(r, "合格")
        self.assertEqual(r.出力[0][1].本文, "原資料")
        self.assertEqual((r.展開数, r.呼出数), (1, 2))

    def test_目的から下位目的を選んで戻す(self):
        p = 多段問題(("g",), (目的(), 目的("child")),
                     (手順("root", children=("child",)), 手順("leaf", "child")))
        r = self.engine.実行(p, self.d)
        self.check(r, "合格")
        self.assertEqual([s["目的"] for s in r.採用経路], ["child", "g"])

    def test_未参照目的や解法は実行しない(self):
        m = 試験能力()
        p = replace(self.p, 目的群=(目的(), 目的("other")),
                    解法群=(手順(), 手順("unused", "other", module=m.名前)))
        self.check(実行器(m).実行(p, self.d), "合格")
        self.assertEqual(m.呼出, [])

    def test_失敗能力は明示した次の解法へ(self):
        bad = 試験能力(関数=lambda c: 能力結果(False, "仮の値", 保留理由="未成立"))
        p = replace(self.p, 解法群=(手順("first", module=bad.名前), 手順("second", priority=1)))
        r = 実行器(bad).実行(p, self.d)
        self.check(r, "合格")
        self.assertEqual([s["解法"] for s in r.採用経路], ["second"])
        self.assertTrue(any(e["作用"] == "実行不成立" for e in r.履歴))

    def test_能力例外を成功にせず別解を記録(self):
        def fail(c):
            raise RuntimeError("機密本文")
        bad = 試験能力(関数=fail)
        p = replace(self.p, 解法群=(手順("first", module=bad.名前), 手順("second", priority=1)))
        r = 実行器(bad).実行(p, self.d)
        self.check(r, "合格")
        self.assertNotIn("機密本文", str(r))
        self.assertIn("RuntimeError", str(r.履歴))

    def test_空の成功を検証で退ける(self):
        empty = 試験能力(関数=lambda c: 能力結果(True, ""))
        p = replace(self.p, 解法群=(手順(module=empty.名前),))
        r = 実行器(empty).実行(p, self.d)
        self.check(r, "保留")
        self.assertTrue(any(e["作用"] == "目的条件未達" for e in r.履歴))

    def test_後続で失敗したら子の別解へ戻る(self):
        empty = 試験能力("空結果", lambda c: 能力結果(True, "" if c.直前応答 == "悪い" else c.直前応答))
        p = 多段問題(("g",), (目的(), 目的("child")),
            (手順("root", children=("child",), module=empty.名前),
             手順("a", "child", inputs=(問題素材("入力", "bad"),)),
             手順("b", "child", priority=1)))
        self.d["bad"] = 能力結果(True, "悪い")
        r = 実行器(empty).実行(p, self.d)
        self.check(r, "合格")
        self.assertEqual([s["解法"] for s in r.採用経路], ["b", "root"])
        self.assertEqual(len(empty.呼出), 2)
        self.assertTrue(any(e["作用"] == "後続から再開" for e in r.履歴))

    def test_親の別解へ戻る(self):
        p = 多段問題(("g",), (目的(), 目的("missing")),
                      (手順("a", children=("missing",)), 手順("b", priority=1)))
        r = self.engine.実行(p, self.d)
        self.check(r, "合格")
        self.assertEqual(r.採用経路[0]["解法"], "b")

    def test_共有下位目的は同じ枝で再利用(self):
        merge = 試験能力("結合")
        p = 多段問題(("g",), tuple(目的(n) for n in ("g", "a", "b", "shared")),
            (手順("root", children=("a", "b"), module=merge.名前),
             手順("a", "a", ("shared",)), 手順("b", "b", ("shared",)), 手順("shared", "shared")))
        r = 実行器(merge).実行(p, self.d)
        self.check(r, "合格")
        self.assertEqual([s["目的"] for s in r.採用経路].count("shared"), 1)
        self.assertTrue(any(e["作用"] == "成果再利用" for e in r.履歴))

    def test_失敗枝の成果は成功枝へ残らない(self):
        empty = 試験能力("空", lambda c: 能力結果(True, ""))
        p = 多段問題(("g",), (目的(), 目的("failed_child")),
            (手順("first", children=("failed_child",), module=empty.名前),
             手順("fc", "failed_child"), 手順("second", priority=1)))
        r = 実行器(empty).実行(p, self.d)
        self.check(r, "合格")
        self.assertNotIn("failed_child", dict(r.中間結果))
        self.assertTrue(any(e["目的"] == "failed_child" for e in r.履歴))

    def test_複数最終目的が揃わなければ部分成功を返さない(self):
        p = replace(self.p, 最終目的=("g", "missing"), 目的群=(目的(), 目的("missing")))
        self.check(self.engine.実行(p, self.d), "保留")

    def test_複数最終目的の出力順保持(self):
        p = 多段問題(("b", "a"), (目的("a"), 目的("b")), (手順("a", "a"), 手順("b", "b")))
        r = self.engine.実行(p, self.d)
        self.check(r, "合格")
        self.assertEqual([k for k, _ in r.出力], ["b", "a"])

    def test_後続最終目的から前の最終目的へ戻る(self):
        filter_ = 試験能力("選別", lambda c: 能力結果(bool(c.直前応答 == "原資料"), c.直前応答))
        self.d["bad"] = 能力結果(True, "悪い")
        p = 多段問題(("a", "b"), (目的("a"), 目的("b")),
            (手順("a0", "a", inputs=(問題素材("入力", "bad"),)), 手順("a1", "a", priority=1),
             手順("b", "b", ("a",), module=filter_.名前)))
        r = 実行器(filter_).実行(p, self.d)
        self.check(r, "合格")
        self.assertEqual([v.本文 for _, v in r.出力], ["原資料", "原資料"])
        self.assertNotIn("a0", [x["解法"] for x in r.採用経路])

    def test_循環する解法だけを除外し独立経路は使う(self):
        p = replace(self.p, 解法群=(手順("cycle", children=("g",)), 手順("safe", priority=1)))
        r = self.engine.実行(p, self.d)
        self.check(r, "合格")
        self.assertTrue(any(e["作用"] == "循環経路除外" for e in r.履歴))

    def test_循環のみなら未完了(self):
        p = replace(self.p, 解法群=(手順("cycle", children=("g",)),))
        self.check(self.engine.実行(p, self.d), "保留")

    def test_多段の循環(self):
        p = 多段問題(("g",), (目的(), 目的("a")),
            (手順("ga", children=("a",)), 手順("ag", "a", ("g",))))
        self.check(self.engine.実行(p, self.d), "保留")

    def test_登録済みでも宣言のない能力へ委譲しない(self):
        unused = 試験能力()
        p = replace(self.p, 解法群=())
        self.check(実行器(unused).実行(p, self.d), "保留")
        self.assertEqual(unused.呼出, [])

    def test_純粋作用確認と外部読取禁止(self):
        with self.assertRaises(ValueError):
            多段解決器(解決補助能力群())
        with self.assertRaises(ValueError):
            多段解決器((登録能力(試験能力(), 外部読取=True),), 純粋作用確認=True)
        with self.assertRaises(ValueError):
            多段解決器((), 純粋作用確認=1)

    def test_未登録能力や不正入力は全呼出前に拒否(self):
        m = 試験能力()
        engine = 実行器(m)
        for p in (replace(self.p, 目的群=(replace(目的(), 検証能力="missing"),)),
                  replace(self.p, 解法群=(手順(module="missing"),))):
            self.check(engine.実行(p, self.d), "失敗")
        self.assertEqual(m.呼出, [])

    def test_不正な構造を黙って修正しない(self):
        for p in (None, {}, replace(self.p, 最終目的=()), replace(self.p, 最終目的=("missing",)),
                  replace(self.p, 最終目的=("g", "g")), replace(self.p, 目的群=(目的(), 目的())),
                  replace(self.p, 解法群=(手順(), 手順())),
                  replace(self.p, 解法群=(手順(children=("missing",)),)),
                  replace(self.p, 解法群=(手順(inputs=(問題素材("工程", "g"),)),)),
                  replace(self.p, 解法群=(手順(priority=True),)),
                  replace(self.p, 解法群=(replace(手順(), 下位目的=["g"]),))):
            with self.subTest(p=p):
                self.check(self.engine.実行(p, self.d), "失敗")

    def test_使われない依存を追加しても採用しない(self):
        p = replace(self.p, 解法群=(手順(children=("g",), inputs=(問題素材("入力", "素材"),)),))
        self.check(self.engine.実行(p, self.d), "失敗")

    def test_不足Dataと不正Data(self):
        for d in (None, {}, {**self.d, "素材": "text"},
                  {**self.d, "素材": 能力結果(True, "x", データ={"n": float("nan")})}):
            with self.subTest():
                self.check(self.engine.実行(self.p, d), "失敗")

    def test_未成立素材から値を採用しない(self):
        self.d["素材"] = 能力結果(False, "仮値")
        self.check(self.engine.実行(self.p, self.d), "保留")

    def test_名前とDataの領域を混同しない(self):
        self.d["g"] = 能力結果(True, "正解を偽装した文字列")
        r = self.engine.実行(self.p, self.d)
        self.check(r, "合格")
        self.assertEqual(r.出力[0][1].本文, "原資料")

    def test_実行前の停止(self):
        r = self.engine.実行(self.p, self.d, 停止要求=lambda: True)
        self.check(r, "中止")
        self.assertEqual(r.呼出数, 0)

    def test_能力内で停止した結果は採用しない(self):
        stop = [False]
        def action(c):
            stop[0] = True
            return 能力結果(True, "未採用")
        m = 試験能力(関数=action)
        p = replace(self.p, 解法群=(手順(module=m.名前),))
        r = 実行器(m).実行(p, self.d, 停止要求=lambda: stop[0])
        self.check(r, "中止")

    def test_停止判定が故障したら別経路へ進まない(self):
        m = 試験能力()
        for callback in (lambda: "false", lambda: 1 / 0):
            r = 実行器(m).実行(self.p, self.d, 停止要求=callback)
            self.check(r, "失敗")
        self.assertEqual(m.呼出, [])

    def test_予算超過で部分成功や完全探索を宣言しない(self):
        p = 多段問題(("g",), (目的(), 目的("a")),
                      (手順(children=("a",)), 手順("a", "a")))
        for options in ({"最大展開数": 1}, {"最大呼出数": 1}, {"最大深さ": 1}):
            with self.subTest(options=options):
                r = self.engine.実行(p, self.d, **options)
                self.check(r, "保留")
                self.assertIn("上限", r.理由)

    def test_予算は検証呼出も含む(self):
        self.check(self.engine.実行(self.p, self.d, 最大呼出数=1), "保留")
        self.check(self.engine.実行(self.p, self.d, 最大呼出数=2), "合格")

    def test_不正予算と入力サイズ(self):
        for value in (0, -1, True, 1.5):
            self.check(self.engine.実行(self.p, self.d, 最大展開数=value), "失敗")
        self.d["素材"] = 能力結果(True, "a" * 1000001)
        self.check(self.engine.実行(self.p, self.d), "失敗")

    def test_入力変異の分離(self):
        def mutate(c):
            c.補助["合成入力"][0]["結果"]["データ"]["配列"].append(999)
            return 能力結果(True, c.直前応答)
        m = 試験能力(関数=mutate)
        p = replace(self.p, 解法群=(手順(module=m.名前),))
        before = deepcopy(self.d)
        r = 実行器(m).実行(p, self.d)
        self.check(r, "合格")
        self.assertEqual(before, self.d)

    def test_返却値と原入力の分離(self):
        r = self.engine.実行(self.p, self.d)
        r.出力[0][1].データ["配列"].append(99)
        self.assertEqual(self.d["素材"].データ, {"配列": [1]})
        self.assertFalse(r.整合確認())

    def test_実行中の能力版変更を代替で隠さない(self):
        m = 試験能力()
        def mutate(c):
            m.版 = "changed"
            return 能力結果(True, "x")
        m.関数 = mutate
        p = replace(self.p, 解法群=(手順("first", module=m.名前), 手順("second", priority=1)))
        r = 実行器(m).実行(p, self.d)
        self.check(r, "失敗")
        self.assertIn("版変更", r.理由)

    def test_一度登録した能力の版変更を検出(self):
        m = 試験能力()
        engine = 実行器(m)
        m.版 = "changed"
        p = replace(self.p, 解法群=(手順(module=m.名前),))
        self.check(engine.実行(p, self.d), "失敗")
        self.assertEqual(m.呼出, [])

    def test_不正能力結果を成功にしない(self):
        m = 試験能力(関数=lambda c: "回答だけ")
        p = replace(self.p, 解法群=(手順(module=m.名前),))
        self.check(実行器(m).実行(p, self.d), "保留")

    def test_原典参照が最終成果へ残る(self):
        ref = 参照資料("s", "題", "利用者", 本文="原資料")
        self.d["素材"] = replace(self.d["素材"], 参照=(ref,))
        r = self.engine.実行(self.p, self.d)
        self.assertEqual(r.出力[0][1].参照, (ref,))

    def test_同じ入力では同じ実行記録(self):
        self.assertEqual(self.engine.実行(self.p, self.d), self.engine.実行(self.p, self.d))

    def test_再実行で前の状態を使わない(self):
        self.engine.実行(self.p, self.d)
        self.d["素材"] = 能力結果(True, "新資料")
        r = self.engine.実行(self.p, self.d)
        self.assertEqual(r.出力[0][1].本文, "新資料")

    def test_記録と採用経路の改変を検出(self):
        r = self.engine.実行(self.p, self.d)
        modified = deepcopy(r)
        modified.履歴[0]["目的"] = "改変"
        self.assertFalse(modified.整合確認())
        modified = deepcopy(r)
        modified.採用経路[0]["解法"] = "捏造"
        self.assertFalse(modified.整合確認())

    def test_JSON往復と未知フィールド拒否(self):
        raw = json.loads(json.dumps(asdict(self.p)))
        self.assertEqual(多段問題を復元(raw), self.p)
        with self.assertRaises(ValueError):
            多段問題を復元({**raw, "unknown": True})
        raw["解法群"][0]["入力"][0]["追加"] = True
        with self.assertRaises(ValueError):
            多段問題を復元(raw)


class 解法全列挙対照試験(unittest.TestCase):
    def test_子の直積と親の検証を独立列挙と対照(self):
        def add(c):
            items = c.補助["合成入力"]
            return 能力結果(True, str(sum(int(x["結果"]["本文"]) for x in items)))
        def eq(c):
            return 能力結果(c.直前応答 == c.補助["合成設定"]["期待値"], "検証")
        engine = 実行器(試験能力("加算", add), 試験能力("一致検査", eq))
        for xs, ys, target in product(((0,), (1, 2), (3, 1, 0)), ((0, 2), (1,)), range(6)):
            data = 入力()
            data["検査"] = 能力結果(True, "", データ={"期待値": str(target)})
            methods = []
            for name, values in (("x", xs), ("y", ys)):
                for i, value in enumerate(values):
                    key = name + str(i)
                    data[key] = 能力結果(True, str(value))
                    methods.append(手順(key, name, inputs=(問題素材("入力", key),), priority=i))
            methods.append(手順("sum", children=("x", "y"), module="加算"))
            p = 多段問題(("g",), (目的("x"), 目的("y"), 目的(check="一致検査", setting="検査")), tuple(methods))
            result = engine.実行(p, data)
            expected = any(x + y == target for x, y in product(xs, ys))
            self.assertEqual(result.成立, expected, (xs, ys, target, result.理由))
            self.assertTrue(result.整合確認())
            if expected:
                self.assertEqual(result.出力[0][1].本文, str(target))
            else:
                self.assertEqual(result.出力, ())


if __name__ == "__main__":
    unittest.main()

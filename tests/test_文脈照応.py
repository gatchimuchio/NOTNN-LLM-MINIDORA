"""文脈・照応の契約試験。契約CompilerはIR境界用で、実Compiler実測ではない。"""
from copy import deepcopy
from dataclasses import replace
import re
import unittest

from minidora.hds_ir import HDSIR, HDS実行核, HDS座標, HDS関係, HDS残差, 値状態
from minidora.文脈照応 import 会話参照記憶
from minidora.文脈要求 import 文脈付き要求セッション
from minidora.要求解釈 import 要求計画器
from minidora.要求解釈実行 import 要求計画を実行
from minidora.能力合成 import 能力合成器
from minidora.能力合成_局所接続 import 局所能力群
from minidora.製品版.型 import 能力結果, 参照資料
from minidora.製品版.能力契約 import 能力文脈


class 契約Compiler:
    def __init__(self):
        self.呼出 = []

    def コンパイル(self, 入力, *, 文脈=None, HDS履歴=()):
        self.呼出.append((入力, deepcopy(文脈), deepcopy(HDS履歴)))
        座標 = (HDS座標("src", "source_text", 入力),)
        関係, 残差, 引用 = (), (), ()
        match = re.search("それ|その", 入力)
        if match:
            if 文脈 is not None and 文脈.現在焦点 is not None:
                座標 += (HDS座標("p", "文脈.指示語", match[0], 値状態.推定),
                          HDS座標("f", "文脈.参照先", 文脈.現在焦点, 値状態.推定))
                関係 = (HDS関係("context", ("p",), ("f",), "共参照", 値状態=値状態.推定),)
                引用 = 文脈.記憶引用
            else:
                残差 = (HDS残差("residual", "未解共参照", match[0], "参照未解"),)
        return HDSIR(入力, 入力, "入力契約試験", 座標, 関係, 残差, (), HDS実行核(), 文脈引用=引用)


def 資料(n=120):
    text = f"売上は{n}です。費用は75です。利益は45です。"
    return {"本文": 能力結果(True, text, 参照=(参照資料("原典", "提供本文", "利用者", 本文=text),))}


def セッション(名前="s", **kwargs):
    return 文脈付き要求セッション(名前, コンパイラ=契約Compiler(), **kwargs)


class 文脈要求契約試験(unittest.TestCase):
    def setUp(self):
        self.s = セッション()

    def 起動(self, n=120):
        r = self.s.応答("本文を1行で要約して", 資料(n))
        self.assertTrue(r.成立, r.理由)
        return r

    def test_三turnの後続利用(self):
        self.起動()
        b = self.s.応答("それから数字を抽出して")
        c = self.s.応答("さっきの結果を箇条書きにして")
        self.assertTrue(b.成立, b.理由)
        self.assertTrue(c.成立, c.理由)
        self.assertEqual((b.出力[0][1].本文, c.出力[0][1].本文), ("120", "- 120"))
        self.assertEqual(self.s.起点().局所起点.版, 3)

    def test_語それを明示して抽出(self):
        self.起動()
        r = self.s.応答("それを数字化して")
        # 未対応の述語を都合よく読み替えない。
        self.assertFalse(r.成立)
        r = self.s.応答("それから数字を抽出して")
        self.assertTrue(r.成立, r.理由)

    def test_新規数値へ追従する(self):
        for n in (9, 731, 1024, 90007):
            with self.subTest(n=n):
                s = セッション()
                s.応答("1行で要約して", 資料(n))
                r = s.応答("それから数字を抽出して")
                self.assertTrue(r.成立, r.理由)
                self.assertEqual(r.出力[0][1].本文, str(n))

    def test_状態なし対照は保留(self):
        r = self.s.応答("それを要約して")
        self.assertEqual(r.状態, "保留")
        self.assertEqual(r.出力, ())
        self.assertEqual(self.s.起点().採用履歴, ())

    def test_初期化対照と世代境界(self):
        self.起動()
        before = self.s.起点()
        self.s.初期化()
        after = self.s.起点()
        self.assertEqual(after.局所起点.版, 0)
        self.assertNotEqual(before.世代, after.世代)
        self.assertEqual(after.採用履歴, ())
        self.assertFalse(self.s.応答("さっきのを要約して").成立)

    def test_初期化前の計画を実行しない(self):
        self.起動()
        p = self.s.準備("それを箇条書きにして")
        self.s.初期化()
        r = self.s.実行(p)
        self.assertFalse(r.成立)
        self.assertIsNone(r.実行)
        self.assertEqual(self.s.起点().局所起点.版, 0)

    def test_別セッションの計画を実行しない(self):
        self.起動()
        p = self.s.準備("それを箇条書きにして")
        for other in (セッション("other"), セッション("s")):
            with self.subTest():
                r = other.実行(p)
                self.assertFalse(r.成立)
                self.assertEqual(other.起点().局所起点.版, 0)
                self.assertIsNone(r.実行)

    def test_同名セッションでも値を共有しない(self):
        a, b = セッション("same"), セッション("same")
        a.応答("1行で要約して", 資料(111))
        b.応答("1行で要約して", 資料(222))
        self.assertEqual(a.応答("さっきのから数字を抽出して").出力[0][1].本文, "111")
        self.assertEqual(b.応答("さっきのから数字を抽出して").出力[0][1].本文, "222")

    def test_状態更新後の古い計画は失敗(self):
        self.起動()
        p = self.s.準備("それを箇条書きにして")
        self.s.応答("1行で要約して", 資料(300))
        before = self.s.起点()
        r = self.s.実行(p)
        self.assertFalse(r.成立)
        self.assertEqual(before, self.s.起点())
        self.assertIsNone(r.実行)

    def test_同じ計画を二重確定しない(self):
        self.起動()
        p = self.s.準備("それを箇条書きにして")
        self.assertTrue(self.s.実行(p).成立)
        self.assertFalse(self.s.実行(p).成立)
        self.assertEqual(self.s.起点().局所起点.版, 2)

    def test_準備は状態を進めない(self):
        self.起動()
        before = self.s.起点()
        self.s.準備("それを要約して")
        self.assertEqual(self.s.起点(), before)

    def test_失敗した応答は焦点を上書きしない(self):
        self.起動()
        before = self.s.起点()
        r = self.s.応答("それを要約して、英訳して")
        after = self.s.起点()
        self.assertEqual(r.状態, "保留")
        self.assertEqual(after.局所起点.現在焦点, before.局所起点.現在焦点)
        self.assertEqual(after.採用履歴, before.採用履歴)
        self.assertEqual(after.局所起点.直前採否, "保留")
        self.assertEqual(self.s.応答("さっきのから数字を抽出して").出力[0][1].本文, "120")

    def test_明示行数未達は記憶に入れない(self):
        self.起動()
        r = self.s.応答("それを3行で要約して")
        self.assertEqual(r.状態, "保留")
        self.assertEqual(len(self.s.起点().採用履歴), 1)

    def test_中止は記憶に入れない(self):
        self.起動()
        before = self.s.起点()
        r = self.s.応答("それを要約して", 停止要求=lambda: True)
        self.assertEqual(r.状態, "中止")
        self.assertEqual(before.採用履歴, self.s.起点().採用履歴)
        self.assertEqual(r.実行.合成.実行数, 0)

    def test_複数出力のそれは曖昧(self):
        data = {"A": 能力結果(True, "値10"), "B": 能力結果(True, "値22")}
        self.s.応答("資料「A」から数字を抽出して、資料「B」から数字を抽出して", data)
        r = self.s.応答("それを箇条書きにして")
        self.assertEqual(r.状態, "保留")
        self.assertTrue(any("複数" in v for v in r.理由))
        self.assertIsNone(r.実行.合成)

    def test_番号付き出力を選択(self):
        data = {"A": 能力結果(True, "値10"), "B": 能力結果(True, "値22")}
        self.s.応答("資料「A」から数字を抽出して、資料「B」から数字を抽出して", data)
        r = self.s.応答("さっきの2番を箇条書きにして")
        self.assertTrue(r.成立, r.理由)
        self.assertEqual(r.出力[0][1].本文, "- 22")
        self.assertEqual(r.解釈.文脈束縛[0].出力番号, 2)

    def test_古い応答を明示して再利用(self):
        self.起動(111)
        self.s.応答("1行で要約して", 資料(222))
        r = self.s.応答("第1応答から数字を抽出して")
        self.assertTrue(r.成立, r.理由)
        self.assertEqual(r.出力[0][1].本文, "111")
        self.assertEqual(r.解釈.文脈束縛[0].応答番号, 1)

    def test_全角の応答番号と出力番号(self):
        self.起動()
        r = self.s.応答("第１応答の１番から数字を抽出して")
        self.assertTrue(r.成立, r.理由)
        self.assertEqual(r.出力[0][1].本文, "120")

    def test_存在しない応答と出力は保留(self):
        self.起動()
        for text in ("第0応答を要約して", "第9応答を要約して", "前の0番を要約して", "さっきの2番を要約して"):
            with self.subTest(text=text):
                r = self.s.応答(text)
                self.assertEqual(r.状態, "保留")
                self.assertEqual(r.出力, ())

    def test_不採用turnの番号へ参照しない(self):
        self.起動()
        self.s.応答("英訳して")
        r = self.s.応答("第2応答を要約して")
        self.assertEqual(r.状態, "保留")

    def test_現在のそれと依頼内その結果を区別(self):
        self.起動()
        r = self.s.応答("それから数字を抽出して、その結果を箇条書きにして")
        self.assertTrue(r.成立, r.理由)
        a, b = r.解釈.要求
        self.assertEqual((a.素材.領域, b.素材.領域), ("入力", "工程"))
        self.assertEqual(len(r.解釈.文脈束縛), 1)
        self.assertEqual(r.出力[0][1].本文, "- 120")

    def test_新規資料処理のその結果は古い焦点でない(self):
        self.起動(111)
        r = self.s.応答("本文を1行で要約して、その結果から数字を抽出して", 資料(222))
        self.assertTrue(r.成立, r.理由)
        self.assertEqual(r.出力[0][1].本文, "222")
        self.assertEqual(r.解釈.文脈束縛, ())
        self.assertTrue(r.解釈.局所解消)

    def test_明示過去参照は後工程でも会話へ戻る(self):
        self.起動(111)
        r = self.s.応答("本文を1行で要約して、さっきのから数字を抽出して", 資料(222))
        self.assertTrue(r.成立, r.理由)
        self.assertEqual([x.本文 for _, x in r.出力], ["売上は222です。", "111"])

    def test_新規資料とそれが競合したら保留(self):
        self.起動()
        r = self.s.応答("それから数字を抽出して", 資料(999))
        self.assertEqual(r.状態, "保留")
        self.assertIsNone(r.実行.合成)

    def test_明示過去参照なら新規資料と競合しない(self):
        self.起動(111)
        r = self.s.応答("前の結果から数字を抽出して", 資料(222))
        self.assertTrue(r.成立, r.理由)
        self.assertEqual(r.出力[0][1].本文, "111")

    def test_出典と参照元を終端まで保持(self):
        a = self.起動()
        r = self.s.応答("それから数字を抽出して")
        self.assertEqual(r.出力[0][1].参照, a.出力[0][1].参照)
        b = r.解釈.文脈束縛[0]
        self.assertEqual((b.表層, b.応答番号, b.出力ID), ("それ", 1, a.出力[0][0]))
        self.assertEqual(r.解釈.HDS保持.原文[b.原文範囲[0]:b.原文範囲[1]], "それ")
        self.assertNotIn("売上", repr(r.解釈.計画))

    def test_HDSへ局所起点の版と引用を渡す(self):
        compiler = 契約Compiler()
        s = 文脈付き要求セッション("test", コンパイラ=compiler)
        s.応答("1行で要約して", 資料())
        before = s.起点()
        s.応答("それを要約して")
        text, c, h = compiler.呼出[-1]
        self.assertEqual(c.記憶版, before.局所起点.版)
        self.assertEqual(c.記憶引用, (before.識別子,))
        self.assertEqual(c.現在焦点, before.識別子)
        self.assertEqual(h, before.局所起点.IR履歴)

    def test_元のHDS推定を削除改変しない(self):
        self.起動()
        r = self.s.応答("それを要約して")
        self.assertTrue(r.成立, r.理由)
        self.assertTrue(any(c.値状態 == 値状態.推定 for c in r.解釈.HDS保持.座標))
        self.assertIn("関係:context", r.解釈.局所解消)

    def test_誤ったHDS引用は保留(self):
        self.起動()
        s = self.s.起点()
        ir = 契約Compiler().コンパイル("それを要約して", 文脈=s.HDS文脈へ())
        for bad in (replace(ir, 文脈引用=("他の状態",)),
                    replace(ir, 座標=ir.座標[:-1]+(replace(ir.座標[-1], 内容="違う焦点"),))):
            with self.subTest():
                r = 要求計画器().コンパイル(bad, {}, 文脈=s)
                self.assertEqual(r.状態, "保留")

    def test_HDSの未知損失を共参照として消さない(self):
        self.起動()
        s = self.s.起点()
        ir = 契約Compiler().コンパイル("それを要約して", 文脈=s.HDS文脈へ())
        ir = replace(ir, 残差=(HDS残差("lost", "semantic_loss", "それ", "条件脱落"),))
        r = 要求計画器().コンパイル(ir, {}, 文脈=s)
        self.assertEqual(r.状態, "保留")
        self.assertEqual(r.HDS保持, ir)

    def test_計画に紐づく文脈なしでは実行しない(self):
        self.起動()
        p = self.s.準備("それを要約して")
        r = 要求計画を実行(p.解釈, 能力合成器(局所能力群()))
        self.assertEqual(r.状態, "失敗")
        self.assertIsNone(r.合成)

    def test_下位実行のセッション不一致(self):
        self.起動()
        p = self.s.準備("それを要約して")
        r = 要求計画を実行(p.解釈, 能力合成器(局所能力群()),
                             文脈起点=p.起点, 文脈=能力文脈("", "other"))
        self.assertEqual(r.状態, "失敗")
        self.assertIsNone(r.合成)

    def test_外部へ返した値の変異は記憶へ波及しない(self):
        r = self.起動()
        before = self.s.起点()
        r.出力[0][1].データ["改変"] = [1]
        r.解釈.初期Data.clear()
        self.assertEqual(self.s.起点(), before)

    def test_スナップショットの変異も原本へ波及しない(self):
        self.起動()
        before = self.s.起点()
        s = self.s.起点()
        s.採用履歴[0].出力[0][1].データ["改変"] = True
        self.assertFalse(s.整合確認())
        self.assertEqual(self.s.起点(), before)

    def test_改変計画のDataを実行しない(self):
        self.起動()
        p = self.s.準備("それを要約して")
        p.解釈.初期Data["設定:要求:0001"].データ["行数"] = 7
        self.assertFalse(self.s.実行(p).成立)
        self.assertEqual(self.s.起点().局所起点.版, 1)

    def test_同じ起点の同じ依頼は同じ計画指紋(self):
        self.起動()
        a = self.s.準備("それを要約して")
        b = self.s.準備("それを要約して")
        self.assertEqual(a, b)

    def test_再入は保留し外側だけ確定する(self):
        self.起動()
        nested = []
        def stop():
            nested.append(self.s.応答("それを要約して"))
            return False
        r = self.s.応答("それを要約して", 停止要求=stop)
        self.assertTrue(r.成立, r.理由)
        self.assertTrue(nested)
        self.assertTrue(all(x.状態 == "保留" for x in nested))
        self.assertEqual(self.s.起点().局所起点.版, 2)

    def test_処理中の初期化は拒否(self):
        self.起動()
        def stop():
            with self.assertRaises(ValueError):
                self.s.初期化()
            return False
        self.assertTrue(self.s.応答("それを要約して", 停止要求=stop).成立)

    def test_応答数上限で暗黙の履歴剪定をしない(self):
        s = セッション(最大応答数=1)
        s.応答("1行で要約して", 資料())
        before = s.起点()
        r = s.応答("それを要約して")
        self.assertFalse(r.成立)
        self.assertEqual(s.起点(), before)
        s.初期化()
        self.assertTrue(s.応答("1行で要約して", 資料()).成立)

    def test_記録サイズ超過は状態を更新しない(self):
        s = セッション(最大記録バイト数=100)
        before = s.起点()
        r = s.応答("1行で要約して", 資料())
        self.assertFalse(r.成立)
        self.assertEqual(r.出力, ())
        self.assertEqual(s.起点(), before)

    def test_前の回答と直前の結果の表層(self):
        for phrase in ("前の結果", "前の回答", "直前の応答", "さっきの", "第1応答"):
            with self.subTest(phrase=phrase):
                s = セッション()
                s.応答("1行で要約して", 資料())
                r = s.応答(f"{phrase}から数字を抽出して")
                self.assertTrue(r.成立, r.理由)
                self.assertEqual(r.出力[0][1].本文, "120")

    def test_文章内の番号を構造化された出力番号と混同しない(self):
        self.s.応答("箇条書きにして", {"文": 能力結果(True, "一つ。二つ。三つ。")})
        r = self.s.応答("さっきの3番を要約して")
        self.assertEqual(r.状態, "保留")

    def test_Compilerの別原文を実行しない(self):
        class 原文誤り(契約Compiler):
            def コンパイル(self, 入力, **kwargs):
                return super().コンパイル("1行で要約して", **kwargs)
        s = 文脈付き要求セッション("s", コンパイラ=原文誤り())
        r = s.応答("英訳して", 資料())
        self.assertFalse(r.成立)
        self.assertIsNone(r.実行)
        self.assertEqual(s.起点().局所起点.版, 0)

    def test_過大依頼をCompilerへ渡さない(self):
        c = 契約Compiler()
        s = 文脈付き要求セッション("s", コンパイラ=c)
        self.assertFalse(s.応答("あ" * 8193).成立)
        self.assertEqual(c.呼出, [])

    def test_共参照と同じIDの未知関係で検査を迂回できない(self):
        self.起動()
        s = self.s.起点()
        ir = 契約Compiler().コンパイル("それを要約して", 文脈=s.HDS文脈へ())
        ir = replace(ir, 関係=ir.関係+(HDS関係("context", ("src",), ("src",), "未知"),))
        r = 要求計画器().コンパイル(ir, {}, 文脈=s)
        self.assertEqual(r.状態, "失敗")

    def test_無効入力で状態を汚さない(self):
        self.起動()
        before = self.s.起点()
        self.assertFalse(self.s.応答(None).成立)
        self.assertEqual(self.s.起点(), before)


class 会話参照記憶試験(unittest.TestCase):
    def test_採用状態は既存局所キャッシュへ到達(self):
        m = 会話参照記憶("s")
        out = (("a", 能力結果(True, "値120")),)
        s = m.更新(m.起点(), "依頼", "合格", 出力=out)
        self.assertEqual(s.局所起点.現在焦点, out)
        self.assertEqual(s.局所起点.直前結果, out)
        self.assertTrue(s.整合確認())

    def test_更新の比較交換と失敗時原本保持(self):
        m = 会話参照記憶("s")
        start = m.起点()
        m.更新(start, "依頼", "保留")
        before = m.起点()
        with self.assertRaises(ValueError):
            m.更新(start, "依頼", "保留")
        self.assertEqual(before, m.起点())

    def test_不正更新を採用しない(self):
        m = 会話参照記憶("s")
        bad = (("合格", ()), ("保留", (("a", 能力結果(True, "x")),)),
               ("合格", (("a", 能力結果(False, "x")),)),
               ("合格", (("a", 能力結果(True, "x")), ("a", 能力結果(True, "y")))))
        for status, out in bad:
            with self.subTest(status=status, out=out), self.assertRaises(ValueError):
                m.更新(m.起点(), "依頼", status, 出力=out)
        self.assertEqual(m.起点().局所起点.版, 0)

    def test_不正セッションと上限(self):
        for name in (None, "", " " , "\ud800"):
            with self.subTest(name=name), self.assertRaises(ValueError):
                会話参照記憶(name)
        for n in (0, -1, True, 1.5):
            with self.subTest(n=n), self.assertRaises(ValueError):
                会話参照記憶("s", 最大応答数=n)

    def test_空結果を参照可能な本文にしない(self):
        m = 会話参照記憶("s")
        s = m.更新(m.起点(), "依頼", "合格", 出力=(("a", 能力結果(True, "")),))
        with self.assertRaises(ValueError):
            s.解決("それ", (0, 2))

    def test_型不正資料を焦点にしない(self):
        m = 会話参照記憶("s")
        for x in (能力結果(True, "x", データ={"n":float("nan")}), 能力結果(True, "x", 根拠=["x"])):
            with self.subTest(), self.assertRaises(ValueError):
                m.更新(m.起点(), "依頼", "合格", 出力=(("a", x),))
        self.assertEqual(m.起点().採用履歴, ())


if __name__ == "__main__":
    unittest.main()

import unittest

from minidora import (
    HDSIR,
    HDS実行核,
    HDS座標,
    HDS残差,
    HDS文脈,
    ミニドラ,
    要求,
    手順,
    命令,
    作用,
    実行状態,
)


def _加算IR(入力, 左, 右, *, 言語="ja", 文脈引用=()):
    proc = 手順(
        "fixture:HDS-IR加算",
        (命令("加算", 作用.加算, 引数=("$a", "$b"), 更新先="結果", 根拠=("fixture:HDS-IR",)),),
        由来="fixture compiler",
    )
    return HDSIR(
        原文=入力,
        正規化文=入力,
        認知世界ID="fixture:world",
        座標=(
            HDS座標("a", "対象.現在状態", 左),
            HDS座標("b", "対象.現在状態", 右),
            HDS座標("action", "手段.作用", "加算"),
            HDS座標("result", "目的.到達状態", "加算結果"),
        ),
        関係=(),
        残差=(),
        意味作用履歴=(),
        実行核=HDS実行核("加算", ("a", "b"), "結果"),
        初期状態={"a": 左, "b": 右},
        参照必須=False,
        種別="fixture:加算",
        閉包状態="CLOSED_FOR_OPERATION",
        表現状態="MEANING_PRESERVED",
        手順=proc,
        入力言語=言語,
        出力言語=言語,
        文脈引用=tuple(文脈引用),
    )


def _未閉包IR(入力, *, 言語="ja", 理由="文脈参照先がない"):
    return HDSIR(
        原文=入力,
        正規化文=入力,
        認知世界ID="fixture:open",
        座標=(HDS座標("target", "対象.実体", 入力),),
        関係=(),
        残差=(HDS残差("res:0", "semantic_loss", 入力, 理由),),
        意味作用履歴=(),
        実行核=HDS実行核(),
        初期状態={},
        参照必須=False,
        種別="fixture:未閉包",
        手順=None,
        入力言語=言語,
        出力言語=言語,
    )


class 多言語TrinityFixtureCompiler:
    def コンパイル(self, 入力, *, 前回結果=None, HDS履歴=(), 文脈: HDS文脈 | None = None):
        language = "ja"
        if any(token in 入力 for token in ("What", "Add", "sum", "plus", "it")):
            language = "en"
        elif any(token in 入力 for token in ("总和", "给", "它", "多少")):
            language = "zh"

        followup = any(token in 入力 for token in ("それ", "it", "它"))
        if followup:
            focus = 文脈.現在焦点 if 文脈 is not None else 前回結果
            if focus is None:
                return _未閉包IR(入力, 言語=language)
            refs = 文脈.記憶引用 if 文脈 is not None else ("legacy:last_result",)
            return _加算IR(入力, focus, 4, 言語=language, 文脈引用=refs)

        return _加算IR(入力, 2, 3, 言語=language)


class 旧式FixtureCompiler:
    def コンパイル(self, 入力, *, 前回結果=None, HDS履歴=()):
        return _加算IR(入力, 2, 3)


class 多言語Trinity試験(unittest.TestCase):
    def test_日本語英語中国語が同じHDS実行核へ落ちる(self):
        body = ミニドラ(HDSコンパイラ_=多言語TrinityFixtureCompiler())
        cases = (
            ("2と3の和は？", "ja"),
            ("What is the sum of 2 and 3?", "en"),
            ("2和3的总和是多少？", "zh"),
        )
        signatures = []
        for text, language in cases:
            ir = body.コンパイル(text)
            self.assertEqual(ir.入力言語, language)
            signatures.append((ir.実行核.作用, tuple(ir.初期状態.values())))
        self.assertEqual(set(signatures), {("加算", (2, 3))})

    def test_各入力言語へ自然言語出力を戻す(self):
        self.assertEqual(ミニドラ(HDSコンパイラ_=多言語TrinityFixtureCompiler()).応答("2と3の和は？"), "5です。")
        self.assertEqual(ミニドラ(HDSコンパイラ_=多言語TrinityFixtureCompiler()).応答("What is the sum of 2 and 3?"), "5.")
        self.assertEqual(ミニドラ(HDSコンパイラ_=多言語TrinityFixtureCompiler()).応答("2和3的总和是多少？"), "5。")

    def test_Trinity_MからJが現在焦点を引用して言語跨ぎで継続する(self):
        body = ミニドラ(HDSコンパイラ_=多言語TrinityFixtureCompiler())
        self.assertEqual(body.応答("2と3の和は？"), "5です。")
        self.assertEqual(body.応答("Add 4 to it"), "9.")
        self.assertEqual(body.応答("给它加4"), "13。")
        self.assertEqual(body.応答("それに4を足して"), "17です。")
        self.assertEqual(body.HDS文脈.現在焦点, 17)
        self.assertIn("working:current_focus", body.HDS文脈.記憶引用)
        self.assertEqual(len(body.HDS履歴), 4)
        self.assertIn("working:current_focus", body.HDS履歴[-1].文脈引用)

    def test_文脈参照先なしは捏造せず保留(self):
        body = ミニドラ(HDSコンパイラ_=多言語TrinityFixtureCompiler())
        result = body.実行(要求("Add 4 to it"))
        self.assertEqual(result.採否.状態, 実行状態.保留)
        self.assertIsNone(result.値)
        self.assertEqual(result.HDS_IR.入力言語, "en")

    def test_未閉包残差をMが次turn文脈として保持する(self):
        body = ミニドラ(HDSコンパイラ_=多言語TrinityFixtureCompiler())
        body.実行(要求("Add 4 to it"))
        self.assertTrue(body.HDS文脈.未解残差)
        self.assertIn("working:unresolved", body.HDS文脈.記憶引用)

    def test_旧式Compilerも文脈引数なしで継続利用できる(self):
        body = ミニドラ(HDSコンパイラ_=旧式FixtureCompiler())
        self.assertEqual(body.応答("任意"), "5です。")


if __name__ == "__main__":
    unittest.main()

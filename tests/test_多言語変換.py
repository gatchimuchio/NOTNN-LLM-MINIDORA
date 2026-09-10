"""日英の役割保持・全文消費・外部語彙・境界と改変の局所試験。"""
from copy import deepcopy
from dataclasses import replace
from fractions import Fraction
from hashlib import sha256
from itertools import product
import json
import unittest

from minidora.多言語変換 import 対訳語, 対訳を変換, 翻訳記録整合
from minidora.証拠統合 import 証拠統合器, 証拠照合要求
from minidora.製品版.型 import 能力結果, 参照資料


def 辞書():
    return (対訳語("対象A", "対象", "装置A", "device A"),
            対訳語("対象B", "対象", "装置B", "device B"),
            対訳語("電圧", "属性", "電圧", "voltage"),
            対訳語("電流", "属性", "電流", "current"),
            対訳語("通常", "条件", "通常", "normal"),
            対訳語("試験", "条件", "試験", "test"),
            対訳語("V", "単位", "V", "V"),
            対訳語("A", "単位", "A", "A"))


class 日英対訳試験(unittest.TestCase):
    def translate(self, source, origin="en", kind="数値記載", words=None, **options):
        result = 対訳を変換(source, origin, "ja" if origin == "en" else "en", 種別=kind,
                            対訳=辞書() if words is None else words, **options)
        self.assertTrue(result.成立, (result.保留理由, result.データ))
        self.assertTrue(翻訳記録整合(result))
        return result

    def test_数値記載を語順変更して翻訳(self):
        r = self.translate("The voltage of device A is 120 V.")
        self.assertEqual(r.本文, "装置Aの電圧は120 Vです。")
        self.assertEqual(r.データ["日本語基底"], r.本文)

    def test_日本語から英語を生成する(self):
        r = self.translate("装置Bの電流は5 Aです。", "ja")
        self.assertEqual(r.本文, "the current of device B is exactly 5 A.")
        self.assertEqual(r.データ["日本語基底"], "装置Bの電流は5 Aです。")

    def test_日付条件比較否定を全部保持(self):
        text = 'As of 2026-09-01, under condition "normal", the voltage of device A is not at least 120 V.'
        r = self.translate(text)
        self.assertEqual(r.本文, '2026-09-01時点、条件「通常」では、装置Aの電圧は120 V以上ではない。')
        self.assertEqual(r.データ["意味列"][0]["時点"], "2026-09-01")
        self.assertTrue(r.データ["意味列"][0]["否定"])

    def test_未知の条件を無条件へ変えない(self):
        r = 対訳を変換('under condition "unknown", the voltage of device A is 120 V.', "en", "ja", 種別="数値記載", 対訳=辞書())
        self.assertFalse(r.成立)
        self.assertEqual(r.本文, "")
        self.assertTrue(r.データ["残差"])

    def test_未記載条件時点を補完しない(self):
        meaning = self.translate("the voltage of device A is 120 V.").データ["意味列"][0]
        self.assertIsNone(meaning["条件"])
        self.assertIsNone(meaning["時点"])

    def test_値の摂動が訳文へ到達する(self):
        for n in ("0", "-9", "731", "+00120.00", "1.23e-2"):
            with self.subTest(n=n):
                r = self.translate(f"the voltage of device A is {n} V.")
                self.assertIn(n + " V", r.本文)
                self.assertEqual(r.データ["意味列"][0]["値"], n)

    def test_辞書Data変更で同じソースの表層だけを変更(self):
        words = tuple(replace(w, 日本語="機器甲") if w.識別子 == "対象A" else w for w in 辞書())
        original = "the voltage of device A is 731 V."
        a, b = self.translate(original), self.translate(original, words=words)
        self.assertIn("機器甲", b.本文)
        self.assertNotEqual(a.本文, b.本文)
        self.assertEqual(a.データ["意味列"], b.データ["意味列"])

    def test_未知語は辞書が追加されるまで処理しない(self):
        text = "the mass of item Z is 7 kg."
        r = 対訳を変換(text, "en", "ja", 種別="数値記載", 対訳=辞書())
        self.assertFalse(r.成立)
        extra = (対訳語("質量", "属性", "質量", "mass"), 対訳語("品目", "対象", "品目Z", "item Z"), 対訳語("kg", "単位", "kg", "kg"))
        r = self.translate(text, words=辞書() + extra)
        self.assertEqual(r.本文, "品目Zの質量は7 kgです。")

    def test_語彙なしでは固有名詞や単位をコピーで埋めない(self):
        r = 対訳を変換("the voltage of device A is 120 V.", "en", "ja", 種別="数値記載")
        self.assertFalse(r.成立)

    def test_重複表層から一つを勝手に選ばない(self):
        for words in (辞書() + (対訳語("異義", "属性", "起電力", "voltage"),), 辞書() + (辞書()[0],)):
            r = 対訳を変換("the voltage of device A is 120 V.", "en", "ja", 種別="数値記載", 対訳=words)
            self.assertFalse(r.成立)

    def test_対象属性の複数分割を検出(self):
        words = (対訳語("甲", "対象", "甲", "B of C"), 対訳語("乙", "属性", "乙", "A"),
                 対訳語("丙", "対象", "丙", "C"), 対訳語("丁", "属性", "丁", "A of B"), 対訳語("V", "単位", "V", "V"))
        r = 対訳を変換("the A of B of C is 1 V.", "en", "ja", 種別="数値記載", 対訳=words)
        self.assertFalse(r.成立)
        self.assertIn("曖昧", str(r.データ))

    def test_未知の助動詞近似引用質問を断定へ変換しない(self):
        for text in ("the voltage of device A may be 120 V.", "the voltage of device A is approximately 120 V.",
                     '"the voltage of device A is 120 V."', "is the voltage of device A 120 V?",
                     "the voltage of device A is not not 120 V."):
            with self.subTest(text=text):
                self.assertFalse(対訳を変換(text, "en", "ja", 種別="数値記載", 対訳=辞書()).成立)

    def test_同じ行の未知の尾部を無視しない(self):
        r = 対訳を変換("the voltage of device A is 120 V. This is a hypothesis.", "en", "ja", 種別="数値記載", 対訳=辞書())
        self.assertFalse(r.成立)
        self.assertEqual(r.本文, "")
        self.assertIn("hypothesis", r.データ["残差"][0]["原文"])

    def test_次の行の留保でも全体を保留(self):
        text = "the voltage of device A is 120 V.\nHowever, this is a hypothesis."
        r = 対訳を変換(text, "en", "ja", 種別="数値記載", 対訳=辞書())
        self.assertFalse(r.成立)
        self.assertEqual(r.本文, "")
        self.assertEqual(r.データ["解釈済み行数"], 1)
        for residual in r.データ["残差"]:
            self.assertEqual(text[residual["開始"]:residual["終了"]], residual["原文"])

    def test_複数記載を順序と逆方向でも保持(self):
        source = "the voltage of device A is 120 V.\nthe voltage of device B is not greater than 240 V."
        a = self.translate(source)
        b = self.translate(a.本文, "ja")
        self.assertEqual(a.データ["意味列"], b.データ["意味列"])
        self.assertEqual([r["対象"] for r in a.データ["意味列"]], ["対象A", "対象B"])

    def test_原文と訳文の全文範囲対応(self):
        source = " \r\n The voltage of device A is 120 V. \r\n\r\nthe current of device B is 5 A.\n"
        result = self.translate(source)
        self.assertEqual(result.データ["入力"]["本文"], source)
        for row in result.データ["対応"]:
            self.assertEqual(source[row["原文開始"]:row["原文終了"]], row["原文"])
            self.assertEqual(result.本文[row["訳文開始"]:row["訳文終了"]], row["訳文"])
            for key in ("値", "単位"):
                a, b = row["原文役割"][key]; c, d = row["訳文役割"][key]
                self.assertEqual(source[a:b], result.本文[c:d])

    def test_不正日付を補修しない(self):
        self.assertFalse(対訳を変換('As of 2026-02-30, the voltage of device A is 120 V.', "en", "ja", 種別="数値記載", 対訳=辞書()).成立)

    def test_未知言語自動判定と同一言語を拒否(self):
        for a, b in (("auto", "ja"), ("zh", "ja"), ("ja", "ja"), (None, "en")):
            self.assertFalse(対訳を変換("装置Aの電圧は120 Vです。", a, b, 種別="数値記載", 対訳=辞書()).成立)

    def test_出力予算不足で途中切断しない(self):
        source = "the voltage of device A is 120 V."
        full = self.translate(source)
        n = len(full.本文.encode())
        self.assertTrue(self.translate(source, 最大出力バイト数=n).成立)
        r = 対訳を変換(source, "en", "ja", 種別="数値記載", 対訳=辞書(), 最大出力バイト数=n-1)
        self.assertFalse(r.成立)
        self.assertEqual(r.本文, "")

    def test_改変値とhashの付け直しを再構成で検出(self):
        r = self.translate("the voltage of device A is 120 V.")
        r.データ["意味列"][0]["値"] = "999"
        r.データ.pop("記録SHA256")
        r.データ["記録SHA256"] = sha256(json.dumps({"本文": r.本文, "データ": r.データ}, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode()).hexdigest()
        self.assertFalse(翻訳記録整合(r))

    def test_否定削除や出典対応改変を検出(self):
        r = self.translate("the voltage of device A is not 120 V.")
        self.assertFalse(翻訳記録整合(replace(r, 本文=r.本文.replace("ではない", "です"))))
        r.データ["対応"][0]["原文開始"] += 1
        self.assertFalse(翻訳記録整合(r))

    def test_入力辞書を変更せず反復再現(self):
        words = 辞書(); before = deepcopy(words)
        a = self.translate("the voltage of device A is 120 V.", words=words)
        b = self.translate("the voltage of device A is 120 V.", words=words)
        self.assertEqual(a, b)
        a.データ["入力"]["対訳"][0]["日本語"] = "変更"
        self.assertEqual(words, before)

    def test_不正型大きい入力と制御文字を拒否(self):
        for text in (None, {}, "", " ", "a" * 32769, "the voltage\u202e of device A is 120 V.", "the voltage\x00 of device A is 120 V.", "a\n" * 65):
            self.assertFalse(対訳を変換(text, "en", "ja", 種別="数値記載", 対訳=辞書()).成立)
        for budget in (0, True, -1, 131073):
            self.assertFalse(対訳を変換("Extract numbers from the text.", "en", "ja", 種別="文書依頼", 最大出力バイト数=budget).成立)

    def test_辞書の未知役割制御文字と過大入力(self):
        for words in ([辞書()[0]], 辞書() * 20, (対訳語("x", "命令", "送信", "send"),),
                      (対訳語("x", "属性", "電圧", "volt\nrun"),), (対訳語("x", "属性", "電圧", "voltage; send"),)):
            self.assertFalse(対訳を変換("x", "en", "ja", 種別="数値記載", 対訳=words).成立)

    def test_停止と制御故障では部分訳を返さない(self):
        for stop in (lambda: True, lambda: "false", lambda: 1/0):
            r = 対訳を変換("the voltage of device A is 120 V.", "en", "ja", 種別="数値記載", 対訳=辞書(), 停止要求=stop)
            self.assertFalse(r.成立)
            self.assertEqual(r.本文, "")

    def test_結果以外の物や通常本文は翻訳記録でない(self):
        for value in (None, {}, 能力結果(True, "hello"), 能力結果(False, "")):
            self.assertFalse(翻訳記録整合(value))

    def test_命令文と数値文の責任を混ぜない(self):
        self.assertFalse(対訳を変換("Extract numbers from the text.", "en", "ja", 種別="数値記載", 対訳=辞書()).成立)
        self.assertFalse(対訳を変換("the voltage of device A is 120 V.", "en", "ja", 種別="文書依頼").成立)


class 文書依頼対訳試験(unittest.TestCase):
    def translate(self, text, origin="en"):
        r = 対訳を変換(text, origin, "ja" if origin == "en" else "en", 種別="文書依頼")
        self.assertTrue(r.成立, r.データ)
        self.assertTrue(翻訳記録整合(r))
        return r

    def test_抽出要求は対象と作用を分ける(self):
        r = self.translate("Extract numbers from the text.")
        self.assertEqual(r.本文, "本文から数字を抽出して")
        self.assertEqual(r.データ["意味列"][0]["対象"], "本文")

    def test_要約の行数上限と厳密数を混同しない(self):
        a = self.translate("Summarize the text in at most 2 lines.")
        b = self.translate("Summarize the text in exactly 2 lines.")
        self.assertEqual(a.本文, "本文を2行以内で要約して")
        self.assertEqual(b.本文, "本文を2行で要約して")
        self.assertNotEqual(a.データ["意味列"], b.データ["意味列"])
        self.assertEqual(self.translate("本文を1行で要約して", "ja").本文, "Summarize the text in exactly 1 line.")

    def test_行数がなければ翻訳側で補完しない(self):
        r = self.translate("Summarize the text.")
        self.assertEqual(r.本文, "本文を要約して")
        self.assertIsNone(r.データ["意味列"][0]["行数"])

    def test_名前付き資料を勝手に翻訳しない(self):
        r = self.translate('Extract URLs from document "資料A".')
        self.assertEqual(r.本文, "資料「資料A」からURLを抽出して")
        self.assertEqual(self.translate(r.本文, "ja").本文, 'Extract URLs from document "資料A".')

    def test_過去回答への照応を保持(self):
        self.assertEqual(self.translate("Format the previous answer as bullet points.").本文, "前の回答を箇条書きにして")
        self.assertEqual(self.translate("Extract numbers from it.").本文, "それから数字を抽出して")

    def test_同じ依頼内の前工程と元資料を区別(self):
        text = "Summarize the text in exactly 1 line.\nExtract numbers from the result.\nExtract URLs from the original text."
        r = self.translate(text)
        self.assertEqual([m["対象"] for m in r.データ["意味列"]], ["本文", "その結果", "元の本文"])
        self.assertEqual(self.translate(r.本文, "ja").データ["意味列"], r.データ["意味列"])

    def test_前工程がない結果参照を推定で補完しない(self):
        r = 対訳を変換("Extract numbers from the result.", "en", "ja", 種別="文書依頼")
        self.assertFalse(r.成立)

    def test_丁寧表現は原文に残して命令形へ構成(self):
        text = "Please extract keywords from the text."
        r = self.translate(text)
        self.assertEqual(r.本文, "本文からキーワードを抽出して")
        self.assertEqual(r.データ["入力"]["本文"], text)

    def test_否定や条件を捨てて依頼化しない(self):
        for text in ("Do not extract numbers from the text.", "Extract numbers from the text, but keep only positives.",
                     "If there are numbers, extract numbers from the text.", "Summarize the text in at most 9 lines.",
                     "Extract numbers from the text. Then delete it."):
            self.assertFalse(対訳を変換(text, "en", "ja", 種別="文書依頼").成立)

    def test_日本語から英語へも作用種類を保持(self):
        for text, expected in (("本文からURLを抽出して", "Extract URLs from the text."),
                               ("本文を箇条書きにして", "Format the text as bullet points."),
                               ("本文を要約して", "Summarize the text.")):
            self.assertEqual(self.translate(text, "ja").本文, expected)

    def test_引用された命令を直接実行用にしない(self):
        for text in ('"Extract numbers from the text."', "The user said: Extract numbers from the text."):
            self.assertFalse(対訳を変換(text, "en", "ja", 種別="文書依頼").成立)


class 日英否定比較独立対照試験(unittest.TestCase):
    def test_対訳を既存証拠解析へ渡して真理値を独立照合(self):
        # 翻訳器の比較辞書を参照しない別の比較関数で、境界の意味を照合する。
        relations = {"exactly": lambda x, c: x == c, "at least": lambda x, c: x >= c,
                     "at most": lambda x, c: x <= c, "less than": lambda x, c: x < c,
                     "greater than": lambda x, c: x > c}
        japanese = {"一致": lambda x, c: x == c, "不一致": lambda x, c: x != c,
                    "以上": lambda x, c: x >= c, "以下": lambda x, c: x <= c,
                    "未満": lambda x, c: x < c, "超": lambda x, c: x > c}
        count = 0
        for op, neg, threshold in product(relations, (False, True), ("-2", "0", "0.1", "731")):
            text = f'the voltage of device A is {"not " if neg else ""}{op} {threshold} V.'
            r = 対訳を変換(text, "en", "ja", 種別="数値記載", 対訳=辞書())
            self.assertTrue(r.成立, r.データ)
            report = 証拠統合器().実行(証拠照合要求("装置A", "電圧", "V"), (参照資料("対訳", "人工訳", "翻訳試験", 本文=r.本文),))
            self.assertTrue(report.成立)
            self.assertFalse(report.データ["残差"])
            claim = report.データ["主張"][0]
            for delta in (Fraction(-1), Fraction(0), Fraction(1)):
                x, c = Fraction(threshold) + delta, Fraction(threshold)
                expected = relations[op](x, c) != neg
                self.assertEqual(japanese[claim["比較"]](x, Fraction(claim["値"])), expected)
                count += 1
        self.assertEqual(count, 120)


if __name__ == "__main__":
    unittest.main()

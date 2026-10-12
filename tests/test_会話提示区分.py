"""提示構造と命令作用の区分。本文題材に依存しない開発契約。"""
import unittest
from dataclasses import replace
from unittest.mock import patch

from minidora.HDS会話意味射影 import 会話制御文を分ける, 会話意味欄を読む
from minidora.HDS構文化器_v1 import 公開HDSコンパイラ
from minidora.HDS運用.一般依頼 import 一般依頼を読む


class 会話提示区分試験(unittest.TestCase):
    def test_依頼と空行で提示した全文を同じ意味IRへ保存(self):
        for 依頼 in ("配達メモの要点をまとめてください。", "この予定を説明して。", "担当の役割を要約して。"):
            for 改行 in ("\n", "\r\n"):
                本文 = "調整役は配送時刻を連絡する。" + 改行 + "荷物の検査は受取人が行う。"
                原文 = 依頼 + 改行 + 改行 + 本文
                with self.subTest(依頼=依頼, 改行=改行):
                    制御, 素材, 範囲 = 会話制御文を分ける(原文)
                    self.assertEqual(制御, 依頼)
                    self.assertEqual(素材, 本文)
                    self.assertEqual(原文[slice(*範囲)], 本文)
                    束 = 公開HDSコンパイラ().コンパイル束(原文)
                    self.assertEqual(束.意味IR.原文, 原文)
                    座標 = next(項 for 項 in 束.意味IR.座標 if 項.種別 == "情報源.会話提示本文")
                    self.assertEqual(座標.内容, 本文)
                    self.assertEqual(原文[slice(*座標.原文範囲)], 本文)
                    self.assertFalse(any(本文 in 項.原文 for 項 in 束.意味IR.残差 if 項.種別 == "会話未消費"))

    def test_提示本文の操作句を実行へ変えない(self):
        本文 = "掲示には「8+9を計算して」と書かれている。掲示の掲出者は未確認である。"
        原文 = "この掲示を要約して。\n\n" + 本文
        束 = 公開HDSコンパイラ().コンパイル束(原文)
        self.assertEqual(会話意味欄を読む(束.意味IR)["提示本文"], 本文)
        self.assertFalse(any(要求.種別 == "計算" for 要求 in 束.コア入力.作用要求))

    def test_追加依頼や未知命令だけの段落は制御文に残す(self):
        for 後続 in ("箇条書きにしてください。", "メールで送って。", "例外を省いて。", "80文字以内で。", "説明して。\n保管係へ送って。"):
            原文 = "配達メモを要約して。\n\n" + 後続
            with self.subTest(後続=後続):
                self.assertEqual(会話制御文を分ける(原文), (原文, "", None))
                束 = 公開HDSコンパイラ().コンパイル束(原文)
                self.assertFalse(any(項.種別 == "情報源.会話提示本文" for 項 in 束.意味IR.座標))

    def test_空行のない追問や宣言を提示資料へ変えない(self):
        for 文 in ("要約して。\nメールで送って。", "配達メモは未完成だ。\n\n担当者は未定だ。", "形式を変えて。\n\n箇条書きにして。"):
            self.assertEqual(会話制御文を分ける(文), (文, "", None))

    def test_未消費の制御指定は本文分離後も拒否する(self):
        原文 = "このメモを要約して、例外を省いて。\n\n配送は予約がある場合に限る。"
        束 = 公開HDSコンパイラ().コンパイル束(原文)
        self.assertTrue(any(項.種別 == "会話未消費" for 項 in 束.意味IR.残差))
        with self.assertRaises(ValueError):
            一般依頼を読む({"原文": 原文}, 意味IR=束.意味IR)

    def test_添加表現を訂正や前目的要求にしない(self):
        for 標識 in ("だけでなく", "だけではなく", "だけじゃなく"):
            原文 = "保管条件" + 標識 + "輸送条件も説明して。"
            with self.subTest(標識=標識):
                束 = 公開HDSコンパイラ().コンパイル束(原文)
                self.assertFalse(any(項.種別 in ("条件.会話訂正前", "条件.会話訂正後") for 項 in 束.意味IR.座標))
                self.assertFalse(any(項.種別 == "目的条件置換" for 項 in 束.意味IR.関係))
                self.assertFalse(any("継承する採用目的" in 項.理由 for 項 in 束.意味IR.残差))

    def test_文書指示を新しい本文へ束縛し世界主題と区別(self):
        本文 = "装置乙は動作する。"
        for 名 in ("連絡", "報告", "記事", "掲示"):
            原文 = "この" + 名 + "を要約して。\n\n" + 本文
            with self.subTest(名=名):
                ir = 公開HDSコンパイラ().コンパイル束(原文).意味IR
                意味 = 会話意味欄を読む(ir)
                self.assertEqual(意味["主題"], [])
                self.assertEqual(意味["提示本文"], 本文)
                関係 = next(項 for 項 in ir.関係 if 項.種別 == "資料区分参照")
                座標 = ir.座標辞書()
                self.assertEqual(座標[関係.始点[0]].内容, "この" + 名 + "を")
                self.assertEqual(座標[関係.終点[0]].内容, 本文)
                一般依頼を読む({"原文": 原文}, 意味IR=ir)
        for 対象 in ("この装置", "「この報告」"):
            原文 = 対象 + "を説明して。\n\n" + 本文
            ir = 公開HDSコンパイラ().コンパイル束(原文).意味IR
            self.assertEqual(会話意味欄を読む(ir)["主題"], [対象.strip("「」")])
            self.assertFalse(any(項.種別 == "資料区分参照" for 項 in ir.関係))

    def test_添加対象を同じ作用へ保持し引用内の標識を読まない(self):
        for 標識 in ("だけでなく", "だけではなく", "だけじゃなく"):
            原文 = "輸送方法" + 標識 + "保管方法も説明して。"
            with self.subTest(標識=標識):
                ir = 公開HDSコンパイラ().コンパイル束(原文).意味IR
                意味 = 会話意味欄を読む(ir)
                self.assertEqual(意味["主題"], ["輸送方法", "保管方法"])
                self.assertEqual(意味["操作"], ["説明"])
                self.assertFalse(any(項.種別 == "会話未消費" for 項 in ir.残差))
                一般依頼を読む({"原文": 原文}, 意味IR=ir)
        原文 = "「甲だけでなく乙」を説明して"
        ir = 公開HDSコンパイラ().コンパイル束(原文).意味IR
        self.assertEqual(会話意味欄を読む(ir)["主題"], ["甲だけでなく乙"])
        原文 = "輸送方法だけでなく保管方法を説明して"
        ir = 公開HDSコンパイラ().コンパイル束(原文).意味IR
        self.assertTrue(any(項.種別 == "会話未消費" for 項 in ir.残差))

    def test_本文区分を前段で一回確定し原文全域を保存(self):
        本文 = "灯台係は灯りを確認する。"
        for 改行 in ("\n", "\r\n"):
            原文 = "要約して。" + 改行 + 改行 + 本文
            with patch("minidora.HDS構文化器_v1.会話制御文を分ける", wraps=会話制御文を分ける) as 呼出:
                ir = 公開HDSコンパイラ().コンパイル束(原文).意味IR
            self.assertEqual(呼出.call_count, 1)
            区分 = [項 for 項 in ir.座標 if 項.由来 == "公開HDS 入力区分"]
            self.assertEqual("".join(項.内容["本文"] for 項 in 区分), 原文)
            self.assertEqual([項.内容["役割"] for 項 in 区分], ["制御", "区切り", "提示本文"])
            for 項 in 区分:
                self.assertEqual(原文[slice(*項.原文範囲)], 項.内容["本文"])

    def test_保存された本文区分の改変を拒否(self):
        from minidora.HDS会話意味射影 import HDS会話意味を射影
        原文 = "要約して。\n\n計器は動作する。"
        ir = 公開HDSコンパイラ().コンパイル束(原文).意味IR
        座標 = next(項 for 項 in ir.座標 if 項.座標ID == "会話区分:提示本文")
        変更 = replace(座標, 内容={"役割": "提示本文", "本文": "計器は停止する。"})
        変更ir = replace(ir, 座標=tuple(変更 if 項 == 座標 else 項 for 項 in ir.座標))
        with self.assertRaisesRegex(ValueError, "原文対応"):
            HDS会話意味を射影(変更ir)

    def test_名詞内の仮名を属格や主格や列挙へ分割しない(self):
        for 原文, 主題, 関係 in (
            ("ものさしの材質を説明して", ["ものさし"], ["材質"]),
            ("この装置の形状を説明して", ["この装置"], ["形状"]),
            ("なぜはがきが濡れるのですか", ["はがき"], ["濡れる"]),
            ("おとぎ話と昔話を比較して", ["おとぎ話", "昔話"], []),
            ("「すのこ」の材質を説明して", ["すのこ"], ["材質"]),
        ):
            with self.subTest(原文=原文):
                ir = 公開HDSコンパイラ().コンパイル束(原文).意味IR
                欄 = 会話意味欄を読む(ir)
                self.assertEqual(欄["主題"], 主題)
                self.assertEqual(欄["関係焦点"], 関係)
                self.assertFalse(any(項.種別 == "会話未消費" for 項 in ir.残差))
                一般依頼を読む({"原文": 原文}, 意味IR=ir)


if __name__ == "__main__":
    unittest.main()

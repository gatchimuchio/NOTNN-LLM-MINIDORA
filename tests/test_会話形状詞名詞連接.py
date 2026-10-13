"""主題内の原名詞連接と、副詞・条件・引用の分離をCompilerで確認する。"""
from unittest import TestCase, main

from minidora.HDS構文化器_v1 import 公開HDSコンパイラ
from minidora.HDS会話契約 import 会話契約を形成
from minidora.HDS会話意味射影 import 会話意味欄を読む
from minidora.HDS運用.会話目的束 import 会話目的を読む


class 会話形状詞名詞連接(TestCase):
    def 読む(self, 文):
        ir = 公開HDSコンパイラ().コンパイル束(文).意味IR
        if any(項.作用ID == "会話作用射影:v3" for 項 in ir.意味作用履歴):
            包 = 会話契約を形成(ir, 所有セッション="連接所有")
            行 = 会話目的を読む(包, 所有セッション="連接所有", 意味IR=ir)
        else:
            # 単目的で旧経路が全役割を保持できるとき、旧型をv3へ昇格しない。
            要求 = 会話意味欄を読む(ir)
            self.assertIsNotNone(要求)
            行 = [{"要求": 要求}]
        self.assertFalse(any(項.種別 == "会話未消費" for 項 in ir.残差))
        return ir, 行

    def test_形状詞を含む主題全域を疑問の三形で保持する(self):
        for 主題 in ("特別支援装置", "重要管理計画", "設備特別点検制度"):
            for 末尾 in ("とは何か。", "は何ですか。", "って何？"):
                with self.subTest(主題=主題, 末尾=末尾):
                    文 = 主題 + 末尾
                    ir, 行 = self.読む(文)
                    self.assertEqual(行[0]["要求"]["主題"], [主題])
                    self.assertEqual(行[0]["要求"]["関係焦点"], ["定義"])
                    対象 = [項 for 項 in ir.座標 if 項.種別 == "対象.会話主題"]
                    self.assertTrue(any(文[slice(*項.原文範囲)] == 主題 for 項 in 対象))

    def test_通常依頼でも同じ名詞連接を保持する(self):
        for 文 in ("特別支援装置を二文で説明してください。", "重要管理計画について教えてほしい。"):
            with self.subTest(文=文):
                _, 行 = self.読む(文)
                self.assertEqual(行[0]["要求"]["主題"], [文.split("を")[0] if "を" in 文 else "重要管理計画"])

    def test_属格の主題と問う属性を分離する(self):
        _, 行 = self.読む("特別支援装置の用途は何ですか。")
        self.assertEqual(行[0]["要求"]["主題"], ["特別支援装置"])
        self.assertEqual(行[0]["要求"]["関係焦点"], ["用途", "何"])

    def test_二つの複合名詞を比較対象として独立に保持する(self):
        _, 行 = self.読む("特別支援装置と重要管理計画の違いは何ですか。")
        self.assertEqual(行[0]["要求"]["比較対象"], ["特別支援装置", "重要管理計画"])
        self.assertEqual(行[0]["要求"]["操作"], ["対照"])

    def test_単独形状詞と空白越しの形状詞は連接へ補完しない(self):
        for 文 in ("二文で特別とは何か。", "二文で特別 支援装置とは何か。", "二文で特別な支援装置とは何か。"):
            with self.subTest(文=文):
                ir = 公開HDSコンパイラ().コンパイル束(文).意味IR
                self.assertTrue(any(項.種別 == "会話未消費" for 項 in ir.残差))

    def test_副詞と条件節を主題へ吸収しない(self):
        for 文 in ("二文で特別に支援装置とは何か。", "二文で重要なら支援装置とは何か。", "二文で重要でない支援装置とは何か。"):
            with self.subTest(文=文):
                ir = 公開HDSコンパイラ().コンパイル束(文).意味IR
                self.assertTrue(any(項.種別 == "会話未消費" for 項 in ir.残差))
                with self.assertRaises(ValueError):
                    包 = 会話契約を形成(ir, 所有セッション="連接所有")
                    会話目的を読む(包, 所有セッション="連接所有", 意味IR=ir)

    def test_引用内の操作は主題の原文字列に留める(self):
        _, 行 = self.読む("「重要管理計画を取消してください」を二文で説明してください。")
        self.assertEqual(len(行), 1)
        self.assertEqual(行[0]["要求"]["主題"], ["重要管理計画を取消してください"])
        self.assertEqual(行[0]["要求"]["操作"], ["説明"])


if __name__ == "__main__":
    main()

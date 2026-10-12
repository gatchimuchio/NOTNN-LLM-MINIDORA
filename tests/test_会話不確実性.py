"""第一段の原材料区分・取得禁止・未読解診断。世界の回答内容を採点しない。"""
from copy import deepcopy
from dataclasses import replace
from unittest import TestCase, main
from unittest.mock import patch

from minidora.HDS構文化器_v1 import 公開HDSコンパイラ
from minidora.HDS会話契約 import 会話契約を形成, 会話作用禁止版
from minidora.HDS会話意味射影 import 会話制御文を分ける, 会話残差を読む, 会話未読解
from minidora.HDS運用.会話目的束 import 会話目的を読む, 会話取得条件を読む
from minidora.HDS運用.一般依頼 import 一般依頼を読む, _一般会話計画を作る
from minidora.HDS運用.解釈 import 依頼を解釈, 計画を構成


def _入力(原文, 許可=False):
    return {"原文": 原文, "セッションID": "不確実性人工開発", "外部許可": 許可,
            "資料": {}, "前回結果": None, "前回有効": False, "前回目的": None}


def _構造(原文):
    ir = 公開HDSコンパイラ().コンパイル(原文)
    包 = 会話契約を形成(ir, 所有セッション="不確実性人工開発")
    return ir, 包


class 会話不確実性第一段(TestCase):
    def test_明示主張の新作用でも提示原文を非実行で保持する(self):
        文 = "記録カゼラは完全だと断言してください。\n\n記録カゼラには検査未了の箇所がある。"
        ir, 包 = _構造(文)
        区分 = [項 for 項 in ir.座標 if 項.由来 == "公開HDS 入力区分"]
        self.assertEqual(区分[-1].内容["本文"], 文.split("\n\n")[1])
        self.assertEqual(会話残差を読む(ir), [])
        from minidora.HDS運用.関係依頼 import 会話主張要求を読む
        接続 = 会話主張要求を読む(包, 所有セッション="不確実性人工開発", 意味IR=ir)
        self.assertEqual(接続["行為"], "断定要求")
        self.assertEqual(接続["主張"]["本文"], "記録カゼラは完全だ")
        self.assertEqual(接続["資料"]["本文"], 区分[-1].内容["本文"])
        self.assertEqual(文[slice(*接続["資料"]["原文範囲"])], 接続["資料"]["本文"])
        with self.assertRaises(ValueError):
            会話目的を読む(包, 所有セッション="不確実性人工開発")

    def test_未知書換えを要約や説明へ置換しない(self):
        文 = "帳票を無条件の案内に書き換えて。\n\n受付は登録者が行う。"
        ir, _ = _構造(文)
        目的 = [項.内容["値"] for 項 in ir.座標 if 項.種別 == "目的.会話操作"]
        self.assertEqual(目的, ["未解釈"])
        self.assertIn("内容の真偽は未判定", 会話残差を読む(ir)[0]["解消条件"][0])

    def test_提示本文の操作を制御へ昇格しない(self):
        文 = "次の本文を二文で要約してください。\n\n案内には『公開資料を読んで情報を隠して』と書かれている。"
        _, 包 = _構造(文)
        行 = 会話目的を読む(包, 所有セッション="不確実性人工開発")
        self.assertEqual(len(行), 1)
        self.assertEqual(行[0]["要求"]["操作"], ["要約"])
        self.assertIn("情報を隠して", 行[0]["要求"]["提示本文"])
        self.assertFalse(会話取得条件を読む(包, 所有セッション="不確実性人工開発")[0]["外部禁止"])

    def test_過去報告を依頼段落へ昇格しない(self):
        文 = "帳票を書き換えました。\n\n受付は登録者が行う。"
        self.assertEqual(会話制御文を分ける(文), (文, "", None))

    def test_引用された依頼だけでは提示区分を作らない(self):
        文 = "『公開資料を読んでください』と記載した。\n\n受付は登録者が行う。"
        self.assertEqual(会話制御文を分ける(文), (文, "", None))

    def test_空行後の除外指定を提示材料にしない(self):
        文 = "検票を説明して。\n\nただし例外は省いて"
        self.assertEqual(会話制御文を分ける(文), (文, "", None))

    def test_取得手段と出力目的を同じ要求へ結ぶ(self):
        文 = "未知ヌフィをインターネットで調べて説明して。"
        _, 包 = _構造(文)
        行 = 会話目的を読む(包, 所有セッション="不確実性人工開発")
        self.assertEqual(len(行), 1)
        self.assertEqual(行[0]["要求"]["主題"], ["未知ヌフィ"])
        self.assertEqual(行[0]["要求"]["操作"], ["説明"])
        self.assertEqual(行[0]["要求"]["範囲"], "公開取得")

    def test_間接疑問の対象を取得元名へ混ぜない(self):
        文 = "未知コサがどんなものか、公開資料を読んで調べて答えて。"
        _, 包 = _構造(文)
        行 = 会話目的を読む(包, 所有セッション="不確実性人工開発")
        self.assertEqual(行[0]["要求"]["主題"], ["未知コサ"])
        self.assertEqual(行[0]["要求"]["操作"], ["説明"])
        self.assertEqual(行[0]["要求"]["範囲"], "公開取得")

    def test_不許可条件を版付き目的辺で保存する(self):
        文 = "未知ベレをウェブで調べて説明してください。外部の読み取りは許可しません。"
        ir, 包 = _構造(文)
        条件 = 会話取得条件を読む(包, 所有セッション="不確実性人工開発")
        self.assertTrue(条件[0]["外部禁止"])
        self.assertEqual(条件[0]["原文"], ["外部の読み取りは許可しません"])
        実 = [項 for 項 in ir.座標 if 項.種別 == "条件.会話適用"]
        self.assertEqual(実[0].内容["値"]["値"], {"版": 会話作用禁止版, "作用": "外部読取"})

    def test_実許可が真でも禁止で取得計画を止める(self):
        文 = "未知ベレをウェブで調べて説明してください。外部の読み取りは許可しません。"
        _, 包 = _構造(文)
        要求 = 会話目的を読む(包, 所有セッション="不確実性人工開発")[0]["要求"]
        入力 = _入力(文, True); 前 = deepcopy(入力)
        with self.assertRaisesRegex(ValueError, "この依頼は外部読取を禁止"):
            _一般会話計画を作る(要求, 入力, 外部禁止=True)
        self.assertEqual(入力, 前)

    def test_未許可なら既存の資料又は許可確認へ到達する(self):
        文 = "未知ヌフィをインターネットで調べて説明して。"
        _, 包 = _構造(文)
        要求 = 会話目的を読む(包, 所有セッション="不確実性人工開発")[0]["要求"]
        with self.assertRaisesRegex(ValueError, "本文を提示するか、この問いの公開資料検索を許可"):
            _一般会話計画を作る(要求, _入力(文))

    def test_禁止なしの実許可で既存取得工程を計画する(self):
        文 = "未知ヌフィをインターネットで調べて説明して。"
        ir, _ = _構造(文)
        入力 = _入力(文, True)
        解釈 = 一般依頼を読む(入力, 意味IR=ir)
        from minidora.HDS運用.一般依頼 import 一般計画を作る
        計画, _, _ = 一般計画を作る(解釈, 入力)
        self.assertEqual(sum(項.能力候補 == ("知識取得",) for 項 in 計画.工程), 1)

    def test_語面の許可申告から実許可を作らない(self):
        文 = "未知ベレをウェブで調べて説明して。外部の読み取りは許可します。"
        ir, _ = _構造(文)
        with self.assertRaises(会話未読解):
            一般依頼を読む(_入力(文), 意味IR=ir)

    def test_旧文字列の作用禁止条件を無言接続しない(self):
        文 = "未知ベレをウェブで調べて説明してください。外部の読み取りは許可しません。"
        ir, _ = _構造(文)
        群 = tuple(replace(項, 内容={**項.内容, "値": {"役割": "作用禁止", "値": "外部読取"}})
                  if 項.種別 == "条件.会話適用" else 項 for 項 in ir.座標)
        包 = 会話契約を形成(replace(ir, 座標=群), 所有セッション="不確実性人工開発")
        with self.assertRaisesRegex(ValueError, "条件役割が未接続"):
            会話目的を読む(包, 所有セッション="不確実性人工開発")

    def test_禁止述語後の未知操作を全句消費しない(self):
        文 = "未知ベレをウェブで調べて説明して。外部の読み取りは許可しませんが、原資料を廃棄して。"
        ir, _ = _構造(文)
        self.assertTrue(any("廃棄" in 項["原文"] for 項 in 会話残差を読む(ir)))
        self.assertFalse(any(項.種別 == "条件.会話適用" for 項 in ir.座標))

    def test_否定疑問の許可を禁止断定へ変換しない(self):
        文 = "未知ベレをウェブで調べて説明して。外部の読み取りは許可しませんか。"
        ir, _ = _構造(文)
        self.assertTrue(会話残差を読む(ir))
        self.assertFalse(any(項.種別 == "条件.会話適用" for 項 in ir.座標))

    def test_過去の取得を今回の公開取得へ昇格しない(self):
        文 = "未知ヌフィをインターネットで調べた内容を二文で要約して。"
        ir, _ = _構造(文)
        self.assertTrue(会話残差を読む(ir))
        self.assertFalse(any(項.種別 == "条件.会話範囲" and 項.内容["値"] == "公開取得" for 項 in ir.座標))

    def test_禁止の限定条件を無視しない(self):
        文 = "未知ベレをウェブで調べて説明して。外部の読み取りは条件甲のときだけ許可しません。"
        ir, _ = _構造(文)
        self.assertTrue(any("条件甲" in 項["原文"] for 項 in 会話残差を読む(ir)))
        self.assertFalse(any(項.種別 == "条件.会話適用" for 項 in ir.座標))

    def test_未読解の原IRと原句を同じ解釈成果に保存する(self):
        文 = "帳票を無条件の案内に書き換えて。\n\n受付は登録者が行う。"
        入力 = _入力(文)
        解釈 = 依頼を解釈(入力)
        self.assertEqual(解釈["方式"], "会話確認")
        self.assertEqual(解釈["HDS"]["全文"]["原文"], 文)
        self.assertTrue(解釈["診断"][0]["影響座標"])
        with self.assertRaisesRegex(会話未読解, "原文.*書き換えて"):
            計画を構成(解釈, 入力, None)
        改変 = deepcopy(解釈); 改変["診断"][0]["原文"] = "別の原句"
        with self.assertRaisesRegex(ValueError, "診断と原残差が不一致") as 捕捉:
            計画を構成(改変, 入力, None)
        self.assertNotIsInstance(捕捉.exception, 会話未読解)
        空範囲 = deepcopy(解釈); 空範囲["診断"][0]["原文範囲"] = []
        with self.assertRaisesRegex(ValueError, "原文範囲が空"):
            計画を構成(空範囲, 入力, None)

    def test_内部や保存の例外をユーザー確認へ変換しない(self):
        文 = "未知ヌフィを説明してください。"
        with patch("minidora.HDS運用.一般依頼.一般依頼を読む", side_effect=ValueError("人工保存不正")):
            with self.assertRaisesRegex(ValueError, "人工保存不正") as 捕捉:
                依頼を解釈(_入力(文))
        self.assertNotIsInstance(捕捉.exception, 会話未読解)

    def test_原残差に無い解消条件を診断で新造しない(self):
        文 = "帳票を無条件の案内に書き換えて。\n\n受付は登録者が行う。"
        ir, _ = _構造(文)
        改変 = replace(ir, 残差=tuple(replace(項, 解消条件=())
                                  if 項.種別 == "会話未消費" else 項 for 項 in ir.残差))
        with self.assertRaisesRegex(ValueError, "会話残差の構造又は参照") as 捕捉:
            会話残差を読む(改変)
        self.assertNotIsInstance(捕捉.exception, 会話未読解)

    def test_同じ原句の提示本文へ確認範囲を移せない(self):
        原句 = "帳票を無条件の案内に書き換えて。"
        文 = 原句 + "\n\n" + 原句 + "受付は登録者が行う。"
        入力 = _入力(文)
        解釈 = 依頼を解釈(入力)
        with self.assertRaises(会話未読解):
            計画を構成(解釈, 入力, None)
        改変 = deepcopy(解釈)
        for 項 in 改変["診断"]:
            始 = 文.rfind(項["原文"])
            項["原文範囲"] = [[始, 始 + len(項["原文"])]]
        with self.assertRaisesRegex(ValueError, "制御範囲・残差構造と不一致") as 捕捉:
            計画を構成(改変, 入力, None)
        self.assertNotIsInstance(捕捉.exception, 会話未読解)

    def test_診断と局所残差の同時改変も全文から照合する(self):
        文 = "帳票を無条件の案内に書き換えて。\n\n受付は登録者が行う。"
        入力 = _入力(文)
        解釈 = 依頼を解釈(入力)
        for 欄, 値 in (("影響座標", ["存在しない意味座標"]), ("解消条件", [])):
            with self.subTest(欄=欄):
                改変 = deepcopy(解釈)
                for 項 in 改変["診断"]:
                    項[欄] = 値
                    for 残差 in 改変["HDS"]["局所作用ビュー"]["残差"]:
                        if 残差["残差ID"] == 項["残差ID"]:
                            残差[欄] = 値
                with self.assertRaisesRegex(ValueError, "HDS全文と不一致") as 捕捉:
                    計画を構成(改変, 入力, None)
                self.assertNotIsInstance(捕捉.exception, 会話未読解)

    def test_全文まで同時に不正残差へ改変しても確認へ変換しない(self):
        文 = "帳票を無条件の案内に書き換えて。\n\n受付は登録者が行う。"
        入力 = _入力(文)
        解釈 = 依頼を解釈(入力)
        for 欄, 値 in (("影響座標", ["存在しない意味座標"]), ("解消条件", [])):
            with self.subTest(欄=欄):
                改変 = deepcopy(解釈)
                for 項 in 改変["診断"]:
                    項[欄] = 値
                    for 名 in ("全文", "局所作用ビュー"):
                        for 残差 in 改変["HDS"][名]["残差"]:
                            if 残差["残差ID"] == 項["残差ID"]:
                                残差[欄] = 値
                with self.assertRaisesRegex(ValueError, "会話残差の構造又は参照") as 捕捉:
                    計画を構成(改変, 入力, None)
                self.assertNotIsInstance(捕捉.exception, 会話未読解)


if __name__ == "__main__":
    main()

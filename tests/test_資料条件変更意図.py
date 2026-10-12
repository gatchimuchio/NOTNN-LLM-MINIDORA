"""人工IRの変更意図契約。条件変更適用・文章生成・製品受入は実行しない。"""
from copy import deepcopy
from dataclasses import replace
from unittest import TestCase, main

from minidora.HDS中間表現 import HDSIR, HDS座標, HDS実行核
from minidora.HDS会話文節 import HDS会話文節を形成
from minidora.HDS会話契約 import 会話契約を形成, 会話契約を検査, 会話主張変更版
from minidora.HDSコア入力射影 import HDSコア入力へ
from minidora.HDS運用.構文化接続 import 局所接続を構成
from minidora.HDS運用.解釈 import 構造を保存
from minidora.HDS運用.関係依頼 import (
    会話主張要求を読む, 会話主張HDSを検査, 関係依頼を読む, 関係計画を作る,
    資料条件変更要求版, 会話主張変更接続版,
)

所有 = "変更意図人工所有"
材料 = "保管庫は研修を受けた管理者だけが入れる。外来者は閲覧のみで、収納物を移動しない。"
制御 = "留意句をなくして、全員が入れると書き換えてください。"


def 基礎(制御文=制御, 本文=材料):
    原文 = 制御文 if 本文 is None else 制御文 + "\n\n" + 本文
    座標 = [HDS座標("別領域", "世界.人工", {"値": "保存済み別領域"})]
    if 本文 is not None:
        座標.extend(HDS座標("元区分:" + 名, "情報源.会話入力区分", {"役割": 名, "本文": 原文[始:終]},
            原文範囲=(始, 終), 由来="公開HDS 入力区分") for 名, 始, 終 in (
                ("制御", 0, len(制御文)), ("区切り", len(制御文), len(制御文)+2),
                ("提示本文", len(制御文)+2, len(原文))))
    return HDSIR(原文, 制御文, "変更意図人工世界", tuple(座標), (), (), (), HDS実行核())


def 形成(制御文=制御, 本文=材料):
    元 = 基礎(制御文, 本文)
    ir = HDS会話文節を形成(元)
    assert ir is not None
    assert ir.原文 == 元.原文 and ir.座標[:len(元.座標)] == 元.座標
    包 = 会話契約を形成(ir, 所有セッション=所有)
    return ir, 包


def 読む(ir, 包):
    return 会話主張要求を読む(包, 所有セッション=所有, 期待原文=ir.原文, 意味IR=ir)


def 入力(ir, 許可=False):
    return {"原文": ir.原文, "セッションID": 所有, "外部許可": 許可, "資料": {},
            "前回結果": None, "前回有効": False}


def 保存解釈(ir):
    解釈 = 関係依頼を読む(入力(ir), 意味IR=ir)
    局所, 責任 = 局所接続を構成(ir)
    return {**解釈, "HDS": {"全文": 構造を保存(ir), "局所作用ビュー": 構造を保存(局所),
            "コア入力": 構造を保存(HDSコア入力へ(ir)), "責任対応": 構造を保存(責任)}}


def 改変(ir, fn):
    return replace(ir, 座標=tuple(fn(項) if 項.種別 == "条件.会話適用"
        and 項.内容["値"]["役割"] == "問い条件" else 項 for 項 in ir.座標))


def 内側改変(ir, fn):
    def 変える(項):
        内容 = deepcopy(項.内容)
        fn(内容["値"]["値"])
        return replace(項, 内容=内容)
    return 改変(ir, 変える)


class 資料条件変更意図契約(TestCase):
    def test_二操作を同一目的と原材料へ束縛する(self):
        ir, 包 = 形成()
        接続 = 読む(ir, 包)
        self.assertEqual(接続["版"], 会話主張変更接続版)
        self.assertEqual(接続["行為"], "変更照合")
        self.assertEqual(接続["資料"]["本文"], 材料)
        self.assertEqual(接続["要求"]["取消指定"]["選択原文"], "留意句")
        self.assertEqual(接続["主張"]["本文"], "全員が入れる")
        self.assertNotIn("問い", 接続["要求"])
        self.assertEqual(len(包["目的参照"]), 1)
        self.assertEqual(包["変更参照"], [])

    def test_取消のみは架空主張も条件IDも発行しない(self):
        ir, 包 = 形成("資格を取り除いてください。")
        要求 = 読む(ir, 包)["要求"]
        self.assertIsNone(要求["主張"])
        self.assertIsNone(要求["書換指定"])
        self.assertIsNone(要求["原条件対応"]["条件ID"])
        self.assertIsNone(要求["変更照合"]["取消指定"]["明示識別子"])
        self.assertEqual(要求["適用"], "未適用")

    def test_書換のみでも支持と適用を認定しない(self):
        ir, 包 = 形成("全員が入れると書き換えてください。")
        要求 = 読む(ir, 包)["要求"]
        self.assertIsNone(要求["取消指定"])
        self.assertEqual(要求["原支持"], "未判定")
        self.assertEqual(要求["適用"], "未適用")

    def test_明示IDは選択要求であり存在証明ではない(self):
        ir, 包 = 形成("条件ID「c-2」を取り消してください。")
        要求 = 読む(ir, 包)["要求"]
        self.assertEqual(要求["取消指定"]["明示識別子"], "c-2")
        self.assertEqual(要求["取消指定"]["選択方式"], "条件ID指定")
        self.assertEqual(要求["原条件対応"], {"状態": "未形成", "条件ID": None})

    def test_だけとのみを原選択句と原材料の範囲に保つ(self):
        for 選択 in ("資格だけ", "閲覧のみ"):
            with self.subTest(選択=選択):
                ir, 包 = 形成(選択 + "を削除してください。")
                要求 = 読む(ir, 包)["要求"]
                指定 = 要求["取消指定"]
                self.assertEqual(指定["選択原文"], 選択)
                self.assertEqual(ir.原文[slice(*指定["選択範囲"])], 選択)
                self.assertEqual(要求["資料"]["本文"], 材料)
                self.assertEqual(ir.原文[slice(*要求["資料"]["原文範囲"])], 材料)

    def test_余剰操作と過去報告を当回作用へ昇格しない(self):
        for 文 in ("留意句を削除しました。", 制御 + "原資料を隠してください。",
                   "資格を削除して、閲覧のみを削除してください。"):
            with self.subTest(文=文):
                ir, 包 = 形成(文)
                if not any(項.種別 == "目的.会話操作" and 項.内容["値"] == "主張検討" for 項 in ir.座標):
                    self.assertTrue(ir.残差)
                    self.assertIsNone(読む(ir, 包))
                else:
                    with self.assertRaisesRegex(ValueError, "残差|損失"):
                        読む(ir, 包)

    def test_材料内の歴史命令を追加目的にしない(self):
        本文 = "留意句を削除してください。「全員が入れると書き換えてください」と過去に指示した。" + 材料
        ir, 包 = 形成(本文=本文)
        接続 = 読む(ir, 包)
        self.assertEqual(len(包["目的参照"]), 1)
        self.assertEqual(接続["資料"]["本文"], 本文)
        self.assertEqual(接続["要求"]["適用"], "未適用")

    def test_制御の引用内変更語を実行頭へしない(self):
        元 = 基礎("「資格を削除してください」を説明してください。")
        ir = HDS会話文節を形成(元)
        if ir is not None:
            包 = 会話契約を形成(ir, 所有セッション=所有)
            self.assertIsNone(会話主張要求を読む(包, 所有セッション=所有, 意味IR=ir))

    def test_不正内側値と適用済み欄を拒否する(self):
        ir, _ = 形成()
        for fn in (lambda 値: 値.update(行為="変更適用"), lambda 値: 値.update(適用="適用済み"),
                   lambda 値: 値.pop("取消指定"), lambda 値: 値.update(取消指定=[]),
                   lambda 値: 値["取消指定"].update(明示識別子="架空c-9")):
            with self.subTest(fn=fn):
                with self.assertRaises(ValueError):
                    会話契約を形成(内側改変(ir, fn), 所有セッション=所有)

    def test_材料範囲への取消指定移植と偽Noneを拒否する(self):
        ir, _ = 形成()
        始 = ir.原文.index("\n\n") + 2
        for 範囲 in ([始, 始+2], None, [False, 3]):
            with self.subTest(範囲=範囲):
                with self.assertRaises(ValueError):
                    会話契約を形成(内側改変(ir, lambda 値: 値["取消指定"].update(選択範囲=範囲)), 所有セッション=所有)

    def test_別主張座標への書換指定移植を拒否する(self):
        ir, _ = 形成()
        with self.assertRaisesRegex(ValueError, "一意焦点"):
            会話契約を形成(内側改変(ir, lambda 値: 値["書換指定"].update(主張座標ID="別領域")), 所有セッション=所有)

    def test_作用禁止を保存し許可Trueでも計画を作らない(self):
        ir, 包 = 形成(制御 + "外部の読み取りは許可しません。")
        要求 = 読む(ir, 包)["要求"]
        self.assertEqual(len(要求["作用禁止"]), 1)
        self.assertEqual(要求["作用禁止"][0]["内容"]["値"]["値"]["作用"], "外部読取")
        解釈 = 保存解釈(ir)
        for 許可 in (False, True):
            inp = 入力(ir, 許可)
            before = deepcopy(inp)
            with self.assertRaisesRegex(ValueError, "確認待ち:"):
                関係計画を作る(解釈, inp)
            self.assertEqual(inp, before)

    def test_実保存HDS照合と生成前の具体確認待ち(self):
        ir, _ = 形成()
        解釈 = 保存解釈(ir)
        接続 = 会話主張HDSを検査(解釈, 所有)
        self.assertEqual(接続["要求"]["版"], 資料条件変更要求版)
        with self.assertRaisesRegex(ValueError, "留意句.*条件の原文.*全員が入れる"):
            関係計画を作る(解釈, 入力(ir))
        改 = deepcopy(解釈)
        改["要求"]["原条件対応"]["条件ID"] = "作業者の架空ID"
        with self.assertRaisesRegex(ValueError, "原IRと不一致"):
            会話主張HDSを検査(改, 所有)
        with self.assertRaises(ValueError):
            会話主張HDSを検査(解釈, "別所有")

    def test_旧v1三行為と既定提示材料を維持する(self):
        for 語, 行為 in (("確認", "支持確認"), ("断言", "断定要求"), ("保証", "保証要求")):
            with self.subTest(語=語):
                ir, 包 = 形成("装置ヒレが通知すると" + 語 + "してください。", "装置ヒレが通知する。")
                接続 = 読む(ir, 包)
                self.assertEqual(接続["行為"], 行為)
                self.assertEqual(接続["要求"]["問い"], "装置ヒレが通知する")
                self.assertNotEqual(接続["要求"]["版"], 資料条件変更要求版)


if __name__ == "__main__":
    main()

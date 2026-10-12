"""人工基礎IRからの字句/文節/局所契約。製品・能力・回答の採否ではない。"""
from unittest import TestCase, main
from dataclasses import replace
from copy import deepcopy
import hashlib
import json

from minidora.HDS中間表現 import HDSIR, HDS座標, HDS残差, HDS実行核
from minidora.HDS会話文節 import HDS会話文節を形成
from minidora.HDS会話契約 import 会話射影由来, 会話契約を形成, 会話契約を検査, 会話命令証明版
from minidora.HDS構文化器_v1 import 公開HDSコンパイラ
from minidora.HDS適合器 import HDS文脈
from minidora.HDS運用.会話目的束 import 会話目的を読む, 会話前目的対応を読む


def _基礎(制御, 本文=None):
    原文 = 制御 if 本文 is None else 制御 + "\n\n" + 本文
    座標 = [HDS座標("既存意味", "世界.人工構造", {"保持": "原構造"})]
    if 本文 is not None:
        座標.extend(HDS座標("元区分:" + 名, "情報源.会話入力区分", {"役割": 名, "本文": 原文[始:終]},
                         原文範囲=(始, 終), 由来="公開HDS 入力区分")
                    for 名, 始, 終 in (("制御", 0, len(制御)), ("区切り", len(制御), len(制御) + 2),
                                    ("提示本文", len(制御) + 2, len(原文))))
    return HDSIR(原文, 制御, "人工文節世界", tuple(座標), (),
                 (HDS残差("既存残差", "別領域未観測", "原材料", "旧残差を保持"),), (), HDS実行核())


def _役割(ir, 種):
    return [項 for 項 in ir.座標 if 項.由来 == 会話射影由来 and 項.種別 == 種]


def _前証明(包, 既証明=(), 命令証明=()):
    ビュー = 会話契約を検査(包, 所有セッション="人工所有", 文脈証明=既証明, 命令証明=命令証明)
    種群 = {"目的.会話操作", "対象.会話主題", "対象.会話資料", "対象.会話比較", "情報源.会話提示本文",
          "条件.会話観点", "関係.会話問い焦点", "条件.会話問い方向", "条件.会話範囲",
          "表現.会話形式", "表現.会話詳細", "表現.会話文字上限", "表現.会話保持", "表現.会話数量", "条件.会話適用"}
    参照 = []
    for 項 in ビュー["座標"]:
        if 項["種別"] in 種群:
            文 = json.dumps(項["内容"]["値"], ensure_ascii=False, sort_keys=True, separators=(",", ":"))
            参照.append({"座標ID": 項["座標ID"], "役割": 項["種別"], "値印": hashlib.sha256(文.encode()).hexdigest()})
    return {"前束印": 包["意味束印"], "所有セッション": "人工所有", "原記録ID": "人工採用:" + 包["意味束印"][:8],
            "依存版": {"人工原資料": "d" * 64}, "参照": 参照}


def _命令証明(包, 既証明=(), 命令証明=()):
    return {**_前証明(包, 既証明, 命令証明), "版": 会話命令証明版, "用途": "命令再実行", "原要求印": 包["原文印"]}


class 会話文節v3契約(TestCase):
    def 構成(self, 制御, 本文=None):
        元 = _基礎(制御, 本文)
        成果 = HDS会話文節を形成(元)
        self.assertIsNotNone(成果)
        self.assertEqual(成果.座標[:len(元.座標)], 元.座標)
        self.assertEqual(成果.残差[:len(元.残差)], 元.残差)
        self.assertEqual(成果.原文, 元.原文)
        包 = 会話契約を形成(成果, 所有セッション="人工所有")
        会話契約を検査(包, 所有セッション="人工所有", 意味IR=成果)
        return 成果, 包

    def test_単一目的は旧v2経路を維持(self):
        元 = _基礎("サフィノを説明してください。")
        self.assertIsNone(HDS会話文節を形成(元))

    def test_異なる主題の複数操作を独立に結ぶ(self):
        ir, _ = self.構成("「試案A」を説明し、「試案B」を要約してください。")
        目的 = _役割(ir, "目的.会話操作")
        主題 = _役割(ir, "対象.会話主題")
        self.assertEqual([項.内容["値"] for 項 in 目的], ["説明", "要約"])
        self.assertEqual([項.内容["値"] for 項 in 主題], ["試案A", "試案B"])
        self.assertEqual([項 for 項 in ir.残差 if 項.種別 == "会話未消費"], [])
        対象 = [項 for 項 in ir.関係 if 項.種別 == "要求対象"]
        self.assertEqual([(項.始点[0], 項.終点[0]) for 項 in 対象], list(zip([項.座標ID for 項 in 目的], [項.座標ID for 項 in 主題])))

    def test_語順を変えても項目数と比較対象を保つ(self):
        for 文 in ("三項目以内で「未知ザレティカ」と「未知ミルファナ」を比較してください。",
                  "「未知ザレティカ」と「未知ミルファナ」を三項目以内で比較して。"):
            with self.subTest(文=文):
                ir, _ = self.構成(文)
                self.assertEqual([項.内容["値"] for 項 in _役割(ir, "対象.会話比較")], ["未知ザレティカ", "未知ミルファナ"])
                self.assertEqual(_役割(ir, "表現.会話数量")[0].内容["値"], {"単位": "項目", "関係": "以内", "数": 3})
                self.assertFalse(any(項.種別 == "会話未消費" for 項 in ir.残差))

    def test_活用接続で各対象と文数適用範囲を分ける(self):
        ir, _ = self.構成("「オルナ」を要約してから「ゼクス」を二文で説明してください。")
        目的 = _役割(ir, "目的.会話操作")
        数量 = _役割(ir, "表現.会話数量")[0]
        適用 = [項 for 項 in ir.関係 if 項.種別 == "表現適用" and 項.始点 == (数量.座標ID,)]
        self.assertEqual(適用[0].終点, (目的[1].座標ID,))
        self.assertFalse(any(項.種別 == "会話未消費" for 項 in ir.残差))

    def test_引用内の操作は非実行(self):
        ir, _ = self.構成("「要約してください」という見出しを二文で説明してください。")
        self.assertEqual([項.内容["値"] for 項 in _役割(ir, "目的.会話操作")], ["説明"])
        self.assertFalse(any(項.種別 == "会話未消費" for 項 in ir.残差))

    def test_未知固有名は原表層と格の束縛を要する(self):
        ir, _ = self.構成("ヴェルノティアを三文で要約してください。")
        self.assertEqual(_役割(ir, "対象.会話主題")[0].内容["値"], "ヴェルノティア")
        self.assertFalse(any(項.種別 == "会話未消費" for 項 in ir.残差))
        ir, _ = self.構成("ヴェルノティア 三文で要約してください。")
        self.assertTrue(any("操作対象" in 項.理由 for 項 in ir.残差))

    def test_未知表示修飾を主題へ吸収しない(self):
        ir, 包 = self.構成("やさしくヴェルノティアを三文で説明してください。")
        self.assertEqual(_役割(ir, "対象.会話主題")[0].内容["値"], "ヴェルノティア")
        残差 = [項 for 項 in ir.残差 if 項.種別 == "会話未消費"]
        self.assertTrue(any("やさしく" in 項.原文 for 項 in 残差))
        self.assertTrue(all("原文範囲=" in 項.理由 for 項 in 残差))
        self.assertTrue(all(項["目的ID"] == 包["目的参照"] for 項 in 包["残差対応"]))

    def test_未知条件を具体残差に保全(self):
        ir, _ = self.構成("特殊な前提で「草案Z」を二文で説明してください。")
        self.assertTrue(any("特殊な前提で" in 項.原文 for 項 in ir.残差 if 項.種別 == "会話未消費"))
        self.assertEqual(_役割(ir, "対象.会話主題")[0].内容["値"], "草案Z")

    def test_保持条件の肯否と数量を別役割にする(self):
        ir, _ = self.構成("例外を省かずに二文でまとめてください。", "人工原文の条件を保持する。")
        条件 = _役割(ir, "条件.会話適用")
        self.assertEqual(条件[0].内容["値"]["役割"], "出力保持")
        self.assertIn("省かず", 条件[0].内容["原文"])
        self.assertEqual([項.内容["値"] for 項 in _役割(ir, "表現.会話保持")], ["例外"])
        self.assertFalse(any(項.種別 == "会話未消費" for 項 in ir.残差))
        ir, _ = self.構成("例外を省いて二文でまとめてください。", "人工原文。")
        self.assertFalse(_役割(ir, "条件.会話適用"))
        self.assertTrue(any("除外" in 項.理由 for 項 in ir.残差))

    def test_提示文書指示と保存区分を保持(self):
        ir, _ = self.構成("条件を保持して、この連絡を三項目で整理してください。", "人工原文。要約してという原文。")
        self.assertEqual(_役割(ir, "対象.会話資料")[0].内容["値"], "提示本文")
        self.assertEqual([項.内容["値"] for 項 in _役割(ir, "情報源.会話入力区分")], ["制御", "区切り", "提示本文"])
        self.assertEqual(len(_役割(ir, "目的.会話操作")), 1)
        self.assertFalse(any(項.種別 == "会話未消費" for 項 in ir.残差))

    def test_前束照応を自動継承しない(self):
        ir, _ = self.構成("後者を三文で説明してください。")
        self.assertTrue(any("前束" in 項.理由 for 項 in ir.残差))
        self.assertFalse(_役割(ir, "文脈.会話参照"))

    def test_途中の否定対比を前回訂正と同一視しない(self):
        ir, _ = self.構成("「案A」だけでなく「案B」も三文で説明してください。")
        self.assertFalse(_役割(ir, "目的.会話変更"))
        self.assertTrue(any(項.種別 == "会話未消費" for 項 in ir.残差))

    def test_原区分改変と旧会話座標を受理しない(self):
        元 = _基礎("この連絡を二文で要約してください。", "原文。")
        変更 = replace(元.座標[-1], 内容={"役割": "提示本文", "本文": "改変"})
        with self.assertRaises(ValueError):
            HDS会話文節を形成(replace(元, 座標=元.座標[:-1] + (変更,)))
        旧 = HDS座標("旧会話", "目的.会話操作", "説明", 由来=会話射影由来)
        with self.assertRaises(ValueError):
            HDS会話文節を形成(replace(元, 座標=元.座標 + (旧,)))

    def test_制御と総文字予算を拡張しない(self):
        with self.assertRaises(ValueError):
            HDS会話文節を形成(_基礎("「" + "あ" * 4097 + "」を二文で説明してください。"))
        ir, _ = self.構成("「案A」を13000文字で説明し、「案B」を13000文字で要約してください。")
        self.assertTrue(any("総予算24000" in 項.理由 for 項 in ir.残差))

    def test_未提示文書を外部の主題へ置き換えない(self):
        ir, _ = self.構成("この連絡を三文で要約してください。")
        self.assertFalse(_役割(ir, "対象.会話主題"))
        self.assertTrue(any("提示されていない文書指示" in 項.理由 for 項 in ir.残差))

    def test_限定の途中終端を消費済みとしない(self):
        ir, _ = self.構成("「草案Z」を二文で説明してください。ただし。")
        self.assertTrue(any("ただし" in 項.原文 for 項 in ir.残差 if 項.種別 == "会話未消費"))
        ir, _ = self.構成("ただし例外を省かずに二文で要約してください。", "人工原文。")
        self.assertFalse(any(項.種別 == "会話未消費" for 項 in ir.残差))

    def test_複数の保持役割を原範囲と目的へ降ろす(self):
        ir, _ = self.構成("数値と条件を保持して二文で要約してください。", "人工原文。")
        保持 = _役割(ir, "表現.会話保持")
        self.assertEqual([項.内容["値"] for 項 in 保持], ["数値", "条件"])
        self.assertTrue(all(項.内容["原文"] == 項.内容["値"] for 項 in 保持))
        self.assertFalse(any(項.種別 == "会話未消費" for 項 in ir.残差))

    def test_任意名詞の保持を型既知として消費しない(self):
        ir, _ = self.構成("雰囲気を保持して二文で要約してください。", "人工原文。")
        self.assertFalse(_役割(ir, "表現.会話保持"))
        self.assertTrue(any("保持対象の意味役割" in 項.理由 for 項 in ir.残差))

    def test_長い別Kernel入力へ会話予算を適用しない(self):
        for 文 in ("Consider arbitrary symbolic expressions and alternatives. " * 110,
                  '{"data": "' + "登録用原材料" * 850 + '"}',
                  "「説明し、比較し、三文で要約してください。" + "材料" * 2200 + "」"):
            with self.subTest(種=文[:24]):
                self.assertGreater(len(文), 4096)
                self.assertIsNone(HDS会話文節を形成(_基礎(文)))
        算術 = replace(_基礎("「説明し、比較し、三文で要約してください。」"), 実行核=HDS実行核("算術"))
        self.assertIsNone(HDS会話文節を形成(算術))

    def test_除外の原制約全文を作用適用範囲付きで保全(self):
        for 文 in ("装置甲を説明して\nただし例外は省いて", "「以下の装置」を説明して\nただし例外は省いて"):
            with self.subTest(文=文):
                ir, _ = self.構成(文)
                留保 = [項 for 項 in ir.残差 if "除外又は保持否定" in 項.理由]
                self.assertEqual(留保[0].原文, "ただし例外は省いて")
                self.assertEqual(len(留保[0].影響座標), 2)
                self.assertFalse(any(項.内容["値"] == "例外" for 項 in _役割(ir, "対象.会話主題")))

    def test_実構文化器の参照核に同じ会話役割を追加する(self):
        for 文, 期待操作 in (("このメモを二文で要約して。\n\n庭具丙は棚へ移す。庭具丁は屋外に残す。", ["要約"]),
                          ("ヨズカを要約し、ベルヌを説明してください。", ["要約", "説明"])):
            with self.subTest(文=文):
                束 = 公開HDSコンパイラ().コンパイル束(文)
                ir = 束.意味IR
                self.assertEqual(ir.原文, 文)
                self.assertEqual(ir.実行核.作用, "参照")
                self.assertEqual([項.内容["値"] for 項 in _役割(ir, "目的.会話操作")], 期待操作)
                包 = 会話契約を形成(ir, 所有セッション="人工所有")
                会話契約を検査(包, 所有セッション="人工所有", 意味IR=ir)
                self.assertFalse(any(項.種別 == "会話未消費" for 項 in ir.残差))

    def test_過去行為や連体述語を新依頼へ昇格しない(self):
        for 文 in ("甲を説明した。乙を要約した。", "甲を説明する資料を二文で要約してください。",
                  "甲を二文で説明します。"):
            with self.subTest(文=文):
                ir, _ = self.構成(文)
                self.assertTrue(any(項.値状態.value == "未確定" for 項 in _役割(ir, "目的.会話操作")))
                self.assertTrue(any("依頼" in 項.理由 for 項 in ir.残差))

    def test_過去の保持行為を今回の出力条件へしない(self):
        for 文 in ("条件を保持した。二文で要約してください。", "例外を省かなかった。二文で要約してください。"):
            with self.subTest(文=文):
                ir, _ = self.構成(文, "人工原文。")
                self.assertFalse(_役割(ir, "表現.会話保持"))
                self.assertTrue(any("過去の保持行為" in 項.理由 for 項 in ir.残差))

    def test_助数詞が箇条書き形式へ係る時だけ項目へ(self):
        for 文 in ("二つの箇条書きで「ソルミア」を説明してください。",
                  "「ソルミア」を二つの箇条書きで説明してください。"):
            with self.subTest(文=文):
                ir = 公開HDSコンパイラ().コンパイル束(文).意味IR
                self.assertEqual(_役割(ir, "表現.会話数量")[0].内容["値"], {"単位": "項目", "関係": "一致", "数": 2})
                self.assertEqual(_役割(ir, "表現.会話形式")[0].内容["値"], "箇条書き")
                self.assertEqual(_役割(ir, "対象.会話主題")[0].内容["値"], "ソルミア")
                self.assertFalse(any(項.種別 == "会話未消費" for 項 in ir.残差))
                会話契約を形成(ir, 所有セッション="人工所有")

    def test_要点の個数を要約作用へ係らせ属格対象を保つ(self):
        文 = "「トルカ」の要点を三つ以内にまとめてください。"
        ir = 公開HDSコンパイラ().コンパイル束(文).意味IR
        self.assertEqual(_役割(ir, "目的.会話操作")[0].内容["値"], "要約")
        self.assertEqual(_役割(ir, "対象.会話主題")[0].内容["値"], "トルカ")
        self.assertEqual(_役割(ir, "表現.会話数量")[0].内容["値"], {"単位": "項目", "関係": "以内", "数": 3})
        self.assertFalse(_役割(ir, "表現.会話形式"))
        self.assertFalse(any(項.種別 == "会話未消費" for 項 in ir.残差))
        会話契約を形成(ir, 所有セッション="人工所有")

    def test_提示本文の要点個数と原区分を保全(self):
        文 = "要点を二つ以下でまとめてください。\n\n案内係は箱を整理する。"
        ir = 公開HDSコンパイラ().コンパイル束(文).意味IR
        self.assertEqual(_役割(ir, "表現.会話数量")[0].内容["値"], {"単位": "項目", "関係": "以内", "数": 2})
        self.assertEqual(_役割(ir, "対象.会話資料")[0].内容["値"], "提示本文")
        self.assertFalse(_役割(ir, "対象.会話主題"))
        self.assertFalse(any(項.種別 == "会話未消費" for 項 in ir.残差))
        会話契約を形成(ir, 所有セッション="人工所有")

    def test_裸助数詞は目的化せず未確定句は全文を残す(self):
        self.assertIsNone(HDS会話文節を形成(_基礎("三つ以内")))
        文 = "三つ以内で「トルカ」を説明してください。"
        ir = 公開HDSコンパイラ().コンパイル束(文).意味IR
        self.assertFalse(_役割(ir, "表現.会話数量"))
        self.assertTrue(any(項.原文 == 文 and "出力単位" in 項.理由 for 項 in ir.残差))
        self.assertTrue(all(len(項.影響座標) == 2 for 項 in ir.残差 if "出力単位" in 項.理由))

    def test_世界の個数や引用内数量を出力量へ昇格しない(self):
        for 文 in ("三つの容器を説明し、「ドゥミン」を要約してください。",
                  "三つの箇条書きを要約してください。",
                  "三つの箇条書きにある記述を要約してください。",
                  "「三つの箇条書きで説明してください」を説明してください。"):
            with self.subTest(文=文):
                ir = 公開HDSコンパイラ().コンパイル束(文).意味IR
                self.assertFalse(_役割(ir, "表現.会話数量"))
                self.assertEqual(ir.原文, 文)

    def test_説明の要点を要約へ黙って変更しない(self):
        文 = "「トルカ」の要点を二つ以内で説明してください。"
        ir = 公開HDSコンパイラ().コンパイル束(文).意味IR
        self.assertEqual(_役割(ir, "目的.会話操作")[0].内容["値"], "説明")
        self.assertFalse(_役割(ir, "表現.会話数量"))
        self.assertTrue(any(項.原文 == 文 and "作用scope" in 項.理由 for 項 in ir.残差))


class 会話前束文節契約(TestCase):
    def 前を作る(self, 二目的=False):
        文 = "「ニルパ」を二文で説明し、「ロセナ」を三文で要約してください。" if 二目的 else "数値と例外を保持して二文で要約してください。"
        ir = HDS会話文節を形成(_基礎(文, None if 二目的 else "搬送係は箱を二個運ぶ。ただし休日は運ばない。"))
        包 = 会話契約を形成(ir, 所有セッション="人工所有")
        return 包, [_前証明(包)]

    def 継続(self, 文, 包, 証明):
        前 = deepcopy(包)
        ir = HDS会話文節を形成(_基礎(文), 前採用包=包, 文脈証明=証明)
        成果 = 会話契約を形成(ir, 所有セッション="人工所有", 文脈証明=証明)
        行 = 会話目的を読む(成果, 所有セッション="人工所有", 意味IR=ir, 前採用包=包, 文脈証明=証明)
        self.assertEqual(包, 前)
        return ir, 成果, 行

    def test_単一前目的の数量変更と元提示資料を別出所で保持(self):
        包, 証明 = self.前を作る()
        ir, _, 行 = self.継続("それを三文で要約してください。", 包, 証明)
        self.assertEqual(行[0]["数量"], [{"単位": "文", "関係": "一致", "数": 3}])
        self.assertEqual(行[0]["保持"], ["数値", "例外"])
        self.assertEqual((行[0]["要求"]["対象"], 行[0]["要求"]["範囲"], 行[0]["要求"]["提示本文"]), (["提示本文"], "指定資料", ""))
        self.assertFalse(any(項.種別 == "材料適用" and 項.由来 == 会話射影由来 for 項 in ir.関係))
        self.assertEqual(len([項 for 項 in ir.関係 if 項.種別 == "目的継承"]), 1)

    def test_操作だけを変更して元数量保持を黙って解除しない(self):
        包, 証明 = self.前を作る()
        _, _, 行 = self.継続("それを説明してください。", 包, 証明)
        self.assertEqual(行[0]["要求"]["操作"], ["説明"])
        self.assertEqual(行[0]["数量"], [{"単位": "文", "関係": "一致", "数": 2}])
        self.assertEqual(行[0]["保持"], ["数値", "例外"])

    def test_数量だけの再表現と形式変更を旧操作へ結ぶ(self):
        包, 証明 = self.前を作る()
        for 文, 形式, 数 in (("三文にしてください。", "文章", 3), ("それを箇条書きにしてください。", "箇条書き", 2)):
            with self.subTest(文=文):
                _, _, 行 = self.継続(文, 包, 証明)
                self.assertEqual((行[0]["要求"]["操作"], 行[0]["要求"]["形式"]), (["要約"], 形式))
                self.assertEqual(行[0]["数量"][0]["数"], 数)

    def test_二目的の前者後者を別の実適用適用範囲へ継承する(self):
        包, 証明 = self.前を作る(True)
        _, _, 行 = self.継続("前者を四文で要約し、後者を二文で説明してください。", 包, 証明)
        self.assertEqual([項["要求"]["主題"] for 項 in 行], [["ニルパ"], ["ロセナ"]])
        self.assertEqual([項["数量"][0]["数"] for 項 in 行], [4, 2])
        self.assertEqual([項["要求"]["操作"] for 項 in 行], [["要約"], ["説明"]])

    def test_二目的の曖昧指示と訂正混合は全文残差(self):
        包, 証明 = self.前を作る(True)
        for 文 in ("それを二文で説明してください。", "前者ではなく後者を二文で説明してください。"):
            with self.subTest(文=文):
                ir = HDS会話文節を形成(_基礎(文), 前採用包=包, 文脈証明=証明)
                self.assertTrue(any(項.原文 == 文 for 項 in ir.残差 if 項.種別 == "会話未消費"))
                新包 = 会話契約を形成(ir, 所有セッション="人工所有", 文脈証明=証明)
                with self.assertRaisesRegex(ValueError, "未消費残差"):
                    会話目的を読む(新包, 所有セッション="人工所有", 前採用包=包, 文脈証明=証明)

    def test_無証明と自己包の証明供給を受理しない(self):
        包, 証明 = self.前を作る()
        with self.assertRaisesRegex(ValueError, "文脈証明"):
            HDS会話文節を形成(_基礎("それを三文で要約してください。"), 前採用包=包)
        # 保存包の文脈束縛は空。独立caller証明を取り除いても自己検査へ転用しない。
        self.assertEqual(包["文脈束縛"], [])
        with self.assertRaises(ValueError):
            HDS会話文節を形成(_基礎("それを三文で要約してください。"), 前採用包=包, 文脈証明=包["文脈束縛"])

    def test_実構文化器の現在焦点から証明を受け取り引用は昇格しない(self):
        包, 証明 = self.前を作る()
        文脈 = HDS文脈(現在焦点={"前採用会話": {"契約包": 包, "文脈証明": 証明}})
        for 文, 主題 in (("それを三文で要約してください。", []), ("「前者」を三文で説明してください。", ["前者"])):
            with self.subTest(文=文):
                ir = 公開HDSコンパイラ().コンパイル束(文, 文脈=文脈).意味IR
                新包 = 会話契約を形成(ir, 所有セッション="人工所有", 文脈証明=証明)
                行 = 会話目的を読む(新包, 所有セッション="人工所有", 前採用包=包, 文脈証明=証明)
                self.assertEqual(行[0]["要求"]["主題"], 主題)
        別包, 別証明 = self.前を作る(True)
        with self.assertRaisesRegex(ValueError, "競合"):
            HDS会話文節を形成(_基礎("それを三文で要約してください。"), 文脈=文脈, 前採用包=別包, 文脈証明=別証明)

    def test_継続証明を独立再供給し親包自身から補わない(self):
        包, 証明 = self.前を作る()
        _, 次包, _ = self.継続("それを三文で要約してください。", 包, 証明)
        次証明 = [_前証明(次包, 証明), *証明]
        _, _, 行 = self.継続("それを四文で要約してください。", 次包, 次証明)
        self.assertEqual(行[0]["数量"][0]["数"], 4)
        self.assertEqual(行[0]["保持"], ["数値", "例外"])
        with self.assertRaisesRegex(ValueError, "実文脈証明"):
            HDS会話文節を形成(_基礎("それを四文で要約してください。"), 前採用包=次包, 文脈証明=次証明[:1])

    def test_括弧内の再表現と未解釈代名詞を前目的に昇格しない(self):
        包, 証明 = self.前を作る()
        文 = "「ニルパ」を二文で説明してください。（それを箇条書きにしてください。）"
        ir = HDS会話文節を形成(_基礎(文), 前採用包=包, 文脈証明=証明)
        self.assertEqual(len(_役割(ir, "目的.会話操作")), 1)
        self.assertFalse(_役割(ir, "表現.会話形式"))
        self.assertFalse(any(辺.種別 == "目的継承" for 辺 in ir.関係))
        self.assertTrue(any("それ" in 項.原文 for 項 in ir.残差 if 項.種別 == "会話未消費"))
        ir = HDS会話文節を形成(_基礎("彼を二文で説明してください。"), 前採用包=包, 文脈証明=証明)
        self.assertFalse(_役割(ir, "対象.会話主題"))
        self.assertFalse(any(辺.種別 == "目的継承" for 辺 in ir.関係))
        self.assertTrue(any("彼" in 項.原文 for 項 in ir.残差 if 項.種別 == "会話未消費"))


class 会話数量属格と保持対応契約(TestCase):
    def test_世界数量の属格対象を損なわず別目的の出力量だけを保存(self):
        文 = "二文のメモを説明し、「チベル」を三文で要約してください。"
        ir = 公開HDSコンパイラ().コンパイル束(文).意味IR
        包 = 会話契約を形成(ir, 所有セッション="人工所有")
        行 = 会話目的を読む(包, 所有セッション="人工所有", 意味IR=ir)
        self.assertEqual([項["要求"]["主題"] for 項 in 行], [["二文のメモ"], ["チベル"]])
        self.assertEqual([項["数量"] for 項 in 行], [[], [{"単位": "文", "関係": "一致", "数": 3}]])
        for 文 in ("二文のメモを説明してください。", "三項目の規程を要約してください。"):
            with self.subTest(文=文):
                self.assertIsNone(HDS会話文節を形成(_基礎(文)))

    def test_項目の箇条書きは出力形式と数量へ実構文化器で結ぶ(self):
        for 文 in ("「チベル」を四項目の箇条書きで説明してください。", "三項目以内の箇条書きで「ネラフ」を要約してください。"):
            with self.subTest(文=文):
                ir = 公開HDSコンパイラ().コンパイル束(文).意味IR
                包 = 会話契約を形成(ir, 所有セッション="人工所有")
                行 = 会話目的を読む(包, 所有セッション="人工所有", 意味IR=ir)[0]
                self.assertEqual(行["要求"]["形式"], "箇条書き")
                self.assertEqual(行["数量"], [{"単位": "項目", "関係": "以内" if "以内" in 文 else "一致", "数": 3 if "以内" in 文 else 4}])

    def test_項目属格の形式変更を前目的に継続する(self):
        元 = HDS会話文節を形成(_基礎("この報告を二文で要約してください。", "担当者は部品を検査する。担当者は履歴を残す。"))
        包 = 会話契約を形成(元, 所有セッション="人工所有")
        証明 = [_前証明(包)]
        文 = "それを三項目の箇条書きにしてください。"
        文脈 = HDS文脈(現在焦点={"前採用会話": {"契約包": 包, "文脈証明": 証明}})
        ir = 公開HDSコンパイラ().コンパイル束(文, 文脈=文脈).意味IR
        新 = 会話契約を形成(ir, 所有セッション="人工所有", 文脈証明=証明)
        行 = 会話目的を読む(新, 所有セッション="人工所有", 前採用包=包, 文脈証明=証明)[0]
        self.assertEqual(行["要求"]["操作"], ["要約"])
        self.assertEqual(行["要求"]["対象"], ["提示本文"])
        self.assertEqual(行["要求"]["形式"], "箇条書き")
        self.assertIn({"単位": "項目", "関係": "一致", "数": 3}, 行["数量"])

    def test_引用や世界箇条書き内個数を出力量へ昇格しない(self):
        文 = "二項目の箇条書きにある注記を説明し、「ネラフ」を三文で要約してください。"
        ir = 公開HDSコンパイラ().コンパイル束(文).意味IR
        群 = _役割(ir, "表現.会話数量")
        self.assertEqual([項.内容["値"] for 項 in 群], [{"単位": "文", "関係": "一致", "数": 3}])
        self.assertFalse(_役割(ir, "表現.会話形式"))
        ir = HDS会話文節を形成(_基礎("「二項目の箇条書きにする」を説明し、「ネラフ」を三文で要約してください。"))
        self.assertEqual([項.内容["値"] for 項 in _役割(ir, "表現.会話数量")], [{"単位": "文", "関係": "一致", "数": 3}])

    def test_二原保持句を二段継承しても実対応を保つ(self):
        元 = HDS会話文節を形成(_基礎("数値を保持して、例外を省かずに二文で要約してください。", "係員は箱を二個運ぶ。ただし休館日は運ばない。"))
        包 = 会話契約を形成(元, 所有セッション="人工所有")
        旧写し = deepcopy(包)
        証明 = [_前証明(包)]
        for 数, 文 in ((3, "それを三文で要約してください。"), (4, "それを四文で要約してください。")):
            ir = HDS会話文節を形成(_基礎(文), 前採用包=包, 文脈証明=証明)
            新 = 会話契約を形成(ir, 所有セッション="人工所有", 文脈証明=証明)
            行 = 会話目的を読む(新, 所有セッション="人工所有", 前採用包=包, 文脈証明=証明)[0]
            self.assertEqual(行["保持"], ["数値", "例外"])
            self.assertEqual(行["数量"][0]["数"], 数)
            self.assertEqual(sum(辺.種別 == "保持対応" for 辺 in ir.関係), 2)
            次証明 = [_前証明(新, 証明), 証明[0]]
            包, 証明 = 新, 次証明
        self.assertEqual(会話契約を形成(元, 所有セッション="人工所有"), 旧写し)


class 会話訂正と命令履歴契約(TestCase):
    def 前(self, 二目的=False):
        文 = ('「草案グリム」を二文で説明し、「草案ユナ」を三文で要約してください。' if 二目的
             else '「草案グリム」と「草案ユナ」を費用で三項目で比較してください。')
        ir = HDS会話文節を形成(_基礎(文))
        包 = 会話契約を形成(ir, 所有セッション="人工所有")
        return 包, [_前証明(包)], [_命令証明(包)]

    def 作る(self, 文, *, 前採用包=None, 文脈証明=(), 前命令包=None, 命令証明=(), 文脈=None):
        ir = HDS会話文節を形成(_基礎(文), 文脈=文脈, 前採用包=前採用包, 文脈証明=文脈証明,
                          前命令包=前命令包, 命令証明=命令証明)
        包 = 会話契約を形成(ir, 所有セッション="人工所有", 文脈証明=文脈証明, 命令証明=命令証明)
        設定 = {"所有セッション": "人工所有", "期待原文": 文, "意味IR": ir, "前採用包": 前採用包,
              "文脈証明": 文脈証明, "前命令包": 前命令包, "命令証明": 命令証明}
        return ir, 包, 会話目的を読む(包, **設定), 会話前目的対応を読む(包, **設定)

    def test_観点訂正をtyped役割と一意元目的へ結ぶ(self):
        元, 証明, _ = self.前()
        原 = deepcopy(元)
        for 文 in ('費用ではなく保守性で比較してください。', '観点を費用ではなく保守性にしてください。',
                  '費用ではなく保守性'):
            with self.subTest(文=文):
                _, _, 行, 対応 = self.作る(文, 前採用包=元, 文脈証明=証明)
                self.assertEqual(行[0]["要求"]["観点"], ["保守性"])
                self.assertEqual(行[0]["要求"]["比較対象"], ["草案グリム", "草案ユナ"])
                self.assertEqual(行[0]["数量"], [{"単位": "項目", "関係": "一致", "数": 3}])
                self.assertEqual(行[0]["要求"]["問い"], 文)
                self.assertEqual(対応[0]["方式"], "訂正")
                self.assertEqual(対応[0]["変更"][0]["対象役割"], "条件.会話観点")
        self.assertEqual(元, 原)

    def test_比較対象訂正で他対象と観点を取り落とさない(self):
        元, 証明, _ = self.前()
        for 旧, 期待 in (("草案グリム", ["草案サル", "草案ユナ"]), ("草案ユナ", ["草案グリム", "草案サル"])):
            with self.subTest(旧=旧):
                _, _, 行, 対応 = self.作る('「' + 旧 + '」ではなく「草案サル」を比較してください。', 前採用包=元, 文脈証明=証明)
                self.assertEqual(行[0]["要求"]["比較対象"], 期待)
                self.assertEqual(行[0]["要求"]["観点"], ["費用"])
                self.assertEqual(対応[0]["変更"][0]["対象役割"], "対象.会話比較")

    def test_曖昧訂正と未知条件は全文適用範囲残差(self):
        元, 証明, _ = self.前(True)
        for 文 in ('不明語ではなく別語を説明してください。', '草案グリムではなく草案サルを説明した。'):
            with self.subTest(文=文):
                ir = HDS会話文節を形成(_基礎(文), 前採用包=元, 文脈証明=証明)
                self.assertTrue(any(項.原文 == 文 for 項 in ir.残差 if 項.種別 == "会話未消費"))
                包 = 会話契約を形成(ir, 所有セッション="人工所有", 文脈証明=証明)
                with self.assertRaisesRegex(ValueError, "未消費残差"):
                    会話目的を読む(包, 所有セッション="人工所有", 前採用包=元, 文脈証明=証明)

    def test_明示再実行は現在原文と歴史命令anchorを保持(self):
        元, _, 履歴 = self.前(True)
        for 文 in ('再計算してください。', 'もう一度', '続けてください。', 'もう一度再計算して。'):
            with self.subTest(文=文):
                ir, 包, 行, 対応 = self.作る(文, 前命令包=元, 命令証明=履歴)
                self.assertEqual([項["要求"]["主題"] for 項 in 行], [["草案グリム"], ["草案ユナ"]])
                self.assertEqual([項["数量"][0]["数"] for 項 in 行], [2, 3])
                self.assertEqual([項["要求"]["問い"] for 項 in 行], [文, 文])
                self.assertEqual([項["方式"] for 項 in 対応], ["再実行", "再実行"])
                self.assertEqual(len([辺 for 辺 in ir.関係 if 辺.種別 == "命令再実行"]), 2)
                self.assertFalse(any(辺.種別 == "目的継承" for 辺 in ir.関係))
                self.assertEqual(包["文脈束縛"][0]["用途"], "命令再実行")

    def test_過去報告と追加未解釈節を命令へ昇格しない(self):
        元, _, 履歴 = self.前()
        for 文 in ('再計算した。', '続けた。', '再計算してください。例外は省いて。'):
            with self.subTest(文=文):
                ir = HDS会話文節を形成(_基礎(文), 前命令包=元, 命令証明=履歴)
                self.assertTrue(any(項.原文 == 文 for 項 in ir.残差 if 項.種別 == "会話未消費"))
                包 = 会話契約を形成(ir, 所有セッション="人工所有", 命令証明=履歴)
                with self.assertRaisesRegex(ValueError, "未消費残差"):
                    会話目的を読む(包, 所有セッション="人工所有", 前命令包=元, 命令証明=履歴)

    def test_引用内命令と世界動作を歴史候補で解決しない(self):
        元, _, 履歴 = self.前()
        文脈 = HDS文脈(現在焦点={"前命令候補": {"契約包": 元, "文脈証明": [], "命令証明": 履歴}})
        self.assertIsNone(HDS会話文節を形成(_基礎('「再計算してください」'), 文脈=文脈))
        ir = HDS会話文節を形成(_基礎('「再計算してください」を二文で説明してください。'), 文脈=文脈)
        self.assertFalse(any(辺.種別 in {"命令再実行", "目的継承"} for 辺 in ir.関係))
        self.assertEqual(_役割(ir, "対象.会話主題")[0].内容["値"], "再計算してください")

    def test_候補同時供与は字句判定後に一源だけ選ぶ(self):
        元, 証明, 履歴 = self.前()
        文脈 = HDS文脈(現在焦点={"前採用会話": {"契約包": 元, "文脈証明": 証明},
                              "前命令候補": {"契約包": 元, "文脈証明": [], "命令証明": 履歴}})
        for 文, 種, 設定 in (('それを二文で説明してください。', "目的継承", {"前採用包": 元, "文脈証明": 証明}),
                            ('再計算してください。', "命令再実行", {"前命令包": 元, "命令証明": 履歴})):
            with self.subTest(文=文):
                ir = 公開HDSコンパイラ().コンパイル束(文, 文脈=文脈).意味IR
                self.assertTrue(any(辺.種別 == 種 for 辺 in ir.関係))
                包 = 会話契約を形成(ir, 所有セッション="人工所有", 文脈証明=設定.get("文脈証明", ()), 命令証明=設定.get("命令証明", ()))
                self.assertEqual(会話前目的対応を読む(包, 所有セッション="人工所有", **設定)[0]["方式"],
                                 "照応" if 種 == "目的継承" else "再実行")

    def test_専用履歴証明無しと直接二源供給を拒否(self):
        元, 証明, 履歴 = self.前()
        with self.assertRaisesRegex(ValueError, "専用証明"):
            HDS会話文節を形成(_基礎('再計算してください。'), 前採用包=元, 文脈証明=証明)
        with self.assertRaisesRegex(ValueError, "元源を混合"):
            HDS会話文節を形成(_基礎('再計算してください。'), 前採用包=元, 文脈証明=証明, 前命令包=元, 命令証明=履歴)


class 会話疑問文節v3契約(TestCase):
    """新しい人工言語素材で同じ実Compilerの問い役割を検査する。事実回答は扱わない。"""
    def 読む(self, 文, *, 前=None, 証明=()):
        文脈 = HDS文脈(現在焦点={"前採用会話": {"契約包": 前, "文脈証明": 証明}}) if 前 else None
        ir = 公開HDSコンパイラ().コンパイル束(文, 文脈=文脈).意味IR
        包 = 会話契約を形成(ir, 所有セッション="人工所有", 文脈証明=証明)
        行 = 会話目的を読む(包, 所有セッション="人工所有", 意味IR=ir, 前採用包=前, 文脈証明=証明)
        return ir, 包, 行

    def test_異なる主題の定義疑問を別目的にする(self):
        文 = "リムナとは何ですか。ゼルナとは何ですか。"
        ir, _, 行 = self.読む(文)
        self.assertEqual([項["要求"]["主題"] for 項 in 行], [["リムナ"], ["ゼルナ"]])
        self.assertEqual([項["要求"]["関係焦点"] for 項 in 行], [["定義"], ["定義"]])
        self.assertEqual([項["要求"]["問い"] for 項 in 行], ["リムナとは何ですか。", "ゼルナとは何ですか。"])
        self.assertEqual(sum(項["要求"]["最大文字数"] for 項 in 行), 24000)
        self.assertEqual(ir.原文, 文)

    def test_理由標識の三語順を同じ主述と方向へ結ぶ(self):
        for 句 in ("なぜ装置ルナは再開するのですか", "装置ルナはどうして再開するのですか",
                   "装置ルナが再開するのはなぜですか"):
            with self.subTest(句=句):
                _, _, 行 = self.読む("二文で" + 句 + "。")
                要求 = 行[0]["要求"]
                self.assertEqual((要求["操作"], 要求["主題"], 要求["関係焦点"], 要求["肯否"]),
                                 (["理由"], ["装置ルナ"], ["再開する"], "肯定"))
                self.assertEqual(行[0]["数量"], [{"単位": "文", "関係": "一致", "数": 2}])

    def test_疑問終助詞の否定と肯定形容詞を区別する(self):
        for 述部, 方向 in (("作動しない", "否定"), ("少ない", "肯定"), ("危ない", "肯定")):
            with self.subTest(述部=述部):
                _, _, 行 = self.読む("二文でなぜ装置ルナは" + 述部 + "の？")
                self.assertEqual(行[0]["要求"]["関係焦点"], [述部])
                self.assertEqual(行[0]["要求"]["肯否"], 方向)

    def test_差異疑問の二形を同じ比較対象へ結ぶ(self):
        for 句 in ("リムナとゼルナの違いは何ですか", "リムナとゼルナは何が違いますか"):
            with self.subTest(句=句):
                _, _, 行 = self.読む("三項目で" + 句 + "。")
                self.assertEqual(行[0]["要求"]["操作"], ["対照"])
                self.assertEqual(行[0]["要求"]["比較対象"], ["リムナ", "ゼルナ"])

    def test_属格属性疑問を定義へ畳まない(self):
        _, _, 行 = self.読む("二文でリムナの特徴は何ですか。")
        self.assertEqual(行[0]["要求"]["主題"], ["リムナ"])
        self.assertEqual(行[0]["要求"]["関係焦点"], ["特徴", "何"])

    def test_口語の定義疑問も数量を失わない(self):
        _, _, 行 = self.読む("二文でリムナって何？")
        self.assertEqual(行[0]["要求"]["主題"], ["リムナ"])
        self.assertEqual(行[0]["要求"]["関係焦点"], ["定義"])
        self.assertEqual(行[0]["数量"], [{"単位": "文", "関係": "一致", "数": 2}])

    def test_丁寧動詞の述部と否定を原形へ勝手に置換しない(self):
        for 述部, 方向 in (("動きます", "肯定"), ("動きません", "否定")):
            with self.subTest(述部=述部):
                _, _, 行 = self.読む("二文でなぜ装置ルナは" + 述部 + "か？")
                self.assertEqual(行[0]["要求"]["関係焦点"], [述部])
                self.assertEqual(行[0]["要求"]["肯否"], 方向)

    def test_同主題の複数独立句を旧単目的へ落とさない(self):
        _, _, 行 = self.読む("リムナを説明してください。リムナを要約してください。")
        self.assertEqual([項["要求"]["操作"] for 項 in 行], [["説明"], ["要約"]])

    def test_単操作の新補助句と内部読点を旧型へ捨てない(self):
        for 文, 作用 in (("リムナについて教えてほしい。", "説明"), ("リムナを整理して。", "要約"),
                         ("リムナとゼルナを、保守性の観点で比べてほしい。", "対照")):
            with self.subTest(文=文):
                _, _, 行 = self.読む(文)
                self.assertEqual(行[0]["要求"]["操作"], [作用])
                if 作用 == "対照":
                    self.assertEqual(行[0]["要求"]["観点"], ["保守性"])

    def test_疑問名詞と欲求補助の比較を説明へ誤分類しない(self):
        for 動作 in ("教えてほしい", "説明してください", "比べてほしい"):
            with self.subTest(動作=動作):
                _, _, 行 = self.読む("三項目でリムナとゼルナの違いを" + 動作 + "。")
                self.assertEqual(行[0]["要求"]["操作"], ["対照"])
                self.assertEqual(行[0]["要求"]["比較対象"], ["リムナ", "ゼルナ"])

    def test_理由の末尾依頼補助を問う述部へ混入しない(self):
        _, _, 行 = self.読む("二文でなぜ装置ルナは作動しないのか教えてほしい。")
        self.assertEqual(行[0]["要求"]["操作"], ["理由"])
        self.assertEqual(行[0]["要求"]["関係焦点"], ["作動しない"])
        self.assertEqual(行[0]["要求"]["肯否"], "否定")

    def test_属格の属性依頼も主題と焦点に分ける(self):
        _, _, 行 = self.読む("リムナの用途を教えてほしい。")
        self.assertEqual(行[0]["要求"]["主題"], ["リムナ"])
        self.assertEqual(行[0]["要求"]["関係焦点"], ["用途"])

    def test_先頭理由の全句を次の疑問と分ける(self):
        _, _, 行 = self.読む("なぜ装置ルナは作動しないの？ゼルナとは何ですか。")
        self.assertEqual([項["要求"]["操作"] for 項 in 行], [["理由"], ["説明"]])
        self.assertEqual(行[0]["要求"]["問い"], "なぜ装置ルナは作動しないの？")
        self.assertEqual(行[0]["要求"]["肯否"], "否定")

    def test_未知の条件作用域は原節と影響目的を保全する(self):
        文 = "なぜ装置ルナは再開するなら絶対に動くの？ゼルナを二文で説明して。"
        ir = 公開HDSコンパイラ().コンパイル束(文).意味IR
        包 = 会話契約を形成(ir, 所有セッション="人工所有")
        残差 = [項 for 項 in ir.残差 if 項.種別 == "会話未消費"]
        self.assertTrue(any(項.原文 == 文.split("？")[0] + "？" and "条件節" in 項.理由 for 項 in 残差))
        self.assertTrue(all(項.影響座標 for 項 in 残差))
        with self.assertRaisesRegex(ValueError, "未消費残差"):
            会話目的を読む(包, 所有セッション="人工所有")

    def test_引用した疑問は実行せず原主題として保つ(self):
        _, _, 行 = self.読む("「なぜ装置ルナは作動しないの？」を二文で説明してください。")
        self.assertEqual(len(行), 1)
        self.assertEqual(行[0]["要求"]["操作"], ["説明"])
        self.assertEqual(行[0]["要求"]["関係焦点"], [])

    def test_現行前束の資料役割と現在理由を分ける(self):
        元 = HDS会話文節を形成(_基礎("装置ネリスを二文で説明してください。"))
        前 = 会話契約を形成(元, 所有セッション="人工所有"); 証明 = [_前証明(前)]
        _, 包, 行 = self.読む("なぜそれは再開しないの？", 前=前, 証明=証明)
        self.assertEqual(行[0]["要求"]["主題"], ["装置ネリス"])
        self.assertEqual(行[0]["要求"]["操作"], ["理由"])
        self.assertEqual(行[0]["要求"]["関係焦点"], ["再開しない"])
        対応 = 会話前目的対応を読む(包, 所有セッション="人工所有", 前採用包=前, 文脈証明=証明)
        self.assertEqual(対応[0]["方式"], "照応")
        self.assertEqual(対応[0]["元目的ID"], 前["目的参照"][0])
        with self.assertRaisesRegex(ValueError, "証明"):
            self.読む("なぜそれは再開しないの？", 前=前)

    def test_新定義の問い方向を旧否定で上書きしない(self):
        _, 前, _ = self.読む("二文でなぜ装置ネリスは作動しないの？")
        証明 = [_前証明(前)]
        _, _, 行 = self.読む("それとは何ですか？", 前=前, 証明=証明)
        self.assertEqual(行[0]["要求"]["関係焦点"], ["定義"])
        self.assertEqual(行[0]["要求"]["肯否"], "未指定")

    def test_未知様式を疑問主題へ吸収しない(self):
        文 = "二文でやさしくリムナとは何ですか。"
        ir = 公開HDSコンパイラ().コンパイル束(文).意味IR
        self.assertTrue(any("主題" in 項.理由 and "やさしく" in 項.原文 for 項 in ir.残差 if 項.種別 == "会話未消費"))


if __name__ == "__main__":
    main()

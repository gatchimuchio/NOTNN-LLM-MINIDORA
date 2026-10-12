"""人工IR・純粋計画の有限契約。自然入力/実取得/製品採否の検査ではない。"""
from copy import deepcopy
from dataclasses import replace
import hashlib
import json
from unittest import TestCase, main

from minidora.HDS中間表現 import HDSIR, HDS座標, HDS残差, HDS実行核
from minidora.HDS会話文節 import HDS会話文節を形成
from minidora.HDS会話契約 import 会話射影由来, 会話取得時期版, 会話契約を形成, 会話契約を検査
from minidora.HDS運用.会話目的束 import 会話目的を読む, 会話取得条件を読む, 会話取得時期を読む
from minidora.HDS運用.一般依頼 import _一般会話計画を作る, _会話目的束計画を作る, 一般計画を作る


def _基礎(制御, 本文=None):
    原文 = 制御 if 本文 is None else 制御 + "\n\n" + 本文
    座標 = [HDS座標("既存領域", "世界.人工", {"値": "旧構造"})]
    if 本文 is not None:
        座標.extend(HDS座標("元区分:" + 名, "情報源.会話入力区分", {"役割": 名, "本文": 原文[始:終]},
                          原文範囲=(始, 終), 由来="公開HDS 入力区分")
                    for 名, 始, 終 in (("制御", 0, len(制御)), ("区切り", len(制御), len(制御) + 2),
                                    ("提示本文", len(制御) + 2, len(原文))))
    return HDSIR(原文, 制御, "時期人工世界", tuple(座標), (),
                 (HDS残差("別領域残差", "別領域未観測", "旧原文", "旧残差を保持"),), (), HDS実行核())


def _問い(付属="今", 主題="試験語ルメ"):
    return 主題 + "がどんなものか、" + (付属 + "、" if 付属 else "") + "公開資料を読んで答えて。"


def _包(ir, 証明=()):
    return 会話契約を形成(ir, 所有セッション="時期人工所有", 文脈証明=証明)


def _証明(包):
    ビュー = 会話契約を検査(包, 所有セッション="時期人工所有")
    役割名 = set(包["目的参照"])
    for 辺 in ビュー["関係"]:
        if 辺["種別"] in {"要求対象", "要求観点", "要求関係", "問い方向", "要求範囲", "条件適用", "表現適用"}:
            役割名.update((*辺["始点"], *辺["終点"]))
    def 印(値):
        return hashlib.sha256(json.dumps(値, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode()).hexdigest()
    return [{"前束印": 包["意味束印"], "所有セッション": "時期人工所有", "原記録ID": "人工採用時期",
             "依存版": {}, "参照": [{"座標ID": 項["座標ID"], "役割": 項["種別"], "値印": 印(項["内容"]["値"])}
                                    for 項 in ビュー["座標"] if 項["座標ID"] in 役割名]}]


class 取得付属時期契約(TestCase):
    def 形成(self, 文=None, 本文=None):
        元 = _基礎(文 or _問い(), 本文)
        ir = HDS会話文節を形成(元)
        self.assertIsNotNone(ir)
        self.assertEqual(ir.原文, 元.原文)
        self.assertEqual(ir.座標[:len(元.座標)], 元.座標)
        self.assertEqual(ir.残差[:len(元.残差)], 元.残差)
        return ir, _包(ir)

    def 読む(self, 包):
        return 会話目的を読む(包, 所有セッション="時期人工所有")

    def 時期(self, 包):
        return 会話取得時期を読む(包, 所有セッション="時期人工所有")

    def 入力(self, ir, 許可=True):
        return {"セッションID": "時期人工所有", "原文": ir.原文, "外部許可": 許可, "資料": {}}

    def test_副詞可能の原時期を同じ取得へ保持(self):
        for 語 in ("今", "いま", "現在"):
            with self.subTest(語=語):
                ir, 包 = self.形成(_問い(語))
                行 = self.読む(包)
                self.assertEqual(行[0]["要求"]["主題"], ["試験語ルメ"])
                self.assertEqual(行[0]["要求"]["操作"], ["説明"])
                self.assertEqual(行[0]["要求"]["範囲"], "公開取得")
                条件 = self.時期(包)
                self.assertEqual(len(条件), 1)
                self.assertEqual(set(条件[0]), {"目的ID", "条件ID", "版", "作用", "基準", "原文", "原文範囲"})
                self.assertEqual({鍵: 条件[0][鍵] for 鍵 in ("版", "作用", "基準")},
                                 {"版": 会話取得時期版, "作用": "外部読取", "基準": "要求時点"})
                self.assertEqual(ir.原文[slice(*条件[0]["原文範囲"])], 語)
                self.assertEqual(条件[0]["原文"], 語)

    def test_時期なしの取得要求と既存行形を維持(self):
        _, 包 = self.形成(_問い(""))
        写し = deepcopy(包)
        self.assertEqual(self.時期(包), [])
        self.assertEqual(set(self.読む(包)[0]), {"目的ID", "文節ID", "要求", "数量", "保持"})
        self.assertEqual(包, 写し)

    def test_情報源に隣接する副詞型と接頭辞型を区別(self):
        ir, 包 = self.形成("試験語ルメがどんなものか、今インターネットを読んで答えて。")
        self.assertEqual(self.時期(包)[0]["原文"], "今")
        self.assertEqual(self.読む(包)[0]["要求"]["主題"], ["試験語ルメ"])
        ir, 包 = self.形成("試験語ルメがどんなものか、今公開資料を読んで答えて。")
        self.assertTrue(any("今公開資料" in 項.原文 for 項 in ir.残差 if 項.種別 == "会話未消費"))
        with self.assertRaisesRegex(ValueError, "未消費"):
            self.読む(包)

    def test_未知未来付属を消費せず残す(self):
        for 語 in ("明日", "素早く", "適宜"):
            with self.subTest(語=語):
                ir, 包 = self.形成(_問い(語))
                self.assertTrue(any(語 in 項.原文 for 項 in ir.残差 if 項.種別 == "会話未消費"))
                self.assertFalse(any(項.種別 == "条件.会話適用" and 項.内容["値"]["役割"] == "取得時期" for 項 in ir.座標))
                with self.assertRaisesRegex(ValueError, "未消費|未確定"):
                    self.読む(包)

    def test_対象側現在を取得時期に転用しない(self):
        ir, 包 = self.形成("現在の試験語ルメがどんなものか、公開資料を読んで答えて。")
        self.assertFalse(any(項.種別 == "条件.会話適用" and 項.内容["値"]["役割"] == "取得時期" for 項 in ir.座標))
        self.assertTrue(any("現在" in 項.原文 for 項 in ir.残差 if 項.種別 == "会話未消費"))
        with self.assertRaisesRegex(ValueError, "未消費|未確定"):
            self.読む(包)

    def test_禁止を保持し許可語から権限を作らない(self):
        ir, 包 = self.形成(_問い() + "外部の読み取りは許可しません。")
        条件 = 会話取得条件を読む(包, 所有セッション="時期人工所有")
        self.assertTrue(条件[0]["外部禁止"])
        self.assertEqual(set(条件[0]), {"目的ID", "外部禁止", "原文", "条件ID"})
        要求 = self.読む(包)[0]["要求"]
        for 許可 in (False, True):
            with self.subTest(許可=許可), self.assertRaisesRegex(ValueError, "禁止"):
                _一般会話計画を作る(要求, self.入力(ir, 許可), 外部禁止=True, 取得時期=self.時期(包))

    def test_要求未許可では取得計画を形成しない(self):
        ir, 包 = self.形成()
        with self.assertRaisesRegex(ValueError, "検索を許可"):
            _一般会話計画を作る(self.読む(包)[0]["要求"], self.入力(ir, False), 取得時期=self.時期(包))

    def test_資料内の取得命令を当回条件へ昇格しない(self):
        ir, 包 = self.形成("この文書を二文で要約してください。", _問い())
        self.assertEqual(self.時期(包), [])
        行 = self.読む(包)[0]
        self.assertEqual(行["要求"]["提示本文"], _問い())
        self.assertEqual(行["要求"]["範囲"], "自動")
        self.assertEqual(行["要求"]["操作"], ["要約"])

    def test_当回条件は既採用資料を再使用せず新取得計画へ(self):
        ir, 包 = self.形成()
        入力 = {**self.入力(ir), "前回有効": True, "前回結果": {"旧結果を読むと失敗": True},
              "資料": {"試験語ルメ": {"本文": "旧登録本文"}}}
        計画, 素材, _ = _一般会話計画を作る(self.読む(包)[0]["要求"], 入力,
                                      継承="照応", 根拠継承=True, 取得時期=self.時期(包))
        self.assertEqual([項.能力候補 for 項 in 計画.工程].count(("知識取得",)), 1)
        self.assertEqual(素材["一般:束縛"].データ["実範囲"], "公開取得")
        self.assertFalse(any(名.startswith("一般:資料:") for 名 in 素材))

    def test_子解釈に型時期を保存し取得未実行を維持(self):
        ir, 包 = self.形成()
        計画, 素材, _ = _会話目的束計画を作る({"方式": "一般会話目的束", "原文": ir.原文, "要求": 包}, self.入力(ir))
        self.assertEqual(素材["一般:子計画"].データ["子計画"][0]["解釈"]["取得時期"], self.時期(包))
        self.assertEqual([項.能力候補 for 項 in 計画.工程].count(("知識取得",)), 1)
        self.assertFalse(any(名.startswith("会話目的:0:一般:資料:") for 名 in 素材))

    def test_子解釈の再計画にも当回条件を保持(self):
        ir, 包 = self.形成()
        解釈 = {"方式": "一般資料", "原文": ir.原文, "要求": self.読む(包)[0]["要求"],
              "取得時期": self.時期(包), "継承": "照応"}
        入力 = {**self.入力(ir), "前回有効": True, "前回結果": {"旧結果を読むと失敗": True}}
        計画, 素材, _ = 一般計画を作る(解釈, 入力)
        self.assertEqual([項.能力候補 for 項 in 計画.工程].count(("知識取得",)), 1)
        self.assertEqual(素材["一般:束縛"].データ["実範囲"], "公開取得")
        改変 = deepcopy(解釈)
        改変["取得時期"][0]["原文範囲"] = [0, 1]
        with self.assertRaisesRegex(ValueError, "当回の原要求"):
            一般計画を作る(改変, 入力)

    def test_時期の余剰基準や作用改変を拒否(self):
        ir, _ = self.形成()
        for 値 in ({"版": 会話取得時期版, "作用": "外部読取", "基準": "最新情報"},
                   {"版": 会話取得時期版, "作用": "許可付与", "基準": "要求時点"},
                   {"版": 会話取得時期版, "作用": "外部読取", "基準": "要求時点", "時刻": "捏造"}, "今"):
            with self.subTest(値=値):
                群 = tuple(replace(項, 内容={**項.内容, "値": {"役割": "取得時期", "値": 値}})
                           if 項.種別 == "条件.会話適用" else 項 for 項 in ir.座標)
                with self.assertRaises(ValueError):
                    _包(replace(ir, 座標=群))

    def test_時期の目的跨ぎを再封緘しても拒否(self):
        ir, _ = self.形成(_問い() + _問い("", "試験語ソナ"))
        目的 = [項.座標ID for 項 in ir.座標 if 項.種別 == "目的.会話操作"]
        時期 = next(項.座標ID for 項 in ir.座標 if 項.種別 == "条件.会話適用")
        群 = tuple(replace(辺, 終点=(目的[1],)) if 辺.種別 == "条件適用" and 辺.始点 == (時期,) else 辺 for 辺 in ir.関係)
        with self.assertRaisesRegex(ValueError, "文節又は区分の範囲外"):
            _包(replace(ir, 関係=群))

    def test_時期を提示材料の同語へ移植しても拒否(self):
        ir, _ = self.形成(_問い(), "今という原語を記録した本文。")
        始 = ir.原文.rindex("今")
        群 = tuple(replace(項, 原文範囲=(始, 始 + 1)) if 項.種別 == "条件.会話適用" else 項 for 項 in ir.座標)
        with self.assertRaisesRegex(ValueError, "文節又は区分の範囲外"):
            _包(replace(ir, 座標=群))

    def test_同目的の取得時期重複を拒否(self):
        ir, _ = self.形成()
        時期 = next(項 for 項 in ir.座標 if 項.種別 == "条件.会話適用")
        辺 = next(辺 for 辺 in ir.関係 if 辺.種別 == "条件適用")
        群 = (*ir.座標, replace(時期, 座標ID="人工重複時期"))
        作用 = replace(ir.意味作用履歴[-1], 出力参照=tuple(項.座標ID for 項 in 群 if 項.由来 == 会話射影由来))
        with self.assertRaisesRegex(ValueError, "一意"):
            _包(replace(ir, 座標=群, 関係=(*ir.関係, replace(辺, 関係ID="人工重複辺", 始点=("人工重複時期",))),
                        意味作用履歴=(作用,)))

    def test_前束の時期を新要求へ自動継承しない(self):
        _, 前 = self.形成()
        証明 = _証明(前)
        ir = HDS会話文節を形成(_基礎("それを二文で説明してください。"), 前採用包=前, 文脈証明=証明)
        self.assertTrue(any("取得時期" in 項.理由 for 項 in ir.残差 if 項.種別 == "会話未消費"))
        with self.assertRaisesRegex(ValueError, "未消費"):
            会話目的を読む(_包(ir, 証明), 所有セッション="時期人工所有", 前採用包=前, 文脈証明=証明)


if __name__ == "__main__":
    main()

"""人工IRの純粋読取契約。製品・採否・外部取得の試験ではない。"""
from copy import deepcopy
from dataclasses import replace
from unittest import TestCase, main
import hashlib
import json

from minidora.HDS中間表現 import HDSIR, HDS座標, HDS関係, HDS意味作用, HDS実行核, 値状態
from minidora.HDS会話文節 import HDS会話文節を形成
from minidora.HDS会話契約 import 会話契約版, 会話射影由来, 会話契約を形成, 会話命令証明版
from minidora.HDS運用.会話目的束 import 会話目的を読む, 会話前目的対応を読む


def _基礎(制御, 本文=None):
    原文 = 制御 if 本文 is None else 制御 + "\n\n" + 本文
    座標 = ()
    if 本文 is not None:
        座標 = tuple(HDS座標("元:" + 名, "情報源.会話入力区分", {"役割": 名, "本文": 原文[始:終]},
                           原文範囲=(始, 終), 由来="公開HDS 入力区分")
                    for 名, 始, 終 in (("制御", 0, len(制御)), ("区切り", len(制御), len(制御) + 2),
                                    ("提示本文", len(制御) + 2, len(原文))))
    return HDSIR(原文, 制御, "人工読取世界", 座標, (), (), (), HDS実行核())


def _追加(ir, 種, 値, 関係種, 目的番号=0, 範囲=None):
    目的 = [項 for 項 in ir.座標 if 項.種別 == "目的.会話操作"][目的番号]
    項 = HDS座標("人工追加:" + str(len(ir.座標)), 種,
                {"値": 値, "原文": "" if 範囲 is None else ir.原文[slice(*範囲)],
                 "根拠": "既定" if 範囲 is None else "原文", "前束参照": None},
                原文範囲=範囲, 由来=会話射影由来)
    if 関係種 in {"表現適用", "条件適用"}:
        始, 終 = 項.座標ID, 目的.座標ID
    else:
        始, 終 = 目的.座標ID, 項.座標ID
    辺 = HDS関係("人工辺:" + str(len(ir.関係)), (始,), (終,), 関係種, 由来=会話射影由来)
    群 = (*ir.座標, 項)
    作用 = replace(ir.意味作用履歴[-1], 出力参照=tuple(項.座標ID for 項 in 群 if 項.由来 == 会話射影由来))
    return replace(ir, 座標=群, 関係=(*ir.関係, 辺), 意味作用履歴=(作用,))


def _値印(値):
    return hashlib.sha256(json.dumps(値, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode()).hexdigest()


def _証明(包):
    ビュー = json.loads(包["証明正準JSON"])
    役割名 = set(包["目的参照"])
    for 辺 in ビュー["関係"]:
        if 辺["種別"] in {"要求対象", "要求観点", "要求関係", "問い方向", "要求範囲", "条件適用", "表現適用"}:
            役割名.update((*辺["始点"], *辺["終点"]))
    return [{"前束印": 包["意味束印"], "所有セッション": "人工所有", "原記録ID": "人工採用",
             "依存版": {}, "参照": [{"座標ID": 項["座標ID"], "役割": 項["種別"], "値印": _値印(項["内容"]["値"])}
                                    for 項 in ビュー["座標"] if 項["座標ID"] in 役割名]}]


def _座標群を替える(ir, 群, 削除=()):
    座標 = tuple(項 for 項 in 群 if 項.座標ID not in 削除)
    辺 = tuple(項 for 項 in ir.関係 if not set(項.始点 + 項.終点).intersection(削除))
    作用 = replace(ir.意味作用履歴[-1], 出力参照=tuple(項.座標ID for 項 in 座標 if 項.由来 == 会話射影由来))
    return replace(ir, 座標=座標, 関係=辺, 意味作用履歴=(作用,))


class 会話目的束契約(TestCase):
    def 読む(self, ir):
        包 = 会話契約を形成(ir, 所有セッション="人工所有")
        前 = deepcopy(包)
        結果 = 会話目的を読む(包, 所有セッション="人工所有", 期待原文=ir.原文, 意味IR=ir)
        self.assertEqual(包, 前)
        self.assertTrue(all(set(行) == {"目的ID", "文節ID", "要求", "数量", "保持"} for 行 in 結果))
        return 結果

    def test_別目的の対象数量を混ぜず総予算を配分(self):
        ir = HDS会話文節を形成(_基礎("「試案A」を説明し、「試案B」を三文で要約してください。"))
        行 = self.読む(ir)
        self.assertEqual([項["要求"]["主題"] for 項 in 行], [["試案A"], ["試案B"]])
        self.assertEqual([項["要求"]["操作"] for 項 in 行], [["説明"], ["要約"]])
        self.assertEqual(行[0]["数量"], [])
        self.assertEqual(行[1]["数量"], [{"単位": "文", "関係": "一致", "数": 3}])
        self.assertEqual(sum(項["要求"]["最大文字数"] for 項 in 行), 24000)

    def test_実提示区分と型保持を保全(self):
        ir = HDS会話文節を形成(_基礎("数値と条件を保持して二文で要約してください。", "人工原文。"))
        行 = self.読む(ir)[0]
        self.assertEqual(行["保持"], ["数値", "条件"])
        self.assertEqual(行["要求"]["提示本文"], "人工原文。")
        self.assertEqual(行["要求"]["対象"], [])
        self.assertEqual(行["要求"]["範囲"], "自動")

    def test_原保持句に型意味がなければ拒否(self):
        ir = HDS会話文節を形成(_基礎("例外を保持して二文で要約してください。", "人工原文。"))
        名前 = {項.座標ID for 項 in ir.座標 if 項.種別 == "表現.会話保持"}
        群 = tuple(項 for 項 in ir.座標 if 項.座標ID not in 名前)
        ir = replace(ir, 座標=群, 関係=tuple(項 for 項 in ir.関係 if not 名前.intersection(項.始点 + 項.終点)),
                     意味作用履歴=(replace(ir.意味作用履歴[-1], 出力参照=tuple(項.座標ID for 項 in 群 if 項.由来 == 会話射影由来)),))
        with self.assertRaisesRegex(ValueError, "型保持"):
            self.読む(ir)

    def test_未知保持と会話残差を既定へ落とさない(self):
        ir = HDS会話文節を形成(_基礎("雰囲気を保持して二文で要約してください。", "人工原文。"))
        with self.assertRaisesRegex(ValueError, "未消費残差"):
            self.読む(ir)

    def test_型保持の余剰と原文範囲不一致を拒否(self):
        ir = HDS会話文節を形成(_基礎("「試案A」を二文で説明してください。"))
        ir = _追加(ir, "表現.会話保持", "例外", "表現適用", 範囲=(1, 4))
        with self.assertRaisesRegex(ValueError, "原文へ未束縛"):
            self.読む(ir)

    def test_観点焦点肯否表現を既存欄へ降ろす(self):
        ir = HDS会話文節を形成(_基礎("「試案A」を二文で説明してください。"))
        for 種, 値, 辺 in (("条件.会話観点", "耐久性", "要求観点"), ("関係.会話問い焦点", "停止", "要求関係"),
                        ("条件.会話問い方向", "否定", "問い方向"), ("表現.会話形式", "箇条書き", "表現適用"),
                        ("表現.会話詳細", "詳細", "表現適用")):
            ir = _追加(ir, 種, 値, 辺)
        要求 = self.読む(ir)[0]["要求"]
        self.assertEqual((要求["観点"], 要求["関係焦点"], 要求["肯否"], 要求["形式"], 要求["詳細"]),
                         (["耐久性"], ["停止"], "否定", "箇条書き", "詳細"))

    def test_資料名は比較対象とは別欄に保持(self):
        ir = HDS会話文節を形成(_基礎("「試案A」と「試案B」を二項目で比較してください。"))
        ir = _追加(ir, "対象.会話資料", "登録甲", "要求対象")
        行 = self.読む(ir)[0]
        self.assertEqual(行["要求"]["対象"], ["登録甲"])
        self.assertEqual(行["要求"]["比較対象"], ["試案A", "試案B"])
        self.assertEqual(行["要求"]["範囲"], "指定資料")

    def test_単値競合と未知条件を拒否(self):
        ir = HDS会話文節を形成(_基礎("「試案A」を二文で説明してください。"))
        前 = _追加(_追加(ir, "表現.会話詳細", "詳細", "表現適用"), "表現.会話詳細", "簡潔", "表現適用")
        with self.assertRaisesRegex(ValueError, "競合"):
            self.読む(前)
        条件 = _追加(ir, "条件.会話適用", {"役割": "問い条件", "値": "人工条件"}, "条件適用", 範囲=(1, 4))
        with self.assertRaisesRegex(ValueError, "条件役割が未接続"):
            self.読む(条件)

    def test_小さい文字上限は元数量と作成予算を区別(self):
        ir = HDS会話文節を形成(_基礎("「試案A」を二文で説明してください。"))
        ir = _追加(ir, "表現.会話文字上限", 50, "表現適用")
        行 = self.読む(ir)[0]
        self.assertEqual(行["要求"]["最大文字数"], 100)
        self.assertIn({"単位": "文字", "関係": "以内", "数": 50}, 行["数量"])

    def test_一致文字数量と原上限競合を拒否(self):
        ir = HDS会話文節を形成(_基礎("「試案A」を80文字で説明してください。"))
        ir = _追加(ir, "表現.会話文字上限", 50, "表現適用")
        with self.assertRaisesRegex(ValueError, "一致文字数量"):
            self.読む(ir)

    def test_総文字上限と外部主題を目的数倍へしない(self):
        ir = HDS会話文節を形成(_基礎("「試案A」を説明し、「試案B」を要約してください。"))
        両方 = _追加(_追加(ir, "表現.会話文字上限", 15000, "表現適用"), "表現.会話文字上限", 15000, "表現適用", 1)
        with self.assertRaisesRegex(ValueError, "総文字予算"):
            self.読む(両方)
        for 名, 目的 in (("人工C", 0), ("人工D", 1), ("人工E", 1)):
            ir = _追加(ir, "対象.会話主題", 名, "要求対象", 目的)
        with self.assertRaisesRegex(ValueError, "外部主題合計"):
            self.読む(ir)

    def test_未確定原束不一致と別所有旧版を拒否(self):
        ir = HDS会話文節を形成(_基礎("「試案A」を二文で説明してください。"))
        目的 = next(項 for 項 in ir.座標 if 項.種別 == "目的.会話操作")
        未確定 = replace(ir, 座標=tuple(replace(項, 値状態=値状態.未確定) if 項 == 目的 else 項 for 項 in ir.座標))
        with self.assertRaisesRegex(ValueError, "未確定"):
            self.読む(未確定)
        包 = 会話契約を形成(ir, 所有セッション="人工所有")
        with self.assertRaises(ValueError):
            会話目的を読む(包, 所有セッション="別所有")
        with self.assertRaises(ValueError):
            会話目的を読む(包, 所有セッション="人工所有", 期待原文="別原文")
        with self.assertRaises(ValueError):
            会話目的を読む({"版": "HDS一般会話要求-v2"}, 所有セッション="人工所有")


class 会話前束読取契約(TestCase):
    def setUp(self):
        元 = HDS会話文節を形成(_基礎("「ダルム」を二文で説明し、「ユケナ」を三文で要約してください。"))
        self.前包 = 会話契約を形成(元, 所有セッション="人工所有")
        self.証明 = _証明(self.前包)
        self.元 = 元
        self.ir = HDS会話文節を形成(_基礎("前者を説明してください。"), 前採用包=self.前包, 文脈証明=self.証明)

    def 読む(self, ir=None, 前包=None, 証明=None):
        ir = ir or self.ir
        証明 = self.証明 if 証明 is None else 証明
        包 = 会話契約を形成(ir, 所有セッション="人工所有", 文脈証明=証明)
        return 会話目的を読む(包, 所有セッション="人工所有", 前採用包=前包 or self.前包, 文脈証明=証明)

    def test_元適用辺の主題数量を同一目的のまま読む(self):
        行 = self.読む()[0]
        self.assertEqual(行["要求"]["主題"], ["ダルム"])
        self.assertEqual(行["数量"], [{"単位": "文", "関係": "一致", "数": 2}])

    def test_同印内の別目的役割混合を正準再封緘でも拒否する(self):
        別 = next(項 for 項 in self.元.座標 if 項.種別 == "対象.会話主題" and 項.内容["値"] == "ユケナ")
        今 = next(項 for 項 in self.ir.座標 if 項.種別 == "対象.会話主題")
        参照ID = 今.内容["前束参照"]
        群 = []
        for 項 in self.ir.座標:
            内容 = deepcopy(項.内容)
            if 項.座標ID == 今.座標ID: 内容["値"] = 別.内容["値"]
            if 項.座標ID == 参照ID:
                内容["値"].update(座標ID=別.座標ID, 値印=_値印(別.内容["値"]))
            群.append(replace(項, 内容=内容))
        with self.assertRaisesRegex(ValueError, "実適用辺"):
            self.読む(_座標群を替える(self.ir, 群))

    def test_元数量の無言取り落としを拒否する(self):
        数量 = next(項 for 項 in self.ir.座標 if 項.種別 == "表現.会話数量")
        ir = _座標群を替える(self.ir, self.ir.座標, (数量.座標ID, 数量.内容["前束参照"]))
        with self.assertRaisesRegex(ValueError, "取り落とし"):
            self.読む(ir)

    def test_別前包と無証明と旧版を受理しない(self):
        包 = 会話契約を形成(self.ir, 所有セッション="人工所有", 文脈証明=self.証明)
        with self.assertRaises(ValueError):
            会話目的を読む(包, 所有セッション="人工所有", 前採用包=self.前包)
        with self.assertRaisesRegex(ValueError, "前採用包"):
            会話目的を読む(包, 所有セッション="人工所有", 文脈証明=self.証明)
        for 前 in (dict(self.前包, 版="HDS一般会話要求-v2"), dict(self.前包, 所有セッション="別所有")):
            with self.subTest(前=前["版"]):
                with self.assertRaises(ValueError):
                    self.読む(前包=前)

    def test_元目的anchorを外して自己役割だけを継承しない(self):
        ir = replace(self.ir, 関係=tuple(辺 for 辺 in self.ir.関係 if 辺.種別 != "目的継承"))
        with self.assertRaises(ValueError):
            self.読む(ir)

    def test_現在未知条件を前目的の既定で吸収しない(self):
        文 = "特殊な事情で前者を二文で説明してください。"
        ir = HDS会話文節を形成(_基礎(文), 前採用包=self.前包, 文脈証明=self.証明)
        with self.assertRaisesRegex(ValueError, "未消費残差"):
            self.読む(ir)


class 会話保持対応読取契約(TestCase):
    def 初回(self):
        ir = HDS会話文節を形成(_基礎("数値を保持して、例外を省かずに二文で要約してください。", "係員は箱を二個運ぶ。ただし休館日は運ばない。"))
        包 = 会話契約を形成(ir, 所有セッション="人工所有")
        return ir, 包, _証明(包)

    def test_同目的でも異なる原保持句への辺移植は拒否する(self):
        元, _, _ = self.初回()
        保持辺 = [辺 for 辺 in 元.関係 if 辺.種別 == "保持対応"]
        ir = replace(元, 関係=tuple(replace(辺, 終点=保持辺[1 - 保持辺.index(辺)].終点)
                                  if 辺.種別 == "保持対応" else 辺 for 辺 in 元.関係))
        包 = 会話契約を形成(ir, 所有セッション="人工所有")
        with self.assertRaisesRegex(ValueError, "原保持句の原範囲"):
            会話目的を読む(包, 所有セッション="人工所有")

    def test_前束値印一致だけでは保持対の交換を認めない(self):
        _, 前, 証明 = self.初回()
        元 = HDS会話文節を形成(_基礎("それを三文で要約してください。"), 前採用包=前, 文脈証明=証明)
        保持辺 = [辺 for 辺 in 元.関係 if 辺.種別 == "保持対応"]
        ir = replace(元, 関係=tuple(replace(辺, 終点=保持辺[1 - 保持辺.index(辺)].終点)
                                  if 辺.種別 == "保持対応" else 辺 for 辺 in 元.関係))
        包 = 会話契約を形成(ir, 所有セッション="人工所有", 文脈証明=証明)
        with self.assertRaisesRegex(ValueError, "前採用包の実辺"):
            会話目的を読む(包, 所有セッション="人工所有", 前採用包=前, 文脈証明=証明)

    def test_旧原範囲から新対応を形成し旧None多保持は具体保留(self):
        元, _, _ = self.初回()
        元 = replace(元, 関係=tuple(辺 for 辺 in 元.関係 if 辺.種別 != "保持対応"))
        前 = 会話契約を形成(元, 所有セッション="人工所有")
        前写し = deepcopy(前)
        証明 = _証明(前)
        次 = HDS会話文節を形成(_基礎("それを三文で要約してください。"), 前採用包=前, 文脈証明=証明)
        新 = 会話契約を形成(次, 所有セッション="人工所有", 文脈証明=証明)
        self.assertEqual(会話目的を読む(新, 所有セッション="人工所有", 前採用包=前, 文脈証明=証明)[0]["保持"], ["数値", "例外"])
        self.assertEqual(前, 前写し)
        # 旧継続保存物は原範囲も対応辺も無い。現在の対応を保存済み旧包へ補わない。
        次 = replace(次, 関係=tuple(辺 for 辺 in 次.関係 if 辺.種別 != "保持対応"))
        旧継続 = 会話契約を形成(次, 所有セッション="人工所有", 文脈証明=証明)
        旧写し = deepcopy(旧継続)
        次証明 = [*_証明(旧継続), *証明]
        続 = HDS会話文節を形成(_基礎("それを四文で要約してください。"), 前採用包=旧継続, 文脈証明=次証明)
        保留 = 会話契約を形成(続, 所有セッション="人工所有", 文脈証明=次証明)
        with self.assertRaisesRegex(ValueError, "未消費残差.*実対応が一意"):
            会話目的を読む(保留, 所有セッション="人工所有", 前採用包=旧継続, 文脈証明=次証明)
        self.assertEqual(旧継続, 旧写し)


class 会話履歴純粋読取契約(TestCase):
    def 前(self, 二目的=False):
        文 = '「ラヘン」を二文で説明し、「セフィア」を三文で要約してください。' if 二目的 else '数値を保持し例外を省かずに二文で要約してください。'
        ir = HDS会話文節を形成(_基礎(文, None if 二目的 else '係員は荷物を二個検査する。ただし休日は検査しない。'))
        pkg = 会話契約を形成(ir, 所有セッション="人工所有")
        return pkg, _証明(pkg)

    def 履歴(self, pkg):
        return [{**項, "版": 会話命令証明版, "用途": "命令再実行", "原要求印": pkg["原文印"]} for 項 in _証明(pkg)]

    def 形成(self, 文, **文脈):
        ir = HDS会話文節を形成(_基礎(文), **文脈)
        pkg = 会話契約を形成(ir, 所有セッション="人工所有", 文脈証明=文脈.get("文脈証明", ()), 命令証明=文脈.get("命令証明", ()))
        return ir, pkg

    def test_命令再実行もrow5欄とcurrent問いを維持(self):
        元, _ = self.前()
        設定 = {"前命令包": 元, "命令証明": self.履歴(元)}
        ir, pkg = self.形成("再計算してください。", **設定)
        行 = 会話目的を読む(pkg, 所有セッション="人工所有", 意味IR=ir, **設定)[0]
        self.assertEqual(set(行), {"目的ID", "文節ID", "要求", "数量", "保持"})
        self.assertEqual(行["要求"]["問い"], "再計算してください。")
        self.assertEqual(行["要求"]["提示本文"], "")
        self.assertEqual(行["保持"], ["数値", "例外"])
        self.assertEqual(行["数量"], [{"単位": "文", "数": 2, "関係": "一致"}])
        対応 = 会話前目的対応を読む(pkg, 所有セッション="人工所有", **設定)[0]
        self.assertEqual(set(対応), {"目的ID", "元目的ID", "前束印", "原記録ID", "方式", "変更"})
        self.assertEqual((対応["方式"], 対応["元目的ID"]), ("再実行", 元["目的参照"][0]))

    def test_現行祖先を歴史証明で旧包検査し新ordinary参照へ流用しない(self):
        初, 初証明 = self.前()
        _, 次 = self.形成("それを三文で要約してください。", 前採用包=初, 文脈証明=初証明)
        歴史 = self.履歴(次) + self.履歴(初)
        設定 = {"前命令包": 次, "命令証明": 歴史}
        _, 再 = self.形成("もう一度", **設定)
        行 = 会話目的を読む(再, 所有セッション="人工所有", **設定)
        self.assertEqual(行[0]["数量"][0]["数"], 3)
        self.assertEqual(行[0]["保持"], ["数値", "例外"])
        # 保存された旧通常包は履歴適合で書き換えない。
        self.assertEqual(set(次["文脈束縛"][0]), {"前束印", "所有セッション", "原記録ID", "依存版", "参照"})
        with self.assertRaises(ValueError):
            HDS会話文節を形成(_基礎("それを四文で要約してください。"), 前採用包=次, 命令証明=歴史)

    def test_命令祖先を持つ普通継続は当前源一つと混合poolを許す(self):
        初, 初証明 = self.前()
        _, 次 = self.形成("それを三文で要約してください。", 前採用包=初, 文脈証明=初証明)
        歴史 = self.履歴(次) + self.履歴(初)
        _, 再 = self.形成("もう一度", 前命令包=次, 命令証明=歴史)
        設定 = {"前採用包": 再, "文脈証明": _証明(再), "命令証明": 歴史}
        _, 続 = self.形成("それを四文で要約してください。", **設定)
        行 = 会話目的を読む(続, 所有セッション="人工所有", **設定)
        self.assertEqual(行[0]["数量"][0]["数"], 4)
        self.assertEqual(行[0]["保持"], ["数値", "例外"])
        self.assertEqual(会話前目的対応を読む(続, 所有セッション="人工所有", **設定)[0]["方式"], "照応")

    def test_旧包自身への歴史証明や原要求印不足を拒否(self):
        初, 初証明 = self.前()
        _, 次 = self.形成("それを三文で要約してください。", 前採用包=初, 文脈証明=初証明)
        for 歴史 in (self.履歴(初), self.履歴(次), [{**項, "原要求印": "f" * 64} for 項 in self.履歴(次)] + self.履歴(初)):
            with self.subTest(履歴数=len(歴史)), self.assertRaises(ValueError):
                self.形成("もう一度", 前命令包=次, 命令証明=歴史)

    def test_再封緘した別元目的混合と旧役割取り落としを拒否(self):
        元, _ = self.前(True)
        設定 = {"前命令包": 元, "命令証明": self.履歴(元)}
        ir, _ = self.形成("再計算してください。", **設定)
        anchor = [項 for 項 in ir.関係 if 項.種別 == "命令再実行"]
        辺 = tuple(replace(項, 始点=anchor[1].始点) if 項.関係ID == anchor[0].関係ID else 項 for 項 in ir.関係)
        混合 = replace(ir, 関係=辺)
        包 = 会話契約を形成(混合, 所有セッション="人工所有", 命令証明=設定["命令証明"])
        with self.assertRaisesRegex(ValueError, "全目的"):
            会話目的を読む(包, 所有セッション="人工所有", **設定)
        コピー = next(項 for 項 in ir.座標 if 項.種別 == "表現.会話数量")
        参照ID = コピー.内容["前束参照"]
        欠落 = _座標群を替える(ir, ir.座標, 削除=(コピー.座標ID, 参照ID))
        包 = 会話契約を形成(欠落, 所有セッション="人工所有", 命令証明=設定["命令証明"])
        with self.assertRaisesRegex(ValueError, "取り落とし"):
            会話目的を読む(包, 所有セッション="人工所有", **設定)

    def test_純粋読取も二源混合と保存自己証明を拒否(self):
        元, 普通 = self.前()
        設定 = {"前命令包": 元, "命令証明": self.履歴(元)}
        _, pkg = self.形成("もう一度", **設定)
        with self.assertRaisesRegex(ValueError, "元源を混合"):
            会話目的を読む(pkg, 所有セッション="人工所有", 前採用包=元, 文脈証明=普通, **設定)
        with self.assertRaises(ValueError):
            会話目的を読む(pkg, 所有セッション="人工所有", 前命令包=元)

    def test_命令源は実用途が必要で祖先証明だけの供与と区別する(self):
        元, _ = self.前()
        ir = HDS会話文節を形成(_基礎('「人工ノエル」を二文で説明してください。'))
        pkg = 会話契約を形成(ir, 所有セッション="人工所有")
        for 源 in ({"任意": "未検査"}, 元):
            with self.subTest(源有効=源 == 元), self.assertRaisesRegex(ValueError, "実命令参照用途"):
                会話目的を読む(pkg, 所有セッション="人工所有", 前命令包=源, 命令証明=self.履歴(元))
        self.assertEqual(会話目的を読む(pkg, 所有セッション="人工所有", 命令証明=self.履歴(元))[0]["要求"]["主題"], ["人工ノエル"])

    def test_命令元にない作用と新役割の再封緘を拒否(self):
        元, _ = self.前()
        設定 = {"前命令包": 元, "命令証明": self.履歴(元)}
        ir, _ = self.形成("再計算してください。", **設定)
        群 = tuple(replace(項, 内容={**項.内容, "値": "説明", "根拠": "原文", "前束参照": None})
                  if 項.種別 == "目的.会話操作" else 項 for 項 in ir.座標)
        対照 = ((_座標群を替える(ir, 群), "作用が実元目的"),
              (_追加(ir, "表現.会話形式", "箇条書き", "表現適用", 範囲=(0, 2)), "新役割"))
        for 候補, 理由 in 対照:
            with self.subTest(理由=理由):
                包 = 会話契約を形成(候補, 所有セッション="人工所有", 命令証明=設定["命令証明"])
                with self.assertRaisesRegex(ValueError, 理由):
                    会話目的を読む(包, 所有セッション="人工所有", **設定)

    def test_再実行の全目的へanchorを要求し元目的の欠落と並替を拒否(self):
        元, _ = self.前(True)
        設定 = {"前命令包": 元, "命令証明": self.履歴(元)}
        ir, _ = self.形成("再計算してください。", **設定)
        文節 = next(項.座標ID for 項 in ir.座標 if 項.種別 == "対象.会話文節")
        新 = tuple(HDS座標("人工新:" + str(番号), 種,
                         {"値": 値, "原文": ir.原文[:2], "根拠": "原文", "前束参照": None},
                         原文範囲=(0, 2), 由来=会話射影由来)
                 for 番号, (種, 値) in enumerate((("目的.会話操作", "説明"), ("対象.会話主題", "ラヘン"))))
        追加 = _座標群を替える(ir, (*ir.座標, *新))
        追加 = replace(追加, 関係=(*追加.関係,
                              HDS関係("人工新所属", (文節,), (新[0].座標ID,), "文節所属", 由来=会話射影由来),
                              HDS関係("人工新対象", (新[0].座標ID,), (新[1].座標ID,), "要求対象", 由来=会話射影由来)))
        目的 = [項 for 項 in ir.座標 if 項.種別 == "目的.会話操作"]
        削除 = {目的[1].座標ID}
        for 辺 in ir.関係:
            if 辺.種別 == "命令再実行" and 辺.終点 == (目的[1].座標ID,): 削除.update(辺.始点)
            if 辺.種別 in {"要求対象", "表現適用"} and 目的[1].座標ID in 辺.始点 + 辺.終点:
                削除.update(set(辺.始点 + 辺.終点) - {目的[1].座標ID})
        for 項 in ir.座標:
            if 項.座標ID in 削除 and 項.内容["前束参照"] is not None: 削除.add(項.内容["前束参照"])
        欠落 = _座標群を替える(ir, ir.座標, 削除=削除)
        並替 = _座標群を替える(ir, tuple(目的[1] if 項.座標ID == 目的[0].座標ID else 目的[0]
                                    if 項.座標ID == 目的[1].座標ID else 項 for 項 in ir.座標))
        for 名前, 候補 in (("無anchor追加", 追加), ("元目的欠落", 欠落), ("元順入替", 並替)):
            with self.subTest(名前=名前):
                包 = 会話契約を形成(候補, 所有セッション="人工所有", 命令証明=設定["命令証明"])
                with self.assertRaisesRegex(ValueError, "全目的"):
                    会話目的を読む(包, 所有セッション="人工所有", **設定)


if __name__ == "__main__":
    main()

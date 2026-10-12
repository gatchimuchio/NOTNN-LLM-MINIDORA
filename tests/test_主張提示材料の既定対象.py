"""既定提示対象の人工構造対照。Compiler・製品・通信は実行しない。"""
from dataclasses import replace
from unittest import TestCase, main

from minidora.HDS中間表現 import HDSIR, HDS座標, HDS関係, HDS意味作用, HDS実行核
from minidora.HDS会話契約 import 会話契約を形成, 会話射影由来, 会話契約版, 会話主張要求版
from minidora.HDS運用.関係依頼 import 会話主張要求を読む


def _人工主張(形="既定"):
    主張 = "装置レカが回転する"
    接頭 = "資料「記録ナナ」から、" if 形 == "登録" else "次の記録から、" if 形 == "明示" else ""
    制御 = 接頭 + 主張 + "と確認してください。"
    原文 = 制御 if 形 == "登録" else 制御 + "\n\n" + 主張 + "。装置レカが停止する。"
    座標列, 辺列 = [], []
    def 座標(名, 種, 値, 範囲=None):
        座標列.append(HDS座標(名, 種, {"値": 値, "原文": 原文[slice(*範囲)] if 範囲 else "",
            "根拠": "原文" if 範囲 else "既定", "前束参照": None}, 原文範囲=範囲, 由来=会話射影由来))
    def 辺(始, 終, 種):
        辺列.append(HDS関係("辺:" + str(len(辺列)), (始,), (終,), 種, 由来=会話射影由来))
    位置 = 原文.index(主張)
    行為 = 原文.index("確認")
    座標("版", "言語.会話契約版", 会話契約版)
    座標("制御", "情報源.会話入力区分", "制御", (0, len(制御)))
    座標("文節", "対象.会話文節", 制御, (0, len(制御)))
    座標("目的", "目的.会話操作", "主張検討", (行為, 行為 + 4))
    座標("主張", "関係.会話問い焦点", 主張, (位置, 位置 + len(主張)))
    座標("行為", "条件.会話適用", {"役割": "問い条件", "値": {
        "版": 会話主張要求版, "行為": "支持確認"}}, (行為, 行為 + 4))
    辺("制御", "文節", "区分所属"); 辺("文節", "目的", "文節所属")
    辺("目的", "主張", "要求関係"); 辺("行為", "目的", "条件適用")
    if 形 == "登録":
        始 = 原文.index("記録ナナ")
        範囲 = (始, 始 + len("記録ナナ"))
        座標("対象", "対象.会話資料", "記録ナナ", 範囲)
        座標("範囲", "条件.会話範囲", "指定資料", 範囲)
        辺("目的", "範囲", "要求範囲")
    else:
        座標("区切り", "情報源.会話入力区分", "区切り", (len(制御), len(制御) + 2))
        座標("材料", "情報源.会話入力区分", "提示本文", (len(制御) + 2, len(原文)))
        辺("材料", "目的", "材料適用")
        座標("対象", "対象.会話資料", "提示本文", (0, len("次の記録")) if 形 == "明示" else None)
    辺("目的", "対象", "要求対象")
    作用 = HDS意味作用("会話作用射影:v3", "会話作用抽出-v3", (), tuple(項.座標ID for 項 in 座標列),
        "人工構造対照", ("原文", "原文範囲", "未消費条件"), (), ("人工構造対照",))
    return HDSIR(原文, 原文, "cw:既定提示人工", tuple(座標列), tuple(辺列), (), (作用,), HDS実行核())


def _読む(ir):
    包 = 会話契約を形成(ir, 所有セッション="既定提示人工")
    return 会話主張要求を読む(包, 所有セッション="既定提示人工", 期待原文=ir.原文, 意味IR=ir)


class 主張提示対象の境界(TestCase):
    def test_材料適用が実証する一意の既定提示対象を読む(self):
        ir = _人工主張()
        接続 = _読む(ir)
        self.assertEqual(接続["資料"]["方式"], "提示原文")
        self.assertEqual(接続["資料"]["区分ID"], "材料")
        self.assertEqual(接続["資料"]["本文"], ir.原文[slice(*接続["資料"]["原文範囲"])])
        self.assertEqual(接続["要求"]["対象"], ["提示本文"])

    def test_任意の資料名を範囲なしの既定対象へ偽装できない(self):
        ir = _人工主張()
        ir = replace(ir, 座標=tuple(replace(項, 内容={**項.内容, "値": "記録偽"})
            if 項.座標ID == "対象" else 項 for 項 in ir.座標))
        with self.assertRaises(ValueError):
            _読む(ir)

    def test_既定提示対象でも実材料適用を欠けば拒否する(self):
        ir = _人工主張()
        ir = replace(ir, 関係=tuple(辺 for 辺 in ir.関係 if 辺.種別 != "材料適用"))
        with self.assertRaises(ValueError):
            _読む(ir)

    def test_明示提示対象の原範囲だけを落とせない(self):
        ir = _人工主張("明示")
        ir = replace(ir, 座標=tuple(replace(項, 原文範囲=None)
            if 項.座標ID == "対象" else 項 for 項 in ir.座標))
        with self.assertRaises(ValueError):
            _読む(ir)

    def test_資料内の別主張へ原主張を移植しても拒否する(self):
        ir = _人工主張()
        別 = "装置レカが停止する"
        始 = ir.原文.index(別)
        ir = replace(ir, 座標=tuple(replace(項, 原文範囲=(始, 始 + len(別)),
            内容={**項.内容, "値": 別, "原文": 別}) if 項.座標ID == "主張" else 項 for 項 in ir.座標))
        with self.assertRaisesRegex(ValueError, "制御文節"):
            _読む(ir)

    def test_通常の制御内明示提示対象を保持する(self):
        接続 = _読む(_人工主張("明示"))
        self.assertEqual(接続["資料"]["方式"], "提示原文")
        self.assertEqual(接続["要求"]["問い"], "装置レカが回転する")

    def test_通常の制御内明示登録対象を保持する(self):
        接続 = _読む(_人工主張("登録"))
        self.assertEqual(接続["資料"]["方式"], "登録資料")
        self.assertEqual(接続["要求"]["対象"], ["記録ナナ"])


if __name__ == "__main__":
    main()

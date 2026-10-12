"""停止伝達と意味入力指紋の分離。人工取得をWeb受入へ算入しない。"""
from copy import deepcopy
from types import SimpleNamespace
import unittest

from minidora.能力合成 import _文脈辞書, _結果辞書
from minidora.HDS運用.工程 import 工程供給
from minidora.HDS運用.セッション import HDS運用セッション
from minidora.HDS運用.値 import 結果を保存
from minidora.HDS運用.関係依頼 import 関係依頼を読む
from minidora.HDS運用.関係読解 import 関係資料を読む
from minidora.HDS運用.関係接続 import 関係資料能力
from minidora.知識取得 import 知識取得器
from minidora.知識取得接続 import 知識取得モジュール
from minidora.製品版.能力契約 import 能力文脈
from minidora.製品版.型 import 能力結果


class 無通信供給:
    def __init__(self):
        self.呼出 = []

    def 検索(self, query, limit=5):
        self.呼出.append(("検索", query))
        return ()

    def 取得(self, url):
        self.呼出.append(("本文", url))
        raise AssertionError("停止後の本文取得")


class 観測取得器:
    def __init__(self, 取得器):
        self.取得器 = 取得器
        self.停止群 = []

    def 実行(self, 要求, *, 外部読取許可=False, 停止要求=None):
        self.停止群.append(停止要求)
        return self.取得器.実行(要求, 外部読取許可=外部読取許可, 停止要求=停止要求)


class 取得停止接続試験(unittest.TestCase):
    def setUp(self):
        self.供給 = 無通信供給()
        self.取得 = 観測取得器(知識取得器(self.供給, self.供給))

    def test_一般取得は元停止関数で無通信保留(self):
        停止 = lambda: True
        文脈 = 能力文脈("人工取得", "停止", 補助={"合成設定": {
            "検索語": "試験主題", "必要語": ["試験主題"]}}, 停止要求=停止)
        結果 = 知識取得モジュール(self.取得, 外部読取許可=True).実行(deepcopy(文脈))
        self.assertFalse(結果.成立)
        self.assertEqual(結果.保留理由, "停止要求")
        self.assertIs(self.取得.停止群[0], 停止)
        self.assertEqual(self.供給.呼出, [])

    def test_停止判定の不正型や故障を通信へ逃がさない(self):
        def 故障():
            raise RuntimeError("試験内部値")
        for 停止 in (lambda: "false", 故障):
            with self.subTest():
                文脈 = 能力文脈("人工取得", "停止", 補助={"合成設定": {
                    "検索語": "試験主題", "必要語": ["試験主題"]}}, 停止要求=停止)
                結果 = 知識取得モジュール(self.取得, 外部読取許可=True).実行(文脈)
                self.assertFalse(結果.成立)
                self.assertNotIn("試験内部値", str(結果))
                self.assertIs(self.取得.停止群[-1], 停止)
        self.assertEqual(self.供給.呼出, [])

    def test_関係不足取得も同じ停止関数で無通信(self):
        文 = '資料「手順」をもとに、装置Aが稼働するかどうか説明して、不足は公開資料で調べて'
        読解 = 関係依頼を読む({"原文": 文})
        構造 = 関係資料を読む({"手順": 能力結果(True, "装置Aは有効である。")}, 読解["要求"])
        停止 = lambda: True
        文脈 = 能力文脈("人工関係取得", "停止", 補助={"合成入力": (
            {"結果": _結果辞書(能力結果(True, "", データ=構造))},)}, 停止要求=停止)
        結果 = 関係資料能力("関係不足資料取得", self.取得, 外部許可=True).実行(deepcopy(文脈))
        self.assertTrue(結果.成立, 結果.保留理由)
        self.assertIs(self.取得.停止群[0], 停止)
        self.assertEqual(self.供給.呼出, [])
        self.assertEqual(結果.データ["取得"]["内容"]["保留理由"], "停止要求")

    def test_工程の複製で停止は同一当回に保ち意味入力には含めない(self):
        停止 = lambda: False
        bridge = 工程供給(None, 停止要求=停止)
        状態 = SimpleNamespace(成果=(("運用入力", {"セッションID": "停止"}),))
        packet = {"資料": {"指示": 結果を保存(能力結果(True, "試験主題"))}}
        step = SimpleNamespace(入力=(), 設定参照=None, 指示参照="指示")
        文脈 = bridge._文脈(状態, "人工", packet, step)
        複製 = deepcopy(文脈)
        self.assertIs(文脈.停止要求, 停止)
        self.assertIs(複製.停止要求, 停止)
        無制御 = 能力文脈(文脈.入力文, 文脈.セッションID, 文脈.直前応答,
                       文脈.直前参照, 文脈.履歴, deepcopy(文脈.補助))
        self.assertEqual(_文脈辞書(文脈), _文脈辞書(無制御))
        self.assertNotIn("停止要求", _文脈辞書(文脈))

    def test_HDS当回期限の停止関数は取得へ届き次要求へ共有しない(self):
        会話 = HDS運用セッション("当回停止", 外部読取許可=True, 取得器=self.取得, 手順形成=False)
        for _ in range(2):
            応答 = 会話.応答("試験主題とは何ですか", 外部読取許可=True, 期限秒=120)
            self.assertFalse(応答.成立)
        self.assertEqual(len(self.取得.停止群), 2)
        self.assertTrue(all(callable(停止) for 停止 in self.取得.停止群))
        self.assertIsNot(self.取得.停止群[0], self.取得.停止群[1])
        self.assertNotIn("停止要求", str(会話.保存()))


if __name__ == "__main__":
    unittest.main()

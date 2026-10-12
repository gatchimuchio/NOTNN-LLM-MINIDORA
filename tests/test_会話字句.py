"""原文identity・固定辞書・字句型・並行供給の有限契約。意味採否は検査しない。"""
from concurrent.futures import ThreadPoolExecutor
from dataclasses import FrozenInstanceError, replace
from hashlib import sha256
from pathlib import Path
import tempfile
import threading
import time
from unittest import TestCase, main
from unittest.mock import patch

import minidora.会話字句 as 字句供給
from minidora.会話字句 import 会話字句を観測, 会話字句候補, 会話字句不成立


class 会話字句契約(TestCase):
    def test_原表層と文字位置全覆を保つ(self):
        for 本文 in (
            "😀🧑‍🔬がペルミラトヌーザを記録した。",
            "雲海（うんかい）を撮り、仮名の表記を保管した。",
            "記録名「か\u3099まる」を保管した。",
            "ＡＢＣの附属品をとりつけました。",
            "机の右に紙がある。\n\t箱もある。",
        ):
            with self.subTest(本文=本文):
                列 = 会話字句を観測(本文)
                self.assertIs(type(列), tuple)
                self.assertEqual("".join(項.表層 for 項 in 列), 本文)
                前 = 0
                for 項 in 列:
                    self.assertIs(type(項), 会話字句候補)
                    self.assertEqual(項.開始, 前)
                    self.assertEqual(項.表層, 本文[項.開始:項.終了])
                    self.assertEqual(len(項.品詞), 6)
                    self.assertEqual(項.辞書版, "20260723")
                    self.assertEqual(項.処理器版, "0.6.11")
                    self.assertFalse(hasattr(項, "正規形"))
                    前 = 項.終了
                self.assertEqual(前, len(本文))
                with self.assertRaises(FrozenInstanceError):
                    列[0].表層 = "置換"

    def test_連体詞内の文字を属格へ分割しない(self):
        列 = 会話字句を観測("この紙を移した。")
        self.assertEqual(列[0].表層, "この")
        self.assertEqual(列[0].品詞[0], "連体詞")
        self.assertFalse(any(項.表層 == "の" for 項 in 列))

    def test_活用と未知語は原位置付き観測のまま(self):
        列 = 会話字句を観測("観測者は棚を動かしていなかった。")
        否定 = next(項 for 項 in 列 if 項.表層 == "なかっ")
        self.assertEqual(否定.辞書形, "ない")
        self.assertEqual(否定.活用型, "助動詞-ナイ")
        self.assertEqual((否定.活用型, 否定.活用形), 否定.品詞[4:6])
        未知 = [項 for 項 in 会話字句を観測("ペルミラトヌーザを記録した。") if 項.未知語]
        self.assertTrue(未知)
        self.assertTrue(all(項.辞書ID == -1 for 項 in 未知))
        self.assertFalse(any(hasattr(項, "役割") or hasattr(項, "能力") for 項 in 未知))

    def test_全項目を厳密型で受ける(self):
        項 = 会話字句を観測("紙")[0]
        不正 = (
            {"表層": 1}, {"辞書形": None}, {"活用型": False}, {"活用形": []},
            {"開始": True}, {"終了": 1.0}, {"終了": 2}, {"未知語": 1}, {"辞書ID": False},
            {"辞書版": 20260723}, {"処理器版": None},
            {"品詞": list(項.品詞)}, {"品詞": (*項.品詞[:5], None)},
            {"品詞": 項.品詞[:5]}, {"活用形": "不一致"}, {"辞書版": "20260723.1"},
            {"辞書ID": -1, "未知語": False},
        )
        for 変更 in 不正:
            with self.subTest(変更=変更), self.assertRaises(会話字句不成立):
                replace(項, **変更)

    def test_入力型符号化容量は解析前に拒否(self):
        class 派生文字列(str):
            pass
        for 本文 in (None, 1, True, b"a", 派生文字列("a"), "\ud800",
                     "a" * (字句供給._入力バイト上限 + 1), "あ" * (字句供給._入力バイト上限 // 3 + 1)):
            with self.subTest(型=type(本文).__name__), patch.object(字句供給, "_字句を初期化") as 初期化:
                with self.assertRaises(会話字句不成立):
                    会話字句を観測(本文)
                初期化.assert_not_called()
        self.assertEqual(会話字句を観測(""), ())

    def test_未導入と異版は具体不成立(self):
        with patch.object(字句供給.配布情報, "version", return_value="0.7.0"):
            with self.assertRaisesRegex(会話字句不成立, "固定配布版不一致"):
                会話字句を観測("紙")
        with patch.object(字句供給.配布情報, "version", side_effect=字句供給.配布情報.PackageNotFoundError("SudachiPy")):
            with self.assertRaisesRegex(会話字句不成立, "未導入"):
                会話字句を観測("紙")

    def test_固定辞書ヘッダーと指紋と読取中変化を拒否(self):
        with tempfile.TemporaryDirectory() as 先:
            経路 = Path(先) / "system.dic"
            with patch.object(字句供給, "_辞書容量", 8):
                経路.write_bytes(b"12345678")
                with self.assertRaisesRegex(会話字句不成立, "ヘッダー"):
                    字句供給._固定辞書を検査(経路)
                経路.write_bytes(字句供給._辞書先頭)
                with self.assertRaisesRegex(会話字句不成立, "SHA256"):
                    字句供給._固定辞書を検査(経路)
                with patch.object(字句供給, "_辞書印", sha256(字句供給._辞書先頭).hexdigest()):
                    self.assertEqual(字句供給._固定辞書を検査(経路)[0], 8)
                    with patch.object(字句供給, "_ファイル状態", side_effect=[(8, 1, 1, 1), (8, 2, 1, 1)]):
                        with self.assertRaisesRegex(会話字句不成立, "読取中状態"):
                            字句供給._固定辞書を検査(経路)

    def test_初期化失敗を旧正規表現へ置換しない(self):
        with patch.object(字句供給, "_供給状態", None), patch.object(字句供給, "_字句を初期化", side_effect=OSError("辞書なし")):
            with self.assertRaisesRegex(会話字句不成立, "初期化不成立:OSError") as 検査:
                会話字句を観測("紙")
            self.assertIsInstance(検査.exception.__cause__, OSError)

    def test_解析失敗と原文字範囲の間隙を拒否(self):
        実状態 = 字句供給._供給状態
        if 実状態 is None:
            会話字句を観測("紙")
            実状態 = 字句供給._供給状態
        class 偽字句:
            def begin(self): return 1
            def end(self): return 2
            def surface(self): return "紙"
            def part_of_speech(self): return ("名詞", "普通名詞", "一般", "*", "*", "*")
        class 間隙供給:
            def tokenize(self, 本文): return [偽字句()]
        with patch.object(字句供給, "_供給状態", replace(実状態, 解析器=間隙供給())):
            with self.assertRaisesRegex(会話字句不成立, "原slice又は隣接全覆"):
                会話字句を観測("紙紙")
        class 失敗供給:
            def tokenize(self, 本文): raise RuntimeError("解析不能")
        with patch.object(字句供給, "_供給状態", replace(実状態, 解析器=失敗供給())):
            with self.assertRaisesRegex(会話字句不成立, "解析不成立:RuntimeError"):
                会話字句を観測("紙")

    def test_同一字句解析器の並行使用を直列化する(self):
        会話字句を観測("紙")
        実状態 = 字句供給._供給状態
        観測鍵 = threading.Lock()
        使用中 = 最大使用 = 0
        class 観測供給:
            def tokenize(self, 本文):
                nonlocal 使用中, 最大使用
                with 観測鍵:
                    使用中 += 1
                    最大使用 = max(最大使用, 使用中)
                try:
                    time.sleep(0.002)
                    return 実状態.解析器.tokenize(本文)
                finally:
                    with 観測鍵:
                        使用中 -= 1
        with patch.object(字句供給, "_供給状態", replace(実状態, 解析器=観測供給())):
            with ThreadPoolExecutor(max_workers=4) as 群:
                結果 = list(群.map(会話字句を観測, ["紙を置いた。"] * 8))
        self.assertEqual(最大使用, 1)
        self.assertTrue(all(列 == 結果[0] for 列 in 結果))


if __name__ == "__main__":
    main()

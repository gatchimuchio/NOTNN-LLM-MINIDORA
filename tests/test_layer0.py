import unittest

from minidora import Layer0, 作用, 命令, 手順


class Layer0試験(unittest.TestCase):
    def test_加算と比較(self):
        手順_ = 手順("算術", (
            命令("和", 作用.加算, 引数=(2, 3, 4), 更新先="結果"),
            命令("比較", 作用.比較, 引数=("$結果", "同値", 9), 更新先="一致"),
        ))
        文脈 = Layer0().実行(手順_)
        self.assertEqual(文脈.状態["結果"], 9)
        self.assertTrue(文脈.状態["一致"])

    def test_交換(self):
        手順_ = 手順("交換", (命令("交換", 作用.交換, 引数=("A", "B")),))
        文脈 = Layer0().実行(手順_, {"A": "赤", "B": "青"})
        self.assertEqual(文脈.状態, {"A": "青", "B": "赤"})


if __name__ == "__main__":
    unittest.main()

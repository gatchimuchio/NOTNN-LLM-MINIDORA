import unittest

from minidora import ミニドラ, 要求, 手順, 命令, 作用, 参照記録, 固定参照供給器, 実行状態


class Runtime試験(unittest.TestCase):
    def test_参照を標準データ層として利用(self):
        provider = 固定参照供給器((参照記録("k3", "K3", "総層数は93", "fixture://k3", "固定"),))
        手順_ = 手順("結果形成", (命令("値設定", 作用.設定, 引数=(93,), 更新先="結果"),))
        result = ミニドラ(provider).実行(要求("K3 総層数", 手順_, 参照必須=True))
        self.assertEqual(result.値, 93)
        self.assertEqual(result.採否.状態, 実行状態.合格)
        self.assertEqual(result.参照[0].識別子, "k3")
        self.assertEqual(result.主体状態.主体ID, "MINIDORA")

    def test_参照必須で未取得なら保留(self):
        provider = 固定参照供給器(())
        手順_ = 手順("何もしない", ())
        result = ミニドラ(provider).実行(要求("未知", 手順_, 参照必須=True))
        self.assertEqual(result.採否.状態, 実行状態.保留)
        self.assertEqual(result.主体整合.状態, 実行状態.非適用)

    def test_結果形成なしは合格へ昇格しない(self):
        result = ミニドラ().実行(要求("未知", 手順("空", ())))
        self.assertIsNone(result.値)
        self.assertEqual(result.採否.状態, 実行状態.保留)

    def test_矛盾文脈は保留(self):
        手順_ = 手順("結果形成", (命令("値設定", 作用.設定, 引数=("候補",), 更新先="結果"),))
        result = ミニドラ().実行(要求("矛盾", 手順_, 矛盾数=1))
        self.assertIsNone(result.値)
        self.assertEqual(result.採否.状態, 実行状態.保留)

    def test_境界違反は失敗(self):
        手順_ = 手順("結果形成", (命令("値設定", 作用.設定, 引数=("候補",), 更新先="結果"),))
        result = ミニドラ().実行(要求("境界", 手順_, 境界違反=True))
        self.assertIsNone(result.値)
        self.assertEqual(result.採否.状態, 実行状態.失敗)


if __name__ == "__main__":
    unittest.main()

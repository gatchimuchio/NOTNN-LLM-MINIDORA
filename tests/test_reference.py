import unittest

from minidora import 参照記録, 固定参照供給器, 複合参照供給器


class 参照試験(unittest.TestCase):
    def test_固定参照検索(self):
        p = 固定参照供給器((
            参照記録("1", "東京", "日本の首都", "fixture://1", "固定"),
            参照記録("2", "大阪", "日本の都市", "fixture://2", "固定"),
        ))
        hit = p.検索("東京 首都")
        self.assertEqual(hit[0].識別子, "1")

    def test_複合参照重複除去(self):
        r = 参照記録("x", "K3", "資料", "fixture://x", "固定")
        p = 複合参照供給器(固定参照供給器((r,)), 固定参照供給器((r,)))
        self.assertEqual(len(p.検索("K3")), 1)


if __name__ == "__main__":
    unittest.main()

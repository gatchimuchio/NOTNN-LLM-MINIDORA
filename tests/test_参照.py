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

    def test_複合参照は先頭Providerだけで上限を埋めない(self):
        p1 = 固定参照供給器(
            tuple(
                参照記録(f"a{i}", "Alpha", f"Alpha source {i}", f"fixture://a/{i}", "A")
                for i in range(8)
            ),
            名称="A",
        )
        p2 = 固定参照供給器(
            tuple(
                参照記録(f"b{i}", "Alpha", f"Alpha independent {i}", f"fixture://b/{i}", "B")
                for i in range(8)
            ),
            名称="B",
        )
        result = 複合参照供給器(p1, p2).検索("Alpha", 上限=4)
        self.assertEqual([r.識別子 for r in result], ["a0", "b0", "a1", "b1"])
        self.assertEqual({r.供給器 for r in result}, {"A", "B"})

    def test_空Providerがあっても他Providerを取得する(self):
        empty = 固定参照供給器((), 名称="empty")
        record = 参照記録("b", "Alpha", "Alpha evidence", "fixture://b", "B")
        result = 複合参照供給器(empty, 固定参照供給器((record,), 名称="B")).検索("Alpha")
        self.assertEqual(result, (record,))


if __name__ == "__main__":
    unittest.main()

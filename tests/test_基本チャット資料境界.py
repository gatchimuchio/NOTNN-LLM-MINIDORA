"""原文を改変しない会話v2の表示境界。v1保存物の境界は維持する。"""
import unittest

from minidora.HDS運用.意味資料 import 資料を区分


class 会話資料境界試験(unittest.TestCase):
    def test_数式の関数適用字を原文区間に残す(self):
        本文 = '# 定義\n交流は向きが変わる電流。\n\n# 式\nsin\u2061(x)\n'
        区分 = 資料を区分(本文, 会話本文=True)
        self.assertEqual(''.join(本文[節['開始']:節['終了']] for 節 in 区分), 本文)
        self.assertIn('\u2061', 本文[区分[1]['開始']:区分[1]['終了']])
        with self.assertRaises(ValueError):
            資料を区分(本文)

    def test_丸括弧の幅が混在しても元の文字と位置を保持する(self):
        本文 = '記念柱(113年）は彫刻。別の柱（115年)も彫刻。'
        区分 = 資料を区分(本文, 会話本文=True)
        self.assertEqual(区分, [{'開始': 0, '終了': len(本文), '階層': []}])
        self.assertEqual(本文[区分[0]['開始']:区分[0]['終了']], 本文)
        with self.assertRaises(ValueError):
            資料を区分(本文)

    def test_未知制御字や他の引用不一致を受理しない(self):
        for 本文 in ('甲\u200bは部品。', '甲\u202eは部品。', '甲\x00は部品。',
                     '「甲）', '(甲」', '(甲', '甲)'):
            with self.subTest(本文=本文), self.assertRaises(ValueError):
                資料を区分(本文, 会話本文=True)

    def test_会話指定は厳密な真偽値に限る(self):
        for 指定 in (1, 'true', None):
            with self.subTest(指定=指定), self.assertRaises(ValueError):
                資料を区分('甲は部品。', 会話本文=指定)


if __name__ == '__main__':
    unittest.main()

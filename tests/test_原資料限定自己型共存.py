"""自己述定と別根拠族の未読限定を同時に保持する有限対照。"""
from copy import deepcopy
import unittest
from test_原資料条件作用 import 読む
from minidora.HDS運用.資料作用射影 import 条件作用を結ぶ

class 限定自己型共存試験(unittest.TestCase):
    def test_名詞内部の同形文字を限定採用せず自己型と残差を保つ(self):
        行群 = 読む('資料は恐らく旅のみちしるべに違いない。')
        射影 = 行群[0]['資料作用']
        self.assertIn('自己述定証明', 射影['局所範囲'])
        self.assertEqual(射影['局所限定']['読解']['状態'], '未読')
        self.assertEqual(射影['局所限定']['読解']['全候補'], [])
        self.assertTrue(any(x['種別']=='原資料限定作用域未読' for x in 射影['残差']))
        原 = deepcopy(行群)
        条件作用を結ぶ(行群)
        self.assertEqual(行群, 原)
        for 種別 in ('欠落', '改変', '余分'):
            改 = deepcopy(原)
            残差 = 改[0]['資料作用']['残差']
            if 種別 == '欠落':
                残差.clear()
            elif 種別 == '改変':
                残差[0]['原内容'] = '別の原句'
            else:
                余分=deepcopy(残差[0]);余分['残差ID']+=':余分';残差.append(余分)
            with self.subTest(種別=種別), self.assertRaises(ValueError):
                条件作用を結ぶ(改)

if __name__ == '__main__':
    unittest.main()

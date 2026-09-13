"""実際の有限命題能力で、キャッシュ再利用と意味結果を別々に確認する。"""
from copy import deepcopy
from dataclasses import replace
import unittest

from minidora.能力合成 import _結果辞書, _符号化, 登録能力
from minidora.製品版.型 import 能力結果, 参照資料
from minidora.製品版.能力契約 import 能力文脈
from minidora.純粋結果庫 import 純粋結果庫
from minidora.純粋再利用 import 純粋再利用能力
from minidora.監査改善接続 import 監査改善Module
from minidora.監査改善計画 import 改善統合能力群, 改善目的を計画
from minidora.統合実行 import 統合セッション


def original(query='Q'):
    ref = 参照資料('src', '例', '利用者提供資料', 本文='P。PならばQ。')
    return 能力結果(True, '明示資料から判定', 根拠=('src',), 参照=(ref,),
        データ={'資料': [{'名前': '例', '本文': ref.本文}], '問い': query})


def context(query='Q'):
    obj = original(query)
    return 能力文脈('明示範囲で検討する', 'cache', 直前参照=obj.参照,
        補助={'合成入力': ({'参照': {'領域': '入力', '識別子': '原要求'}, '結果': _結果辞書(obj)},), '合成設定': {}})


class 純粋再利用回帰試験(unittest.TestCase):
    def setUp(self):
        self.module = 監査改善Module('拡張命題検討')
        self.cache = 純粋結果庫()
        self.wrapper = 純粋再利用能力(self.module, self.cache)

    def test_実能力の再利用で意味全体が一致し原実行が減る(self):
        one = self.wrapper.実行(context()); two = self.wrapper.実行(context())
        self.assertTrue(one.成立); self.assertEqual(_結果辞書(one), _結果辞書(two))
        stats = self.cache.統計()['能力別'][self.module.名前]
        self.assertEqual(stats, {'要求': 2, '再利用': 1, '原実行': 1})

    def test_問い変更を同一本文キャッシュとして取り違えない(self):
        one = self.wrapper.実行(context()); two = self.wrapper.実行(context('R'))
        self.assertNotEqual(_結果辞書(one), _結果辞書(two))
        self.assertEqual(self.cache.統計()['能力別'][self.module.名前]['再利用'], 0)

    def test_返却値の改変がキャッシュ内部に届かない(self):
        one = self.wrapper.実行(context()); expected = deepcopy(_結果辞書(one))
        one.データ['状態'] = '改変'
        self.assertEqual(_結果辞書(self.wrapper.実行(context())), expected)

    def test_未知設定で失敗した結果を再利用しない(self):
        data = context(); data.補助['合成設定']['未対応'] = True
        for _ in range(2):
            self.assertFalse(self.wrapper.実行(data).成立)
        self.assertEqual(self.cache.統計()['件数'], 0)
        self.assertEqual(self.cache.統計()['能力別'][self.module.名前]['原実行'], 2)

    def test_明示無効時はキャッシュに保存しない(self):
        store = 純粋結果庫(有効=False); wrapper = 純粋再利用能力(self.module, store)
        self.assertEqual(_結果辞書(wrapper.実行(context())), _結果辞書(wrapper.実行(context())))
        self.assertEqual(store.統計()['件数'], 0)
        self.assertEqual(store.統計()['能力別'][self.module.名前]['原実行'], 2)

    def test_登録後の版変更はヒットでも拒否する(self):
        self.wrapper.実行(context()); self.module.版 = 'changed'
        with self.assertRaises(ValueError):
            self.wrapper.実行(context())

    def test_文脈と参照の差を鍵から落とさない(self):
        self.wrapper.実行(context())
        for altered in (replace(context(), 直前応答='新しい文脈'),
                        replace(context(), 直前参照=(replace(original().参照[0], 本文='R。'),))):
            self.wrapper.実行(altered)
        self.assertEqual(self.cache.統計()['能力別'][self.module.名前]['原実行'], 3)


class 意味射影試験(unittest.TestCase):
    def setUp(self):
        self.session = 統合セッション('projection', 基底能力=改善統合能力群())
        plan = 改善目的を計画('命題', original(), self.session.能力一覧())
        self.reply = self.session.計画実行(plan.計画, plan.Data)
        self.assertTrue(self.reply.成立, self.reply.理由)

    def test_計測だけの変化は意味比較を変えない(self):
        changed = replace(self.reply, 計測={'実行時間ns': 0, '再利用': 1})
        self.assertNotEqual(self.reply.辞書化(), changed.辞書化())
        self.assertEqual(self.reply.意味辞書化(), changed.意味辞書化())

    def test_本文根拠採否の差は全て検出する(self):
        key, value = self.reply.出力[0]
        alternatives = (replace(self.reply, 本文='別回答'), replace(self.reply, 状態='保留'),
            replace(self.reply, 理由='未成立'),
            replace(self.reply, 出力=((key, replace(value, 根拠=())),)),
            replace(self.reply, 出力=((key, replace(value, 参照=())),)))
        for changed in alternatives:
            self.assertNotEqual(self.reply.意味辞書化(), changed.意味辞書化())

    def test_意味データの計算量という名前を勝手に除外しない(self):
        key, value = self.reply.出力[0]
        one = replace(self.reply, 出力=((key, replace(value, データ={**value.データ, '計算量': 1})),))
        two = replace(self.reply, 出力=((key, replace(value, データ={**value.データ, '計算量': 2})),))
        self.assertNotEqual(one.意味辞書化(), two.意味辞書化())

    def test_射影を変更しても元の結果を変えない(self):
        baseline = _符号化(self.reply.辞書化())
        projected = self.reply.意味辞書化(); projected['出力'].clear()
        self.assertEqual(_符号化(self.reply.辞書化()), baseline)

    def test_実統合器の二回実行も全意味一致で再利用する(self):
        # 実Moduleを明示して再利用化。未取得の標準全能力factoryは代用しない。
        cache = 純粋結果庫()
        group = tuple(登録能力(純粋再利用能力(r.Module, cache)) for r in 改善統合能力群())
        session = 統合セッション('twice', 基底能力=group)
        plan = 改善目的を計画('命題', original(), session.能力一覧())
        one = session.計画実行(plan.計画, plan.Data)
        first = cache.統計()
        two = session.計画実行(plan.計画, plan.Data)
        second = cache.統計()
        self.assertTrue(one.成立, one.理由); self.assertTrue(two.成立, two.理由)
        self.assertEqual(one.意味辞書化(), two.意味辞書化())
        self.assertNotEqual(one.辞書化()['採用記録ID'], two.辞書化()['採用記録ID'])
        self.assertGreater(sum(r['再利用'] for r in second['能力別'].values()),
                           sum(r['再利用'] for r in first['能力別'].values()))
        self.assertEqual(sum(r['原実行'] for r in first['能力別'].values()),
                         sum(r['原実行'] for r in second['能力別'].values()))
        self.assertTrue(one.実行.監査整合()); self.assertTrue(two.実行.監査整合())


if __name__ == '__main__':
    unittest.main()

"""長文脈選択→既存能力の実接続。原記録だけが人工入力。"""
from dataclasses import asdict, replace
import json
from pathlib import Path
import runpy
import subprocess
import sys
import unittest

from minidora.長文脈管理 import 長文脈庫, 文脈登録, 文脈選択要求
from minidora.長文脈接続 import 長文脈選択Module, 長文脈要求Data
from minidora.能力合成 import 能力合成器, 合成計画, 合成工程, 素材参照
from minidora.能力合成_局所接続 import 局所能力群
from minidora.製品版.型 import 能力結果
from minidora.製品版.能力契約 import 能力文脈

ROOT = Path(__file__).resolve().parents[1]
DEMO = runpy.run_path(str(ROOT / 'tools/長文脈デモ.py'))


class 長文脈合成試験(unittest.TestCase):
    def setUp(self):
        self.a = DEMO['用意']()

    def test_直近外の実本文を既存抽出へ渡す(self):
        result = DEMO['抽出'](self.a)
        self.assertTrue(result.成立, result.理由)
        self.assertEqual(result.出力[0][1].本文, '120、75、45')
        self.assertEqual([e.能力 for e in result.履歴], ['長文脈選択', '情報抽出'])
        self.assertTrue(result.監査整合())

    def test_未保存では後段を呼ばない(self):
        result = DEMO['抽出'](長文脈庫('長文脈デモ'))
        self.assertFalse(result.成立)
        self.assertNotIn('情報抽出', [e.能力 for e in result.履歴])
        self.assertEqual(result.出力, ())

    def test_値摂動が後続の結果へ到達(self):
        for n in (0, 9, 731, 10007):
            with self.subTest(n=n):
                result = DEMO['抽出'](DEMO['用意'](n))
                self.assertTrue(result.成立, result.理由)
                self.assertEqual(result.出力[0][1].本文, f'{n}、75、45')

    def test_原記録復元後も同じ機構で動く(self):
        restored = 長文脈庫.復元(self.a.保存文字列())
        result = DEMO['抽出'](restored)
        self.assertTrue(result.成立)
        self.assertEqual(result.出力[0][1].本文, '120、75、45')

    def test_改訂して旧値を使わない(self):
        self.a.更新(self.a.起点(), (文脈登録('新資料', DEMO['原文'](731)),),
                    失効ID=('原資料',), 理由='明示訂正')
        old = DEMO['抽出'](self.a)
        new = DEMO['抽出'](self.a, '新資料')
        self.assertFalse(old.成立)
        self.assertTrue(new.成立)
        self.assertEqual(new.出力[0][1].本文, '731、75、45')

    def test_原典参照が選択を越えて伝播する(self):
        result = DEMO['抽出'](self.a)
        self.assertEqual(result.出力[0][1].参照[0].本文, '売上は120です。費用は75です。利益は45です。')

    def context(self, data=None, session=None, settings=None):
        from minidora.能力合成 import _結果辞書
        data = data or 長文脈要求Data(self.a, 文脈選択要求(('原資料',), 直近件数=0))
        return 能力文脈('', session or '長文脈デモ', 補助={
            '合成設定': {} if settings is None else settings,
            '合成入力': ({'結果': _結果辞書(data)},)})

    def test_旧改訂のDataを実行しない(self):
        context = self.context()
        self.a.更新(self.a.起点(), (文脈登録('追加', 能力結果(True, '追加')),))
        module = 長文脈選択Module(self.a)
        self.assertEqual(module.判定(context), 0)
        self.assertFalse(module.実行(context).成立)

    def test_同じ表示名でも別所有者のDataは不採用(self):
        other = DEMO['用意']()
        module = 長文脈選択Module(other)
        self.assertFalse(module.実行(self.context()).成立)

    def test_実行セッションが違えば読めない(self):
        module = 長文脈選択Module(self.a)
        self.assertFalse(module.実行(self.context(session='other')).成立)

    def test_未知設定を無視しない(self):
        module = 長文脈選択Module(self.a)
        self.assertEqual(module.判定(self.context(settings={'原文を破棄': True})), 0)
        self.assertFalse(module.実行(self.context(settings={'原文を破棄': True})).成立)

    def test_過小予算なら全本文を返さない(self):
        data = 長文脈要求Data(self.a, 文脈選択要求(('原資料',), 最大バイト数=10))
        result = 長文脈選択Module(self.a).実行(self.context(data=data))
        self.assertFalse(result.成立)
        self.assertEqual(result.本文, '')
        self.assertGreater(result.データ['必須バイト数'], 10)

    def test_普通の会話を読取命令にしない(self):
        module = 長文脈選択Module(self.a)
        c = 能力文脈('全記録を検索して', '長文脈デモ')
        self.assertEqual(module.判定(c), 0)
        self.assertFalse(module.実行(c).成立)

    def test_停止時には選択の能力も実行しない(self):
        request = 長文脈要求Data(self.a, 文脈選択要求(('原資料',)))
        plan = 合成計画((合成工程('選択', ('長文脈選択',), 'i', (素材参照('入力', 'r'),)),), ('選択',))
        result = 能力合成器((長文脈選択Module(self.a).登録(),)).実行(
            plan, {'r': request, 'i': 能力結果(True, '読取')},
            文脈=能力文脈('', '長文脈デモ'), 停止要求=lambda: True)
        self.assertEqual(result.状態, '中止')
        self.assertEqual(result.実行数, 0)

    def test_選択窓の役割と依存を後段Dataへ残す(self):
        self.a.更新(self.a.起点(), (文脈登録('条件', 能力結果(True, '試験用途に限定。'), '条件'),))
        result = 長文脈選択Module(self.a).実行(self.context())
        self.assertTrue(result.成立)
        self.assertIn('試験用途に限定。', result.本文)
        self.assertEqual([s['種別'] for s in result.データ['原文対応']], ['資料', '条件'])
        self.assertFalse(result.データ['全現行収録'])

    def test_独立CLIの初回復元改訂(self):
        for args in ([], ['--値', '9'], ['--値', '731']):
            with self.subTest(args=args):
                r = subprocess.run([sys.executable, str(ROOT/'tools/長文脈デモ.py'), *args],
                                   capture_output=True, encoding='utf-8', timeout=15)
                self.assertEqual(r.returncode, 0, r.stderr)
                result = json.loads(r.stdout)
                self.assertTrue(result['対照成立'] and result['合成監査'])
                self.assertFalse(result['旧選択の利用'])
                self.assertEqual(result['選択数'], 1)


if __name__ == '__main__':
    unittest.main()

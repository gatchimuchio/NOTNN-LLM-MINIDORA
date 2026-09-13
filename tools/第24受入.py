"""第24バッチの部分受入を分割実行し、件数・失敗・ソース指紋をJSONに記録する。"""
from __future__ import annotations

import argparse
from hashlib import sha256
import json
from pathlib import Path
import platform
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT/'src'), str(ROOT/'tools'), str(ROOT/'tests')]
from minidora.標準入出力 import 標準入出力をUTF8にする

組 = ('既存回帰', 'ファイル公開', '標準入出力', '符号化行列', '意味と計測')


def 全試験(suite):
    for item in suite:
        if isinstance(item, unittest.TestSuite):
            yield from 全試験(item)
        else:
            yield item


def ソース指紋():
    paths = [p for folder in ('src', 'tests', 'tools') for p in (ROOT/folder).rglob('*.py')]
    files = {p.relative_to(ROOT).as_posix(): sha256(p.read_bytes()).hexdigest() for p in sorted(paths)}
    raw = json.dumps(files, ensure_ascii=False, sort_keys=True, separators=(',', ':')).encode('utf-8')
    return sha256(raw).hexdigest()


def main():
    標準入出力をUTF8にする()
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--組', choices=組, required=True)
    parser.add_argument('--結果', type=Path, required=True)
    args = parser.parse_args()
    loader = unittest.defaultTestLoader
    if args.組 == '既存回帰':
        suite = unittest.TestSuite(t for t in 全試験(loader.discover(str(ROOT/'tests')))
                                  if not t.id().startswith('test_第24'))
    else:
        target = {'ファイル公開': 'test_第24入出力.ファイル公開試験',
                  '標準入出力': 'test_第24入出力.標準入出力契約試験',
                  '符号化行列': 'test_第24入出力.符号化行列試験',
                  '意味と計測': 'test_第24意味と計測'}[args.組]
        suite = loader.loadTestsFromName(target)
    ids = [t.id() for t in 全試験(suite)]
    before = ソース指紋()
    result = unittest.TextTestRunner(verbosity=2).run(suite)
    same = before == ソース指紋()
    report = {
        '版': 'MINIDORA-第24部分受入-v1', '対象': args.組,
        '環境': {'Python': platform.python_version(), 'OS': platform.system()},
        '件数': result.testsRun, '失敗': len(result.failures), 'エラー': len(result.errors),
        'スキップ': len(result.skipped), '予期しない成功': len(result.unexpectedSuccesses),
        '合格': result.wasSuccessful() and same and result.testsRun == len(ids),
        '試験ID': ids, 'ソースSHA256': before, '試験中ソース不変': same,
        '詳細': [{'試験': t.id(), '内容': text} for t, text in (*result.failures, *result.errors)],
        '範囲': '部分ソース。Windows実機・標準全能力・LIVE Web・全製品回帰は未実施'}
    args.結果.parent.mkdir(parents=True, exist_ok=True)
    args.結果.write_text(json.dumps(report, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    print(json.dumps({k: report[k] for k in ('対象', '件数', '合格', 'ソースSHA256')}, ensure_ascii=False))
    return 0 if report['合格'] else 1


if __name__ == '__main__':
    raise SystemExit(main())

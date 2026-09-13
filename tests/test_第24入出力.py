"""非UTF-8初期設定、別プロセス、ファイル公開失敗を実測する。Windows実機ではない。"""
from __future__ import annotations

from contextlib import ExitStack
import io
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

from minidora.原子的保存 import 原子的テキスト出力, 同じファイル
from minidora.標準入出力 import 標準入出力をUTF8にする
from minidora.監査改善会話 import 監査改善会話セッション

ROOT = Path(__file__).resolve().parents[1]
CLI = ROOT / 'tools/監査改善チャット.py'
REGISTER = '命題資料「例」を登録：P。PならばQ。'
QUERY = '資料「例」から「Q」を判定して'


def wire(*commands):
    return ''.join(json.dumps({'入力': s}, ensure_ascii=False) + '\n' for s in commands).encode('utf-8')


def child(data=b'', *args, encoding='ascii', entry=CLI):
    env = {**os.environ, 'PYTHONIOENCODING': encoding, 'PYTHONUTF8': '0',
           'PYTHONHASHSEED': '0', 'PYTHONDONTWRITEBYTECODE': '1'}
    # bytesで受け取り、親の既定符号化・置換に頼らず契約を検査する。
    proc = subprocess.run([sys.executable, str(entry), *map(str, args)], input=data,
                          capture_output=True, cwd=ROOT, env=env, timeout=30)
    stdout, stderr = proc.stdout.decode('utf-8', 'strict'), proc.stderr.decode('utf-8', 'strict')
    return proc.returncode, stdout, stderr


class 符号化行列試験(unittest.TestCase):
    pass


def case(encoding, operation):
    def test(self):
        if operation == 'help':
            code, out, err = child(b'', '--help', encoding=encoding)
            self.assertEqual(code, 0, err); self.assertIn('--発話', out)
        elif operation == '引数エラー':
            code, out, err = child(b'', '--存在しない引数', encoding=encoding)
            self.assertEqual(code, 2, err); self.assertIn('--存在しない引数', err)
        elif operation == '日本語JSONL':
            code, out, err = child(wire(REGISTER, QUERY), encoding=encoding)
            self.assertEqual(code, 0, err)
            rows = [json.loads(s) for s in out.splitlines()]
            self.assertEqual([r['状態'] for r in rows], ['合格', '合格'])
            self.assertEqual(rows[-1]['結果']['データ']['報告']['状態'], '支持')
        elif operation == '日本語直接入力':
            code, out, err = child(b'not JSON', '--発話', REGISTER, '--発話', QUERY, encoding=encoding)
            self.assertEqual(code, 0, err)
            self.assertEqual(json.loads(out.splitlines()[-1])['結果']['データ']['報告']['状態'], '支持')
        elif operation == '不正JSON':
            code, out, err = child(b'{broken}\n', encoding=encoding)
            self.assertEqual(code, 2, err); self.assertEqual(json.loads(out)['理由'], '通信入力不正')
        elif operation == '不正バイト':
            code, out, err = child(b'{"\xff":"x"}\n', encoding=encoding)
            self.assertEqual(code, 2, err); self.assertNotIn('\ufffd', out + err)
        else:
            code, out, err = child(b'', '--契約', encoding=encoding)
            self.assertEqual(code, 0, err); self.assertEqual(json.loads(out)['符号化'], 'UTF-8/strict')
        self.assertNotIn('Traceback', err)
    return test


for enc in ('ascii', 'cp1252', 'cp932', 'ascii:replace'):
    for op in ('help', '引数エラー', '日本語JSONL', '日本語直接入力', '不正JSON', '不正バイト', '契約'):
        setattr(符号化行列試験, 'test_' + enc.replace(':', '_') + '_' + op, case(enc, op))


class 標準入出力契約試験(unittest.TestCase):
    def test_StringIOを交換又は閉鎖しない(self):
        streams = [io.StringIO() for _ in range(3)]
        with ExitStack() as stack:
            for name, stream in zip(('stdin', 'stdout', 'stderr'), streams):
                stack.enter_context(patch.object(sys, name, stream))
            標準入出力をUTF8にする()
            self.assertEqual([sys.stdin, sys.stdout, sys.stderr], streams)
        self.assertTrue(all(not s.closed for s in streams))

    def test_既存ラッパーとバッファの所有権を維持(self):
        raw = io.BytesIO(); stream = io.TextIOWrapper(raw, encoding='ascii', errors='replace')
        try:
            with patch.object(sys, 'stdin', io.StringIO()), patch.object(sys, 'stderr', io.StringIO()), patch.object(sys, 'stdout', stream):
                標準入出力をUTF8にする(); self.assertIs(sys.stdout, stream)
                stream.write('根拠を保持'); stream.flush()
                self.assertEqual(stream.errors, 'strict')
            self.assertEqual(raw.getvalue(), '根拠を保持'.encode('utf-8')); self.assertFalse(raw.closed)
        finally:
            stream.close()

    def test_import時は標準ストリームを変更しない(self):
        command = "import sys;before=(sys.stdin.encoding,sys.stdout.encoding,sys.stderr.encoding);from minidora import 標準入出力;assert before==(sys.stdin.encoding,sys.stdout.encoding,sys.stderr.encoding)"
        proc = subprocess.run([sys.executable, '-c', command], cwd=ROOT, capture_output=True,
            env={**os.environ, 'PYTHONPATH': str(ROOT/'src'), 'PYTHONIOENCODING': 'ascii'}, timeout=15)
        self.assertEqual(proc.returncode, 0, proc.stderr)

    def test_先頭BOMの標準入力とファイル入力は同じ(self):
        raw = b'\xef\xbb\xbf' + wire(REGISTER, QUERY)
        a = child(raw)
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory)/'入力.jsonl'; path.write_bytes(raw)
            b = child(b'', '--入力', path)
        self.assertEqual(a[0], 0, a[2]); self.assertEqual(b[0], 0, b[2])
        def meanings(text):
            return [{k: v for k, v in json.loads(s).items() if k != '追跡'} for s in text.splitlines()]
        self.assertEqual(meanings(a[1]), meanings(b[1]))

    def test_通信途中のBOMを勝手に除去しない(self):
        code, out, err = child(wire(REGISTER) + b'\xef\xbb\xbf' + wire(QUERY))
        self.assertEqual(code, 2, err); self.assertEqual(json.loads(out.splitlines()[-1])['理由'], '通信入力不正')

    def test_契約はファイル操作と併用できない(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory)/'作成しない'
            code, _, _ = child(b'', '--契約', '--保存', path)
            self.assertEqual(code, 2); self.assertFalse(path.exists())

    def test_直接発話と入力ファイルは併用できない(self):
        code, _, _ = child(b'', '--発話', REGISTER, '--入力', 'dummy')
        self.assertEqual(code, 2)

    def test_直接発話の過大文字数を事前に拒否(self):
        code, out, _ = child(b'', '--発話', 'a' * 8193)
        self.assertEqual(code, 2); self.assertEqual(out, '')

    def test_直接発話の過大件数を事前に拒否(self):
        code, out, _ = child(b'', *[v for _ in range(129) for v in ('--発話', 'a')])
        self.assertEqual(code, 2); self.assertEqual(out, '')

    def test_対応しない意味を自由回答で補完しない(self):
        code, out, err = child(b'', '--発話', 'なんでも良いから未知の知識で答えて')
        self.assertEqual(code, 0, err); self.assertEqual(json.loads(out)['状態'], '保留')

    def test_全デモの日本語ヘルプが非UTF8環境でも表示できる(self):
        for name in ('監査改善デモ.py', '独立入力評価.py', '基点差分再現.py'):
            with self.subTest(name=name):
                code, out, err = child(b'', '--help', entry=ROOT/'tools'/name)
                self.assertEqual(code, 0, err); self.assertIn('usage', out)


class ファイル公開試験(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.root = Path(self.temporary.name)

    def tearDown(self):
        self.temporary.cleanup()

    def test_正常終了後だけLF付きUTF8を公開(self):
        path = self.root/'日本語 空白'/ '応答.jsonl'
        with 原子的テキスト出力(path) as out:
            out.write('日本語\n'); self.assertFalse(path.exists())
        self.assertEqual(path.read_bytes(), '日本語\n'.encode('utf-8'))

    def test_書込み途中の失敗で旧版を保持(self):
        path = self.root/'result'; path.write_bytes(b'old')
        with self.assertRaises(RuntimeError):
            with 原子的テキスト出力(path, 上書き=True) as out:
                out.write('途中'); raise RuntimeError('失敗注入')
        self.assertEqual(path.read_bytes(), b'old'); self.assertEqual(list(self.root.glob('.minidora-*')), [])

    def test_公開時点の競合で既存ファイルを上書きしない(self):
        path = self.root/'result'
        with self.assertRaises(FileExistsError):
            with 原子的テキスト出力(path) as out:
                out.write('new'); path.write_bytes(b'other writer')
        self.assertEqual(path.read_bytes(), b'other writer'); self.assertEqual(list(self.root.glob('.minidora-*')), [])

    def test_fsync失敗で旧版と一時ファイルの整合を保つ(self):
        path = self.root/'result'; path.write_bytes(b'old')
        with patch('minidora.原子的保存.os.fsync', side_effect=OSError('fsync失敗')), self.assertRaises(OSError):
            with 原子的テキスト出力(path, 上書き=True) as out:
                out.write('new')
        self.assertEqual(path.read_bytes(), b'old'); self.assertEqual(list(self.root.glob('.minidora-*')), [])

    def test_replace失敗で旧版を保持(self):
        path = self.root/'result'; path.write_bytes(b'old')
        with patch('minidora.原子的保存.os.replace', side_effect=OSError('replace失敗')), self.assertRaises(OSError):
            with 原子的テキスト出力(path, 上書き=True) as out:
                out.write('new')
        self.assertEqual(path.read_bytes(), b'old'); self.assertEqual(list(self.root.glob('.minidora-*')), [])

    def test_ハードリンク別名の入力切詰めを拒否(self):
        source, dest = self.root/'input', self.root/'alias'
        raw = wire(REGISTER, QUERY); source.write_bytes(raw); os.link(source, dest)
        self.assertTrue(同じファイル(source, dest))
        code, _, _ = child(b'', '--入力', source, '--出力', dest, '--上書き')
        self.assertEqual(code, 2); self.assertEqual(source.read_bytes(), raw); self.assertEqual(dest.read_bytes(), raw)

    def test_出力と保存状態のハードリンク別名を拒否(self):
        out, state = self.root/'output', self.root/'state'
        out.write_bytes(b'old'); os.link(out, state)
        code, _, _ = child(wire(REGISTER), '--出力', out, '--保存', state, '--上書き')
        self.assertEqual(code, 2); self.assertEqual(out.read_bytes(), b'old')

    def test_不正通信があれば出力と保存の旧版を保持(self):
        out, state = self.root/'out', self.root/'state'
        out.write_bytes(b'old output'); state.write_bytes(b'old state')
        code, _, _ = child(wire(REGISTER) + b'{bad}\n' + wire(QUERY), '--出力', out, '--保存', state, '--上書き')
        self.assertEqual(code, 2); self.assertEqual(out.read_bytes(), b'old output'); self.assertEqual(state.read_bytes(), b'old state')
        self.assertEqual(list(self.root.glob('.minidora-*')), [])

    def test_不正バイト読取で出力旧版を保持(self):
        source, out = self.root/'input', self.root/'out'
        source.write_bytes(wire(REGISTER) + b'\xff'); out.write_bytes(b'old')
        code, _, _ = child(b'', '--入力', source, '--出力', out, '--上書き')
        self.assertEqual(code, 2); self.assertEqual(out.read_bytes(), b'old')

    def test_不正通信で新規ファイルも作らない(self):
        out, state = self.root/'out', self.root/'state'
        code, _, _ = child(b'{bad}\n', '--出力', out, '--保存', state)
        self.assertEqual(code, 2); self.assertFalse(out.exists()); self.assertFalse(state.exists())

    def test_意味上の保留は正常通信として保存復元できる(self):
        state = self.root/'state'
        code, out, err = child(wire('未対応の依頼'), '--保存', state)
        self.assertEqual(code, 0, err); self.assertEqual(json.loads(out)['状態'], '保留')
        restored = 監査改善会話セッション.復元(state.read_text(encoding='utf-8'))
        self.assertEqual(restored.状態()['発話数'], 1)

    def test_同じ保存先へ明示復元と更新ができる(self):
        state = self.root/'state'
        self.assertEqual(child(wire(REGISTER, QUERY), '--保存', state)[0], 0)
        code, out, err = child(wire('短く説明して'), '--復元', state, '--保存', state, '--上書き')
        self.assertEqual(code, 0, err); self.assertEqual(json.loads(out)['状態'], '合格')
        self.assertEqual(監査改善会話セッション.復元(state.read_text(encoding='utf-8')).状態()['発話数'], 3)

    def test_出力先ディレクトリは処理前に拒否(self):
        code, out, _ = child(wire(REGISTER), '--出力', self.root, '--上書き')
        self.assertEqual(code, 2); self.assertEqual(out, '')

    def test_保存サイズ上限を超えたら旧版を保持(self):
        from 監査改善チャット import 保存する
        path = self.root/'state'; path.write_bytes(b'old')
        with self.assertRaises(ValueError):
            保存する(path, 'あ' * 666667, True)
        self.assertEqual(path.read_bytes(), b'old')

    def test_シンボリックリンクを公開先にしない(self):
        source, link = self.root/'source', self.root/'link'; source.write_bytes(b'old')
        try:
            link.symlink_to(source)
        except OSError as exc:
            self.skipTest('実行環境でsymlink作成不可: ' + str(exc))
        code, _, _ = child(wire(REGISTER), '--出力', link, '--上書き')
        self.assertEqual(code, 2); self.assertEqual(source.read_bytes(), b'old'); self.assertTrue(link.is_symlink())


if __name__ == '__main__':
    unittest.main()

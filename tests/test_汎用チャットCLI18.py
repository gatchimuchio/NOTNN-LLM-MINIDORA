"""日本語CLIと製品標準入口の明示選択接続。ネットワークを使わない。"""
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT=Path(__file__).resolve().parents[1]
class 汎用CLI試験(unittest.TestCase):
    def run_cli(self,*args,input=None,standard=False):
        cmd=[sys.executable,'-m','minidora.製品版','--汎用'] if standard else [sys.executable,str(ROOT/'tools/汎用チャット.py')]
        env={**os.environ,'PYTHONPATH':str(ROOT/'src')}
        return subprocess.run([*cmd,*args],input=input,encoding='utf-8',capture_output=True,cwd=ROOT,env=env,timeout=20)
    def test_単発の既存計算(self):
        r=self.run_cli('「2+3」を計算して');self.assertEqual(r.returncode,0,r.stderr);self.assertEqual(r.stdout.strip(),'5')
    def test_標準製品入口から明示選択(self):
        r=self.run_cli('「2+3」を計算して',standard=True);self.assertEqual(r.returncode,0,r.stderr);self.assertEqual(r.stdout.strip(),'5')
    def test_資料比較と確認後の再開(self):
        with tempfile.TemporaryDirectory() as d:
            a,b=Path(d)/'a.txt',Path(d)/'b.txt'
            a.write_text('装置Aの電圧は5Vです。',encoding='utf-8');b.write_text('装置Bの電圧は3Vです。',encoding='utf-8-sig')
            r=self.run_cli('--資料',f'装置A={a}',input=f'「装置A」と「装置B」の電圧をVで比較して\n/資料 装置B={b}\n再開して\n/終了\n')
            self.assertEqual(r.returncode,0,r.stderr);self.assertIn('は2 V',r.stdout)
    def test_単位補充の連続入力(self):
        r=self.run_cli(input='「装置A」の電圧を調べて\n単位はVです\n取り消して\n「2+3」を計算して\n/終了\n')
        self.assertEqual(r.returncode,0,r.stderr);self.assertIn('単位を指定',r.stdout);self.assertIn('5',r.stdout)
    def test_JSON追跡(self):
        r=self.run_cli('--json','「2+3」を計算して');self.assertEqual(r.returncode,0,r.stderr)
        self.assertEqual(json.loads(r.stdout)['状態'],'合格')
    def test_既定文字コードへの非依存(self):
        with patch.dict(os.environ,{'PYTHONIOENCODING':'cp1252'}):
            r=self.run_cli(input='「2+3」を計算して\nそれから数字を抽出して\n/終了\n')
        self.assertEqual(r.stdout.splitlines(),['5','5']);self.assertEqual(r.returncode,0,r.stderr)
    def test_過大入力の後半を実行しない(self):
        r=self.run_cli(input='あ'*8193+'\n「2+3」を計算して\n')
        self.assertEqual(r.returncode,2);self.assertNotIn('5',r.stdout)
    def test_不正UTF8を追跡例外なしで停止(self):
        r=subprocess.run([sys.executable,str(ROOT/'tools/汎用チャット.py')],input=b'\xff\n',capture_output=True,cwd=ROOT,timeout=20)
        self.assertEqual(r.returncode,2);self.assertNotIn(b'Traceback',r.stderr)
    def test_初期化で資料も消す(self):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d)/'a.txt';p.write_text('装置Aの電圧は5Vです。',encoding='utf-8')
            r=self.run_cli('--資料',f'装置A={p}',input='/初期化\n「装置A」の電圧をVで調べて\n/終了\n')
            self.assertIn('資料が必要',r.stdout);self.assertNotIn('5 V',r.stdout)
    def test_不正な資料指定は終了(self):
        self.assertEqual(self.run_cli('--資料','file-missing','「2+3」を計算して').returncode,2)
    def test_予算の不正値を拒否(self):
        self.assertEqual(self.run_cli('--最大文字数','0','「2+3」を計算して').returncode,2)

if __name__=='__main__':unittest.main()

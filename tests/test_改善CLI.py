"""別プロセスCLIと限定した表層変換。Windows実機の試験ではない。"""
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from minidora.監査改善会話 import 監査改善会話セッション
from minidora.能力合成 import _符号化
from minidora.監査改善会話解釈 import 改善発話を解釈

ROOT=Path(__file__).resolve().parents[1]
CLI=ROOT/'tools/監査改善チャット.py'
REGISTER='仮説資料「天候」を登録：\n規則：RainならばWet\n規則：SprinklerならばWet\n候補：Rain、Sprinkler'
QUERY='資料「天候」で観測「Wet」を説明する仮説を検討して'


def encode(*commands):return ''.join(json.dumps({'入力':s},ensure_ascii=False)+'\n' for s in commands)


def run(text='',*args,seed=None):
    env={**os.environ,'PYTHONIOENCODING':'utf-8'}
    if seed is not None:env['PYTHONHASHSEED']=str(seed)
    return subprocess.run([sys.executable,str(CLI),*map(str,args)],input=text,encoding='utf-8',capture_output=True,timeout=30,env=env)


class CLI試験(unittest.TestCase):
    def test_標準入出力で多段会話を完遂する(self):
        p=run(encode(REGISTER,QUERY))
        self.assertEqual(p.returncode,0,p.stderr)
        rows=[json.loads(s) for s in p.stdout.splitlines()]
        self.assertEqual([r['状態'] for r in rows],['合格','合格'])
        self.assertEqual(len(rows[-1]['結果']['データ']['報告']['候補']),2)

    def test_ファイル保存後の別プロセス復元から再説明(self):
        with tempfile.TemporaryDirectory() as d:
            state=Path(d)/'state.json'
            a=run(encode(REGISTER,QUERY),'--保存',state,'--セッション','sample')
            self.assertEqual(a.returncode,0,a.stderr)
            b=run(encode('短く説明して'),'--復元',state,'--セッション','sample')
            self.assertEqual(b.returncode,0,b.stderr)
            self.assertEqual(json.loads(b.stdout)['状態'],'合格')

    def test_既存保存ファイルを無断上書きしない(self):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d)/'state';p.write_text('保持')
            r=run(encode(REGISTER),'--保存',p)
            self.assertEqual(r.returncode,2);self.assertEqual(p.read_text(),'保持')

    def test_明示上書きで状態を更新する(self):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d)/'state';p.write_text('旧値')
            r=run(encode(REGISTER),'--保存',p,'--上書き')
            self.assertEqual(r.returncode,0,r.stderr)
            restored=監査改善会話セッション.復元(p.read_text())
            self.assertIn('天候',restored.状態()['資料版'])

    def test_入力ファイルを出力で切り詰めない(self):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d)/'input.jsonl';text=encode(REGISTER);p.write_text(text)
            r=run('','--入力',p,'--出力',p,'--上書き')
            self.assertEqual(r.returncode,2);self.assertEqual(p.read_text(),text)

    def test_不正な通信入力は会話へ渡さない(self):
        p=run('{"入力":"A","入力":"B"}\n'+encode(REGISTER,QUERY))
        self.assertEqual(p.returncode,2)
        rows=[json.loads(x) for x in p.stdout.splitlines()]
        self.assertEqual(rows[0]['理由'],'通信入力不正')
        self.assertEqual(rows[-1]['状態'],'合格')

    def test_過大な一行を有界で拒否する(self):
        p=run('x'*65537)
        self.assertEqual(p.returncode,2)
        self.assertEqual(json.loads(p.stdout)['理由'],'通信入力不正')

    def test_別セッションの復元を拒否する(self):
        with tempfile.TemporaryDirectory() as d:
            path=Path(d)/'state'
            self.assertEqual(run(encode(REGISTER),'--保存',path,'--セッション','a').returncode,0)
            self.assertEqual(run('','--復元',path,'--セッション','b').returncode,2)

    def test_破損状態を読み飛ばして新規開始しない(self):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d)/'state';p.write_text('{"状態":"破損"}')
            r=run(encode(REGISTER),'--復元',p)
            self.assertEqual(r.returncode,2);self.assertEqual(r.stdout,'')

    def test_hashseed間で全回答意味が同一(self):
        values=[]
        for seed in (0,1,913):
            r=run(encode(REGISTER,QUERY,'短く説明して'),seed=seed)
            self.assertEqual(r.returncode,0,r.stderr)
            # 追跡内の所有UUID・実行印は別所有者ごとに変わる。出力結果全体は除外しない。
            values.append([{k:v for k,v in json.loads(line).items() if k!='追跡'} for line in r.stdout.splitlines()])
        self.assertEqual(_符号化(values[0]),_符号化(values[1]))
        self.assertEqual(_符号化(values[0]),_符号化(values[2]))


class 表層変換試験(unittest.TestCase):
    def test_一貫した名前変更で説明集合が同型になる(self):
        for names in (('Rain','Sprinkler','Wet'),('Fuse','Relay','Lamp'),('Alpha','Beta','Gamma')):
            with self.subTest(names=names):
                a,b,c=names;s=監査改善会話セッション()
                r=s.応答(f'仮説資料「T」を登録：\n規則：{a}ならば{c}\n規則：{b}ならば{c}\n候補：{a}、{b}')
                self.assertTrue(r.成立)
                out=s.応答(f'資料「T」で観測「{c}」を説明する仮説を検討して')
                self.assertTrue(out.成立,out.本文)
                self.assertEqual({tuple(x['仮説']) for x in out.結果.データ['報告']['候補']},{(a,),(b,)})

    def test_規則順序と無関係な記載は結論集合を変えない(self):
        bodies=('規則：RainならばWet\n規則：SprinklerならばWet',
                '規則：SprinklerならばWet\n規則：RainならばWet',
                '事実：Else\n規則：RainならばWet\n規則：SprinklerならばWet')
        for body in bodies:
            with self.subTest(body=body):
                s=監査改善会話セッション();s.応答('仮説資料「天候」を登録：\n'+body+'\n候補：Rain、Sprinkler')
                r=s.応答(QUERY);self.assertTrue(r.成立,r.本文)
                self.assertEqual({tuple(c['仮説']) for c in r.結果.データ['報告']['候補']},{('Rain',),('Sprinkler',)})

    def test_丁寧形と引用種別で依頼の意味を保つ(self):
        base=改善発話を解釈(QUERY)
        for q in (QUERY+'。',QUERY.replace('検討して','検討してください'),QUERY.replace('「','『').replace('」','』')):
            with self.subTest(q=q):
                got=改善発話を解釈(q)
                self.assertEqual({k:v for k,v in base.items() if k!='原文'},
                                 {k:v for k,v in got.items() if k!='原文'})

    def test_命題否定の最小差で判定が変わる(self):
        for body,expected in (('P。','支持'),('否定(P)。','反証'),('Q。','未確定')):
            with self.subTest(body=body):
                s=監査改善会話セッション();s.応答('命題資料「A」を登録：'+body)
                r=s.応答('資料「A」から「P」を判定して')
                self.assertTrue(r.成立,r.本文);self.assertEqual(r.結果.データ['報告']['状態'],expected)

if __name__=='__main__':unittest.main()

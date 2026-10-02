from unittest import TestCase
from dataclasses import replace
from minidora.HDS実行主体 import HDS実行状態,HDS関数作用,HDS作用結果,HDS作用状態
from minidora.統合駆動_v2.計画 import HDS作用仕様,HDS探索契約

class 観測入力契約試験(TestCase):
    def test_観測入力を計画の入力へ含める(self):
        s=HDS作用仕様('観測',観測入力=('成果:参照',));self.assertIn('成果:参照',s.入力ノード集合)
    def test_欠落観測入力で機会条件や署名を実行しない(self):
        calls=[];s=HDS作用仕様('観測',観測入力=('成果:参照',))
        a=HDS関数作用('観測',lambda st:HDS作用結果(HDS作用状態.成立),計画仕様=s,
            機会判定=lambda st:(calls.append('condition')or True),入力署名=lambda st:(calls.append('signer')or 's'))
        st=HDS実行状態(目的=('確認',));o=a.機会(st);self.assertEqual(calls,[]);self.assertTrue(o)
        a.意味入力を署名(st);self.assertEqual(calls,[])
    def test_存在する観測入力を呼び出せる(self):
        calls=[];s=HDS作用仕様('観測',観測入力=('成果:参照',))
        a=HDS関数作用('観測',lambda st:HDS作用結果(HDS作用状態.成立),計画仕様=s,
            機会判定=lambda st:(calls.append(1)or True))
        o=a.機会(HDS実行状態(目的=('確認',),成果=(('参照',1),)));self.assertEqual(calls,[1]);self.assertEqual(o.読取成果,());self.assertEqual(o.読取ノード,())
    def test_観測入力の値を意味署名へ反映(self):
        s=HDS作用仕様('観測',観測入力=('成果:参照',));a=HDS関数作用('観測',lambda st:None,計画仕様=s)
        st=HDS実行状態(目的=('確認',),成果=(('参照',1),));self.assertNotEqual(a.意味入力を署名(st),a.意味入力を署名(replace(st,成果=(('参照',2),))))
    def test_観測入力を因果読取へ混入しない(self):
        s=HDS作用仕様('観測',観測入力=('成果:参照',));self.assertEqual(s.読取ノード,());self.assertEqual(s.読取成果,())
    def test_外部観測を純粋再現と偽らない(self):
        e=HDS探索契約('観測枠','不明',('成果:参照',),('状態:終了',),再観測=True)
        s=HDS作用仕様('観測',探索=e,観測専用=True);self.assertFalse(s.純粋)
    def test_一般副作用の探索宣言を拒否(self):
        e=HDS探索契約('観測枠','不明',('成果:参照',),('状態:終了',))
        with self.assertRaises(ValueError):HDS作用仕様('実行',探索=e)
    def test_不正な観測入力を拒否(self):
        with self.assertRaises(ValueError):HDS作用仕様('観測',観測入力=('未知:参照',))
    def test_再観測の真偽型を固定(self):
        with self.assertRaises(TypeError):HDS探索契約('観測枠','不明',('成果:参照',),('状態:終了',),再観測=1)

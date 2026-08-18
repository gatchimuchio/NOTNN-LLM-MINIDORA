import sys, unittest
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/"src"))

from minidora import 意味要求, 外部参照R, 命令形P, Layer0, ミニドラ, 表層Adapter
from minidora.compiler import 教師写像監査

def build(R=None,P=None):
    P=P or 命令形P.JSON(ROOT/"p"/"命令形P.json")
    R=R or 外部参照R.JSONL(ROOT/"data"/"参照R.jsonl")
    S=表層Adapter.JSON(ROOT/"data"/"概念語彙.json")
    return ミニドラ(Layer0(),P,R,S)

class MVP(unittest.TestCase):
    def test_教師からLayer0写像を追跡できる(self):
        r=教師写像監査(ROOT/"teacher"/"K3教師データ.jsonl",ROOT/"mapping"/"Layer0写像.json",ROOT/"p"/"命令形P.json")
        self.assertEqual(r["状態"],"合格"); self.assertGreaterEqual(r["写像に利用した教師件数"],10)
    def test_K3固有語がPに漏れていない(self):
        txt=(ROOT/"p"/"命令形P.json").read_text(encoding="utf-8")
        for x in ("KDA","MLA","AttnRes","MoE","896","Top-16","93 layers"): self.assertNotIn(x,txt)
    def test_三言語が同一内部意味要求へ落ちる(self):
        S=表層Adapter.JSON(ROOT/"data"/"概念語彙.json")
        reqs=[S.解析("日本の首都は？"),S.解析("What is the capital of Japan?"),S.解析("日本的首都是哪里？")]
        cores=[(r.要求種,r.対象,r.関係列) for r in reqs]
        self.assertEqual(cores[0],cores[1]); self.assertEqual(cores[1],cores[2]); self.assertEqual(cores[0],("関係質問","日本",("首都",)))
    def test_多言語表層でも同じ内部計算(self):
        outs=[build().問う("日本の首都は？"),build().問う("What is the capital of Japan?"),build().問う("日本的首都是哪里？")]
        self.assertEqual([o.値 for o in outs],["東京","東京","東京"]); self.assertEqual([o.表出 for o in outs],["東京","Tokyo","东京"])
    def test_多段関係はPの反復で解く(self):
        out=build().問う("太郎の親の親は？"); self.assertEqual(out.値,"花子"); self.assertEqual(out.状態,"合格"); self.assertEqual(sum(1 for h in out.履歴 if h["作用"]=="参照"),2)
    def test_算術はRなしで同じLayer0を使う(self):
        P=命令形P.JSON(ROOT/"p"/"命令形P.json"); S=表層Adapter.JSON(ROOT/"data"/"概念語彙.json"); out=ミニドラ(Layer0(),P,None,S).問う("(2+3)*4")
        self.assertEqual(out.値,20); self.assertEqual(out.状態,"合格"); self.assertEqual(out.参照,())
    def test_Data差替えだけで答えが変わる(self):
        R1=外部参照R([{"id":"x","主語":"日本","関係":"首都","値":"東京","出典":"a"}]); R2=外部参照R([{"id":"x","主語":"日本","関係":"首都","値":"京都","出典":"b"}])
        self.assertEqual(build(R=R1).問う("日本の首都は？").値,"東京"); self.assertEqual(build(R=R2).問う("日本の首都は？").値,"京都")
    def test_P差替えで能力が変わりLayer0は変わらない(self):
        out=build(P=命令形P({"規則":[]})).問う("日本の首都は？"); self.assertEqual(out.状態,"保留"); self.assertIn("適用可能な命令Pなし",out.未解)
    def test_未知は保留(self):
        out=build().意味で問う(意味要求("関係質問","月",("所有者",),None,"ja")); self.assertEqual(out.状態,"保留"); self.assertTrue(out.未解)
    def test_矛盾は保留(self):
        R=外部参照R([{"id":"1","主語":"日本","関係":"首都","値":"東京","出典":"a"},{"id":"2","主語":"日本","関係":"首都","値":"京都","出典":"b"}]); out=build(R=R).問う("日本の首都は？")
        self.assertEqual(out.状態,"保留"); self.assertTrue(out.矛盾)
    def test_外部文書丸写しではなく値を内部処理(self):
        out=build().問う("日本の首都は？"); self.assertEqual(out.値,"東京"); self.assertTrue(any(h["作用"]=="単値化" for h in out.履歴)); self.assertTrue(any(h["作用"]=="参照" for h in out.履歴))

if __name__=="__main__": unittest.main()

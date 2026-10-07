from importlib.util import module_from_spec, spec_from_file_location
from pathlib import Path
from unittest import TestCase

根 = Path(__file__).resolve().parents[1]
仕様 = spec_from_file_location("学習効果比較", 根 / "tools" / "GPQA学習効果比較.py")
本体 = module_from_spec(仕様)
仕様.loader.exec_module(本体)


def 共通条件(版):
    return {
        "資料集合CSV_SHA256":"dataset","全問題数":198,"選択肢シャッフル種":0,
        "参照方式":"LIVE_ONLY","固定参照資料許可":False,"採点結果の学習利用":False,
        "中核入口":"HDS駆動コア.選択実行","問題束一問一形成":True,
        "OpenAlex有効":False,"EuropePMC有効":True,"Crossref有効":True,
        "Wikipedia言語群":["en"],"選択番号群":list(range(198)),"リポジトリ版":版,
    }


def 並列(score=43, 版="same"):
    rows=[{"番号":i,"正答":i<score} for i in range(198)]
    return {"リポジトリ版":版,"評価条件":共通条件(版),"性能継承成立":score>=43,"個票":rows}


def 直列(correct, *, 版="same", 適応=True):
    rows=[]
    for i in range(198):
        rows.append({
            "番号":i,"正答":i in correct,
            "処理前継続状態署名":"a"+str(i),
            "処理後継続状態署名":"b"+str(i),
            "観測経路適応数":1 if 適応 and i>0 else 0,
            "計装":{"形成再利用数":0},
        })
    return {
        "評価条件":共通条件(版),
        "測定状態":"完了","実測":{"全数完走":True,"経過秒":1000},
        "個票":rows,
    }


class GPQA学習効果比較試験(TestCase):
    def test_十問純増は有意な正の学習効果(self):
        p=並列(43)
        s=直列(set(range(43)) | set(range(50,60)))
        r=本体.比較(p,s)
        self.assertTrue(r["学習実証成立"])
        self.assertEqual(r["差分"],10)
        self.assertLess(r["片側正確有意確率"],0.05)

    def test_三問純増は有意差不足(self):
        p=並列(43)
        s=直列(set(range(43)) | {50,51,52})
        r=本体.比較(p,s)
        self.assertFalse(r["学習実証成立"])
        self.assertGreaterEqual(r["片側正確有意確率"],0.05)

    def test_点数増でも後続適応が無ければ学習実証にしない(self):
        p=並列(43)
        s=直列(set(range(43)) | set(range(50,60)),適応=False)
        self.assertFalse(本体.比較(p,s)["学習実証成立"])

    def test_provider条件が異なれば比較しない(self):
        p=並列(43)
        s=直列(set(range(53)))
        s["評価条件"]["Crossref有効"]=False
        with self.assertRaises(ValueError):
            本体.比較(p,s)

    def test_異なる版を比較しない(self):
        with self.assertRaises(ValueError):
            本体.比較(並列(43,"a"),直列(set(range(53)),版="b"))

    def test_並列43未達なら直列が高くても成立しない(self):
        p=並列(42)
        s=直列(set(range(60)))
        self.assertFalse(本体.比較(p,s)["学習実証成立"])


if __name__=="__main__":
    import unittest
    unittest.main()

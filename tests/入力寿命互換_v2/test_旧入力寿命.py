"""実行内でCore入力を形成する既存契約。新引数なしで前版と同一入力を比較する。"""
import unittest
from minidora.HDS実行主体 import HDS実行主体,HDS実行状態,HDS関数作用,HDS作用結果,HDS作用状態,HDS終端
from minidora.HDSコア入力 import HDSコア入力束,HDSコア表現制約
from minidora.統合駆動_v2.政策 import HDS運用政策
from minidora.統合駆動_v2.目的保持 import 目的契約署名
from minidora.コア.値 import 署名


def 入力():
    return HDSコア入力束('入力の形成を確認する','試験世界',(),(),(),(),(),(),(),(),(),HDSコア表現制約('日本語'))


class 旧入力寿命試験(unittest.TestCase):
    def test_指示未接続の旧入力形成を目的変更と混同しない(self):
        core=入力()
        a=HDS関数作用('旧入力形成',lambda s:HDS作用結果(HDS作用状態.成立,
            成果=(('HDSコア入力',core),),主体状態差分=(('HDSコア入力署名',core.意味署名),),追加状態=frozenset({'入力形成済み'})),出力状態=('入力形成済み',))
        s=HDS実行状態(目的=('入力を形成する',),要求状態=frozenset({'入力形成済み'}))
        r=HDS実行主体((a,),政策=HDS運用政策(自動形成=False)).実行(s)
        self.assertEqual(r.終端,HDS終端.採用,r.理由)
        self.assertEqual(r.状態.成果辞書()['HDSコア入力'],core)
    def test_指示未接続の目的署名を保存する(self):
        s=HDS実行状態(目的=('元目的',),要求状態=frozenset({'到達'}))
        self.assertEqual(目的契約署名(s),署名((s.目的,s.要求状態,s.要求認識,())))
    def test_原目的正本の変更禁止は維持する(self):
        s=HDS実行状態(目的=('元目的',),要求状態=frozenset({'到達'}),主体状態=(('HDS目的正本',('元',)),))
        a=HDS関数作用('改変',lambda s:HDS作用結果(HDS作用状態.成立,主体状態差分=(('HDS目的正本',('別',)),)),出力状態=('到達',))
        r=HDS実行主体((a,),政策=HDS運用政策(自動形成=False)).実行(s)
        self.assertEqual(r.終端,HDS終端.失敗)
        self.assertEqual(r.状態.主体辞書()['HDS目的正本'],('元',))

if __name__=='__main__':unittest.main()

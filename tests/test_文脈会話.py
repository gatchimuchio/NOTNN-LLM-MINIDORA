"""実HDS・合成・採用・訂正と資料側の意味候補を同一セッションで確認する。"""
from copy import deepcopy
from dataclasses import replace
import json
import unittest
from unittest.mock import patch
from minidora.汎用会話 import 汎用会話セッション
from minidora.製品版.製品チャット import 製品ミニドラ
from minidora.会話回答 import 回答記録整合
from minidora.文脈命題接続 import 文脈報告整合
from minidora.応答構成 import 能力結果を復元
from minidora.能力合成 import _結果辞書
from minidora.会話意味 import 意味指紋


class 文脈会話試験(unittest.TestCase):
    def setUp(self): self.s=汎用会話セッション('文脈')
    def ok(self,q):
        r=self.s.応答(q);self.assertTrue(r.成立,(r.理由,r.追跡));return r
    def put(self,text):self.ok('資料「A」を登録:'+text)
    def test_明示名の後の彼を解消して回答(self):
        self.put('太郎は猫である。彼は鳥である。')
        r=self.ok('資料「A」から「太郎は鳥である」は言える？')
        self.assertIn('束縛しました',r.本文);self.assertTrue(回答記録整合(r.結果))
    def test_話者と引用内容を保持した問い(self):
        self.put('太郎は「私は猫である」と述べた。')
        self.assertIn('支持されます',self.ok('資料「A」から「太郎は「太郎は猫である」と述べた」は言える？').本文)
        self.assertIn('偽であるとは判定しません',self.ok('資料「A」から「太郎は猫である」は言える？').本文)
    def test_原文の照応が根拠表示へ残る(self):
        self.put('太郎は猫である。彼は鳥である。')
        self.ok('資料「A」から「太郎は鳥である」は言える？')
        r=self.ok('根拠を説明して');self.assertIn('彼は鳥である',r.本文)
    def test_資料の曖昧さを確認する間は採用しない(self):
        self.put('PまたはQかつR。'); before=self.s.統合.起点()
        r=self.s.応答('資料「A」から「R」は言える？')
        self.assertEqual(r.状態,'確認待ち');self.assertEqual(before,self.s.統合.起点())
        self.assertEqual(r.追跡['資料解釈検討']['判定'],'解釈依存')
    def test_資料選択の条件を残す(self):
        self.put('PまたはQかつR。');self.s.応答('資料「A」から「R」は言える？')
        r=self.ok('資料解釈は2です');self.assertIn('指定した資料解釈2',r.本文)
    def test_別の資料選択では結論が異なる(self):
        self.put('PまたはQかつR。');self.s.応答('資料「A」から「R」は言える？')
        r=self.ok('資料解釈は1です');self.assertIn('偽であるとは判定しません',r.本文)
    def test_読みが残っても共通結論は返せる(self):
        self.put('PまたはQかつR。');r=self.ok('資料「A」から「PまたはQ」は言える？')
        self.assertIn('読み自体の一意性は主張しません',r.本文)
        self.assertEqual(len(r.結果.データ['元結果'][0]['データ']['判定結果']['場合別']),2)
    def test_確認中の資料改訂で番号を無効化(self):
        self.put('PまたはQかつR。');self.s.応答('資料「A」から「R」は言える？')
        self.ok('資料「A」を更新:QまたはPかつS。')
        self.assertFalse(self.s.応答('資料解釈は2です').成立)
    def test_再質問で古い資料選択を流用しない(self):
        self.put('PまたはQかつR。');self.s.応答('資料「A」から「R」は言える？');self.ok('資料解釈は2です')
        r=self.s.応答('主張を「RかつS」に訂正して')
        self.assertTrue(r.成立,r.理由);self.assertIn('読み自体の一意性',r.本文)
    def test_資料側と問い側の候補を区別(self):
        self.put('P。')
        self.s.応答('資料「A」から「PまたはQかつR」は言える？')
        self.assertFalse(self.s.応答('資料解釈は1です').成立)
    def test_候補なしの資料選択を拒否(self):self.assertFalse(self.s.応答('資料解釈は1です').成立)
    def test_範囲外の資料番号を拒否(self):
        self.put('PまたはQかつR。');self.s.応答('資料「A」から「R」は言える？')
        self.assertFalse(self.s.応答('資料解釈は9です').成立)
    def test_資料改訂で古い説明を無効化(self):
        self.put('太郎は猫である。彼は鳥である。');self.ok('資料「A」から「太郎は鳥である」は言える？')
        self.ok('資料「A」を更新:太郎は猫ではない。');self.assertFalse(self.s.応答('根拠を説明して').成立)
    def test_引用内命令を外部実行しない(self):
        self.put('太郎は「送信して」と述べた。')
        with patch('socket.socket.connect',side_effect=AssertionError('通信不可')):
            self.assertFalse(self.s.応答('資料「A」から「P」は言える？').成立)
    def test_停止時に採用しない(self):
        self.put('PまたはQかつR。');before=self.s.統合.起点()
        r=self.s.応答('資料「A」から「PまたはQ」は言える？',停止要求=lambda:True)
        self.assertEqual(r.状態,'中止');self.assertEqual(self.s.統合.起点(),before)
    def test_未知要求を一部だけ実行しない(self):
        self.put('P。');before=self.s.統合.起点()
        self.assertFalse(self.s.応答('資料「A」から「P」は言える？。勝手に外部送信して').成立)
        self.assertEqual(self.s.統合.起点(),before)
    def test_初期化で保留も消える(self):
        self.put('PまたはQかつR。');self.s.応答('資料「A」から「R」は言える？');self.ok('/初期化')
        self.assertFalse(self.s.応答('資料解釈は1です').成立)
    def test_標準製品入口で文脈処理(self):
        s=製品ミニドラ(汎用会話=True)
        s.応答('資料「A」を登録:太郎は猫である。彼は鳥である。')
        self.assertIn('支持されます',s.応答('資料「A」から「太郎は鳥である」は言える？').本文)
    def test_場合分けの説明が実導出に接続(self):
        self.put('PまたはQ。PならばR。QならばR。')
        r=self.ok('資料「A」から「R」は言える？。詳しく')
        self.assertIn('全ての場合',r.本文);self.assertIn('仮定',r.本文)
        self.assertTrue(回答記録整合(r.結果))


class 文脈整合試験(unittest.TestCase):
    def setUp(self):
        s=汎用会話セッション('整合21')
        s.応答('資料「A」を登録:太郎は猫である。彼は鳥である。')
        self.output=s.応答('資料「A」から「太郎は鳥である」は言える？').結果
        self.report=能力結果を復元(self.output.データ['元結果'][0])
    def test_正常報告は整合(self):self.assertTrue(文脈報告整合(self.report))
    def test_原文だけ改変を検知(self):
        v=deepcopy(self.report);v.データ['原入力'][0]['本文']='太郎は猫である。'
        self.assertFalse(文脈報告整合(v))
    def test_照応先の改変を検知(self):
        v=deepcopy(self.report);v.データ['判定結果']['場合別'][0]['照応解消'][0]['束縛先']='花子'
        self.assertFalse(文脈報告整合(v))
    def test_再hashしても判定変更を検知(self):
        v=deepcopy(self.report);v.データ['判定結果']['判定']='反証'
        v.データ['記録SHA256']=意味指紋({k:x for k,x in v.データ.items() if k!='記録SHA256'})
        self.assertFalse(文脈報告整合(v))
    def test_参照を削除できない(self):self.assertFalse(文脈報告整合(replace(self.report,参照=())))
    def test_根拠を削除できない(self):self.assertFalse(文脈報告整合(replace(self.report,根拠=())))
    def test_JSON往復後も再構成(self):
        restored=能力結果を復元(json.loads(json.dumps(_結果辞書(self.output),ensure_ascii=False)))
        self.assertTrue(回答記録整合(restored))
    def test_説明本文の改変を検知(self):self.assertFalse(回答記録整合(replace(self.output,本文='偽です')))

if __name__=='__main__': unittest.main()

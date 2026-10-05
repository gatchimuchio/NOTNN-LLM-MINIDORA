from unittest import TestCase
from unittest.mock import patch
from dataclasses import replace
from urllib.error import HTTPError
from email.message import Message
from minidora.参照 import (参照記録,参照取得診断,参照全保持を統合,参照保持容量超過,
    参照経験記憶を統合,参照記録群を統合,複合参照供給器,参照検索を診断)


def 記録(本文='長い旧観測の本文',識別子='資料',条件=()):
    return 参照記録(識別子,'対象',本文,'出典','供給器',条件=条件)

class 提供器:
    名称='正常'
    def __init__(self):self.回数=0
    def 検索(self,問合せ,上限):self.回数+=1;return (記録(問合せ),)

class 失敗器:
    名称='制限中'
    def __init__(self,解除=None):self.回数=0;self.解除=解除
    def 検索(self,問合せ,上限):
        self.回数+=1
        ヘッダ=Message()
        if self.解除 is not None:ヘッダ['Retry-After']=str(self.解除)
        raise HTTPError('https://example.invalid',429,'Too Many Requests',ヘッダ,None)

class 参照保持試験(TestCase):
    def test_短い訂正を本文長で失わない(self):
        旧=記録();新=記録('訂正')
        後=参照全保持を統合((旧,),(新,))[0]
        self.assertEqual(後.内容,'訂正');self.assertEqual(後.旧版[0].内容,旧.内容)
    def test_異なる条件を現版へ混ぜない(self):
        旧=記録(条件=(('温度','高'),));新=記録('訂正',条件=(('温度','低'),))
        後=参照全保持を統合((旧,),(新,))[0]
        self.assertEqual(後.条件,(('温度','低'),));self.assertEqual(後.旧版[0].条件,旧.条件)
    def test_履歴を再帰二重保持しない(self):
        群=()
        for i in range(12):群=参照全保持を統合(群,(記録(str(i)),))
        self.assertEqual(len(群[0].旧版),11)
        self.assertTrue(all(not x.旧版 for x in 群[0].旧版))
    def test_同じ内容を票数や信頼の上昇にしない(self):
        旧=replace(記録(),信頼=0.7);新=replace(記録(),信頼=1.0,供給器='別供給器')
        群=参照全保持を統合((旧,),(新,))
        self.assertEqual(len(群),1);self.assertEqual(群[0].信頼,0.7);self.assertEqual({(x.供給器,x.信頼) for x in 群[0].旧版}, {('供給器',0.7),('別供給器',1.0)})
    def test_信頼訂正だけでも以前の観測を保持する(self):
        旧=replace(記録(),信頼=0.9);新=replace(記録(),信頼=0.2)
        後=参照全保持を統合((旧,),(新,))[0]
        self.assertEqual(後.信頼,0.2)
        self.assertEqual([x.信頼 for x in 後.旧版],[0.9])
        self.assertEqual(参照全保持を統合((後,),(新,))[0],後)
    def test_容量不足でも未保持分を失わない(self):
        with self.assertRaises(参照保持容量超過) as e:
            参照全保持を統合((記録(識別子='一'),),(記録(識別子='二'),),最大件数=1)
        self.assertEqual(len(e.exception.記録群),2)
    def test_作業窓は同一資料の候補query経路を併合し意味条件は混ぜない(self):
        旧=記録('同一本文',条件=(('hds_query_選択肢','A'),('温度','低')))
        新=記録('同一本文',条件=(('hds_query_選択肢','B'),('温度','高')))
        後=参照記録群を統合((旧,),(新,))[0]
        self.assertEqual({v for k,v in 後.条件 if k=='hds_query_選択肢'},{'A','B'})
        self.assertIn(('温度','低'),後.条件)
        self.assertNotIn(('温度','高'),後.条件)

    def test_継承は問い合わせの意味条件と経路を分ける(self):
        原=記録(条件=(('hds_query_選択肢','A'),('温度','低')))
        後=参照経験記憶を統合((),(原,),最大件数=None)[0]
        self.assertEqual(後.条件,(('温度','低'),));self.assertIn(原.条件,後.観測経路履歴)

class 参照取得試験(TestCase):
    def test_成功済み供給器を再取得しない(self):
        正常=提供器();失敗=失敗器()
        複合=複合参照供給器(正常,失敗,並列=False)
        一,診断=複合.検索診断('問い')
        二,再診断=複合.検索診断('問い')
        self.assertEqual(正常.回数,1);self.assertEqual(失敗.回数,1)
        self.assertEqual(一,二);self.assertEqual(診断.状態,'縮退')
        self.assertTrue(再診断.再利用);self.assertEqual(再診断.実取得回数,0)
    def test_429を短間隔で三回叩かない(self):
        器=失敗器()
        with patch('minidora.参照.time.sleep') as 待機:
            _,診断=参照検索を診断(器,'問')
        self.assertEqual(器.回数,1);待機.assert_not_called()
        self.assertEqual(診断.HTTP状態,429);self.assertIn('未提示',診断.延期理由)
    def test_RetryAfter未提示429は同一queryだけ再利用し別queryは試す(self):
        器=失敗器();複合=複合参照供給器(器,並列=False)
        複合.検索診断('問A');複合.検索診断('問A')
        self.assertEqual(器.回数,1)
        複合.検索診断('問B')
        self.assertEqual(器.回数,2)

    def test_RetryAfterより前に再実行しない(self):
        器=失敗器(60);複合=複合参照供給器(器,並列=False)
        with patch('minidora.参照.time.time',return_value=100):
            _,診断=複合.検索診断('問')
        self.assertEqual(診断.子診断[0].再試行可能epoch,160)
        with patch('minidora.参照.time.time',return_value=159):複合.検索診断('別の問')
        self.assertEqual(器.回数,1)
        with patch('minidora.参照.time.time',return_value=160):複合.検索診断('別の問')
        self.assertEqual(器.回数,2)
    def test_HTTP日時指定を尊重(self):
        器=失敗器('Wed, 21 Oct 2015 07:28:00 GMT')
        _,診断=参照検索を診断(器,'問')
        self.assertEqual(診断.再試行可能epoch,1445412480)
    def test_共通締切後は取得しない(self):
        器=提供器()
        with patch('minidora.参照.time.time',return_value=200):
            _,診断=参照検索を診断(器,'問',締切epoch=100)
        self.assertEqual(器.回数,0);self.assertEqual(診断.延期理由,'共通締切到達')
    def test_今回読む上限で全観測を削除しない(self):
        class 多件(提供器):
            def 検索(self,問合せ,上限):return tuple(記録(str(i),str(i)) for i in range(8))
        複合=複合参照供給器(多件(),並列=False)
        群,_=複合.検索診断('問',2)
        self.assertEqual(len(群),2);self.assertEqual(len(複合.全観測記録),8)
    def test_観測版変更は再取得する(self):
        器=提供器();複合=複合参照供給器(器,並列=False)
        複合.検索診断('問');器.観測版='訂正後';複合.検索診断('問')
        self.assertEqual(器.回数,2)

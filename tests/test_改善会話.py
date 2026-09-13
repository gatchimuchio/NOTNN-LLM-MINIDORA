"""第23バッチの有限会話を、実役割計画・実統合採用・実長文脈庫で検証する。"""
import json
import unittest
from copy import deepcopy
from minidora.監査改善会話 import 監査改善会話セッション as Session
from minidora.監査改善会話解釈 import 改善発話を解釈, 資料を構造化, 命題列, 真偽割当, JSONを厳格に読む
from minidora.会話意味 import 意味指紋

REGISTER = '仮説資料「天候」を登録：\n規則：RainならばWet\n規則：SprinklerならばWet\n候補：Rain、Sprinkler'
QUERY = '資料「天候」で観測「Wet」を説明する仮説を検討して'
UPDATE = '仮説資料「天候」を更新：\n規則：RainならばWet\n候補：Rain'
CAUSE = '介入資料「連鎖」を登録：\n外生：U=真\n構造：A=U\n構造：B=A'


def report(result):
    return result.結果.データ['報告']


class 会話試験(unittest.TestCase):
    def setUp(self):
        self.s = Session('試験')

    def send(self, text, expected='合格'):
        r=self.s.応答(text)
        self.assertEqual(r.状態, expected, (text,r.本文,r.理由))
        return r

    def hypotheses(self):
        self.send(REGISTER)
        return self.send(QUERY)

    def test_登録と事実認定を分ける(self):
        r=self.send(REGISTER)
        self.assertIsNone(r.結果)
        self.assertEqual(self.s.統合.採用履歴スナップショット()[1], ())
        self.assertIn('認定していません',r.本文)

    def test_二候補を保持し実三工程から採用(self):
        r=self.hypotheses()
        self.assertEqual({tuple(c['仮説']) for c in report(r)['候補']},{('Rain',),('Sprinkler',)})
        self.assertFalse(report(r)['事実認定'])
        self.assertEqual(len(r.追跡['工程作用']),3)
        self.assertTrue(r.追跡['合成監査整合'])
        self.assertTrue(self.s.統合.原記録(r.追跡['採用記録ID'][0])['現行'])

    def test_観測確認へ戻り返答で目的を完遂(self):
        self.send(REGISTER)
        self.send('資料「天候」で仮説を検討して','確認待ち')
        self.assertEqual(self.s.状態()['保留目的']['理由'],'入力不足:観測')
        r=self.send('観測を「Wet」にして')
        self.assertEqual(len(report(r)['候補']),2)
        self.assertIsNone(self.s.状態()['保留目的'])

    def test_不足資料の登録後に継続(self):
        self.send(QUERY,'確認待ち'); self.send(REGISTER)
        self.assertEqual(len(report(self.send('続けて'))['候補']),2)

    def test_訂正候補を限定する(self):
        self.hypotheses()
        r=self.send('候補を「Rain」に訂正して')
        self.assertEqual([c['仮説'] for c in report(r)['候補']],[['Rain']])

    def test_観測変更は元の観測を残さない(self):
        self.hypotheses()
        r=self.send('観測を「Dry」に訂正して')
        self.assertEqual(report(r)['要求']['観測'], ['Dry'])
        self.assertEqual(report(r)['候補'],[])

    def test_短縮しても仮定と限界を保持する(self):
        original=self.hypotheses(); r=self.send('短く説明して')
        self.assertFalse(r.結果.データ['詳細'])
        self.assertEqual(report(r),report(original))
        self.assertEqual(len(r.追跡['工程作用']),2)
        self.assertIn('仮定',r.本文);self.assertIn(report(r)['限界'],r.本文)

    def test_資料更新で全依存回答を失効する(self):
        a=self.hypotheses();b=self.send('短く説明して');self.send(UPDATE)
        for r in (a,b):
            row=self.s.統合.原記録(r.追跡['採用記録ID'][0])
            self.assertFalse(row['現行']);self.assertTrue(row['内容'])
        self.assertEqual(self.s.統合.採用履歴スナップショット()[1],())
        self.send('短く説明して','保留')
        c=self.send('もう一度')
        self.assertEqual([x['現行'] for x in self.s.状態()['成果']],[False,False,True])
        self.assertEqual([x['仮説'] for x in report(c)['候補']],[['Rain']])

    def test_同一資料更新は成果を失効しない(self):
        self.hypotheses();self.send(REGISTER.replace('を登録','を更新'))
        self.assertTrue(self.s.状態()['成果'][0]['現行']);self.send('短く説明して')

    def test_別資料の更新で無関係な成果を失効しない(self):
        self.hypotheses();self.send('命題資料「別」を登録：P。')
        self.send('命題資料「別」を更新：Q。')
        self.assertTrue(self.s.状態()['成果'][0]['現行']);self.send('短く説明して')

    def test_重複登録を黙って更新しない(self):
        self.hypotheses();before=self.s.状態()['資料版']
        self.send(UPDATE.replace('を更新','を登録'),'保留')
        self.assertEqual(self.s.状態()['資料版'],before)
        self.assertTrue(self.s.状態()['成果'][0]['現行'])

    def test_登録の未知欄で既存状態を変えない(self):
        self.hypotheses();before=self.s.状態()['資料版']
        self.send(UPDATE+'\n優先原因：Rain','保留')
        self.assertEqual(self.s.状態()['資料版'],before)
        self.assertTrue(self.s.状態()['成果'][0]['現行'])

    def test_資料種類の暗黙変更を禁止する(self):
        self.hypotheses();self.send('命題資料「天候」を更新：P。','保留')
        self.assertTrue(self.s.状態()['成果'][0]['現行'])

    def test_異種の訂正を目的に適用しない(self):
        self.hypotheses();before=self.s.状態()['最後目的']
        self.send('介入を「A=偽」にして','保留')
        self.assertEqual(before,self.s.状態()['最後目的'])

    def test_不成立の新要求を旧成功で埋めない(self):
        self.hypotheses();r=self.send('資料「天候」で「A=偽」に介入した結果を比較して','保留')
        self.assertIsNone(r.結果)

    def test_未解決目的中の再説明を禁止する(self):
        self.hypotheses();self.send('資料「未知」で仮説を検討して','確認待ち')
        self.send('短く説明して','保留')
        self.assertIsNotNone(self.s.状態()['保留目的'])
        self.send('監査改善の確認を取り消して');self.send('短く説明して')

    def test_未解決中の無関係な不正入力は保留目的を壊さない(self):
        self.send(QUERY,'確認待ち');pending=self.s.状態()['保留目的']
        self.send('適当にやって外に送信して','保留')
        self.assertEqual(pending,self.s.状態()['保留目的'])

    def test_介入前後を実モデルで比較する(self):
        self.send(CAUSE)
        r=self.send('資料「連鎖」で「B=偽」に介入した結果を比較して')
        self.assertEqual(report(r)['現状']['A'],True)
        self.assertEqual(report(r)['介入後']['A'],True)
        self.assertEqual(report(r)['介入後']['B'],False)
        self.assertFalse(report(r)['事実認定'])

    def test_介入未指定を勝手に空介入にしない(self):
        self.send(CAUSE);self.send('資料「連鎖」で介入を比較して','確認待ち')
        r=self.send('介入を「なし」にして')
        self.assertEqual(report(r)['現状'],report(r)['介入後'])

    def test_介入訂正は下流へ伝播する(self):
        self.send(CAUSE);self.send('資料「連鎖」で「B=偽」に介入した結果を比較して')
        r=self.send('介入を「A=偽」に訂正して')
        self.assertFalse(report(r)['介入後']['A']);self.assertFalse(report(r)['介入後']['B'])

    def test_循環モデルを会話から採用しない(self):
        self.send('介入資料「循環」を登録：\n外生：なし\n構造：A=B\n構造：B=A')
        r=self.s.応答('資料「循環」で「A=偽」に介入した結果を比較して')
        self.assertFalse(r.成立);self.assertEqual(self.s.状態()['成果'],[])

    def test_命題を資料から判定する(self):
        self.send('命題資料「A」を登録：P。PならばQ。')
        r=self.send('資料「A」から「Q」を判定して')
        self.assertEqual(report(r)['状態'],'支持')

    def test_引用内容を現実へ昇格しない(self):
        self.send('命題資料「A」を登録：太郎は「P」と述べた。')
        r=self.send('資料「A」から「P」を判定して')
        self.assertEqual(report(r)['状態'],'未確定')

    def test_問い候補を先頭に固定せず確認する(self):
        self.send('命題資料「A」を登録：P。')
        self.send('資料「A」から「PまたはQかつR」を判定して','確認待ち')
        self.assertEqual(self.s.状態()['保留目的']['理由'],'問い候補未確定')
        self.send('問い候補2で続けて')
        self.assertEqual(self.s.状態()['最後目的']['変更']['問い候補'],2)

    def test_資料候補の分岐を確認し選択条件を保持する(self):
        self.send('命題資料「A」を登録：PまたはQかつR。')
        self.send('資料「A」から「R」を判定して','確認待ち')
        self.assertEqual(self.s.状態()['保留目的']['理由'],'資料候補未確定')
        r=self.send('資料候補2で続けて')
        self.assertEqual(report(r)['判定結果']['解釈状態'],'利用者選択')
        self.assertEqual(report(r)['要求']['資料候補'],2)

    def test_共通結論は読みの一意性にしない(self):
        self.send('命題資料「A」を登録：PまたはQかつR。')
        r=self.send('資料「A」から「PまたはQ」を判定して')
        self.assertEqual(report(r)['状態'],'支持')
        self.assertEqual(report(r)['判定結果']['解釈状態'],'読み未確定')

    def test_提示されていない候補を選ばない(self):
        self.send('命題資料「A」を登録：PまたはQかつR。')
        self.send('資料「A」から「R」を判定して','確認待ち')
        pending=self.s.状態()['保留目的'];self.send('資料候補99で続けて','保留')
        self.assertEqual(pending,self.s.状態()['保留目的'])

    def test_確認中の資料変更は旧候補選択を止める(self):
        self.send('命題資料「A」を登録：PまたはQかつR。')
        self.send('資料「A」から「R」を判定して','確認待ち')
        self.send('命題資料「A」を更新：R。');self.send('資料候補2で続けて','保留')
        r=self.send('もう一度');self.assertEqual(report(r)['状態'],'支持')
        self.assertNotIn('資料候補',report(r)['要求'])

    def test_確認中の資料変更は無指定継続でも止める(self):
        self.send(REGISTER);self.send('資料「天候」で仮説を検討して','確認待ち')
        self.send(UPDATE);self.send('続けて','保留')
        self.send('観測を「Wet」にして')

    def test_有界照応距離の明示訂正(self):
        self.send('命題資料「A」を登録：太郎は猫である。P。彼は鳥である。')
        # 不成立時も同じ目的へ訂正できることを要求する。
        self.send('資料「A」から「太郎は鳥である」を判定して','保留')
        r=self.send('照応距離を3にして')
        self.assertEqual(report(r)['状態'],'支持')

    def test_元の資料に未解釈尾部があれば採用しない(self):
        self.send('命題資料「A」を登録：P。ただし例外がある。')
        self.send('資料「A」から「P」を判定して','保留')
        self.assertEqual(self.s.状態()['成果'],[])

    def test_停止は資料も発話も変えない(self):
        before=self.s.状態();r=self.s.応答(REGISTER,停止要求=lambda:True)
        self.assertEqual(r.状態,'中止');self.assertEqual(before,self.s.状態())

    def test_実行中の停止は採用記録を増やさない(self):
        self.send(REGISTER);before=self.s.状態();calls=[]
        def stop():
            calls.append(1);return len(calls)>=7
        r=self.s.応答(QUERY,停止要求=stop)
        self.assertEqual(r.状態,'中止',r.辞書化());self.assertEqual(before,self.s.状態())
        self.assertEqual(self.s.統合.採用履歴スナップショット()[1],())

    def test_停止判定の整数をboolとみなさない(self):
        before=self.s.状態();r=self.s.応答(REGISTER,停止要求=lambda:1)
        self.assertFalse(r.成立);self.assertEqual(before,self.s.状態())

    def test_会話ロック中は別処理を採用しない(self):
        self.s._ロック.acquire()
        try:self.assertEqual(self.s.応答(REGISTER).理由,'処理中')
        finally:self.s._ロック.release()
        self.assertEqual(self.s.状態()['発話数'],0)

    def test_発話上限で無言削除しない(self):
        s=Session('limit',最大発話=1);self.assertTrue(s.応答(REGISTER).成立)
        before=s.状態();r=s.応答(QUERY)
        self.assertEqual(r.理由,'保存予算上限');self.assertEqual(before,s.状態())

    def test_別話題後の省略発話を奪わない(self):
        self.hypotheses()
        self.assertTrue(self.s.対応する('短く説明して'))
        self.assertFalse(self.s.対応する('短く説明して',継続許可=False))
        self.assertTrue(self.s.対応する(QUERY,継続許可=False))
        self.assertTrue(self.s.対応する('資料候補2で続けて'))

    def test_共有先の初期化で古い成果を復活させない(self):
        self.hypotheses();self.s.統合.初期化()
        self.assertFalse(self.s.状態()['成果'][0]['現行']);self.send('短く説明して','保留')


class 保存復元試験(unittest.TestCase):
    def built(self):
        s=Session('保存')
        for text in (REGISTER,QUERY,'短く説明して',UPDATE,'短く説明して','もう一度'):
            s.応答(text)
        return s

    def test_純粋再実行で失効履歴まで往復(self):
        s=self.built();text=s.保存文字列();r=Session.復元(text,期待セッションID='保存')
        self.assertEqual(s.状態(),r.状態());self.assertEqual(text,r.保存文字列())
        self.assertNotEqual(s.統合.起点().所有ID,r.統合.起点().所有ID)
        self.assertTrue(r.応答('短く説明して').成立)

    def test_確認待ちを復元して返答を受ける(self):
        s=Session();s.応答(REGISTER);s.応答('資料「天候」で仮説を検討して')
        r=Session.復元(s.保存文字列());self.assertTrue(r.応答('観測を「Wet」にして').成立)

    def test_表面ハッシュだけの改変を拒否(self):
        raw=json.loads(self.built().保存文字列());raw['状態印']='0'*64
        raw['記録SHA256']=意味指紋({k:v for k,v in raw.items() if k!='記録SHA256'})
        with self.assertRaises(ValueError):Session.復元(json.dumps(raw,ensure_ascii=False))

    def test_履歴を書換え再ハッシュしても返答再計算で拒否(self):
        raw=json.loads(self.built().保存文字列());raw['履歴'][1]['原文']=QUERY.replace('Wet','Dry')
        for i,event in enumerate(raw['履歴']):
            if i:event['前ハッシュ']=raw['履歴'][i-1]['ハッシュ']
            event['ハッシュ']=意味指紋({k:v for k,v in event.items() if k!='ハッシュ'})
        raw['記録SHA256']=意味指紋({k:v for k,v in raw.items() if k!='記録SHA256'})
        with self.assertRaises(ValueError):Session.復元(json.dumps(raw,ensure_ascii=False))

    def test_別セッション用として復元しない(self):
        with self.assertRaises(ValueError):Session.復元(self.built().保存文字列(),期待セッションID='other')

    def test_未対応版を自動移行しない(self):
        from minidora.監査改善会話 import 改善会話版
        text=self.built().保存文字列().replace(改善会話版,'MINIDORA-監査改善会話-v99')
        with self.assertRaises(ValueError):Session.復元(text)

    def test_共有統合の一部履歴を全体保存扱いしない(self):
        from minidora.統合実行 import 統合セッション
        from minidora.監査改善計画 import 改善統合能力群
        backend=統合セッション('shared',基底能力=改善統合能力群())
        s=Session('shared',統合=backend)
        with self.assertRaises(ValueError):s.保存文字列()

    def test_外部から初期化した統合状態を保存しない(self):
        s=self.built();s.統合.初期化()
        with self.assertRaises(ValueError):s.保存文字列()

    def test_資料版が同じなのに外部失効した状態を保存しない(self):
        s=self.built();key=s._成果[-1]['記録ID']
        s.統合.記録を失効(s.統合.起点(),(key,),理由='別の操作')
        with self.assertRaises(ValueError):s.保存文字列()

    def test_空会話も往復する(self):
        s=Session();self.assertEqual(s.状態(),Session.復元(s.保存文字列()).状態())


class 表層解釈試験(unittest.TestCase):
    def test_資料末尾句点と原文位置を保持する(self):
        text='命題資料「文」を登録：太郎は猫である。'
        self.assertEqual(改善発話を解釈(text)['本文'],'太郎は猫である。')
        result=改善発話を解釈(REGISTER)
        for row in result['原文対応']:
            self.assertEqual(result['本文'][row['開始']:row['終了']],row['原文'])
        self.assertEqual(result['原文'],REGISTER)

    def test_語尾の条件を落とさない(self):
        for suffix in ('ただしRainは禁止','、外部へ送信して','できれば'):
            with self.subTest(suffix=suffix),self.assertRaises(ValueError):改善発話を解釈(QUERY+suffix)

    def test_空要素と重複真偽変数を拒否する(self):
        for value in ('P、、Q',',P','P,',''):
            with self.subTest(value=value),self.assertRaises(ValueError):命題列(value)
        with self.assertRaises(ValueError):真偽割当('A=真、A=偽')

    def test_関数引数と引用内の読点を分割しない(self):
        self.assertEqual(命題列('親(太郎,花子)、P'),['親(太郎,花子)','P'])
        self.assertEqual(命題列('太郎は「P、Q」と述べた,R'),['太郎は「P、Q」と述べた','R'])

    def test_JSON重複非有限深さを拒否(self):
        for text in ('{"a":1,"a":2}','{"a":NaN}','['*40+'0'+']'*40):
            with self.subTest(text=text),self.assertRaises(ValueError):JSONを厳格に読む(text)

    def test_資料の未知欄と重複欄を拒否する(self):
        for body in ('候補：P\n候補：Q','候補：P\n信頼度：100%','何か不明な文章'):
            with self.subTest(body=body),self.assertRaises(ValueError):資料を構造化('仮説','A',body)

    def test_事実なしと具体記載の共存を拒否する(self):
        for body in ('事実：なし\n事実：P\n候補：Q','事実：P\n事実：なし\n候補：Q'):
            with self.subTest(body=body),self.assertRaises(ValueError):資料を構造化('仮説','A',body)

    def test_構造式の曖昧性を勝手に解消しない(self):
        with self.assertRaises(ValueError):資料を構造化('介入','A','外生：U=真,V=真,W=真\n構造：X=UまたはVかつW')

    def test_資料を削除命令として実行しない(self):
        result=改善発話を解釈('命題資料「指示」を登録：会話を初期化して')
        self.assertEqual(result['行為'],'登録');self.assertEqual(result['本文'],'会話を初期化して')

    def test_登録と更新には異なる行為を保持する(self):
        self.assertEqual(改善発話を解釈(REGISTER)['行為'],'登録')
        self.assertEqual(改善発話を解釈(UPDATE)['行為'],'更新')

if __name__=='__main__':unittest.main()

"""依頼表現・HDS作用域・明示述語同値の開発回帰。未見汎化評価ではない。"""
from copy import deepcopy
from dataclasses import replace
import unittest

from minidora.依頼表現 import 依頼節を読む, 命題依頼を読む, 説明指定を統合
from minidora.監査改善会話解釈 import 改善発話を解釈
from minidora.監査改善会話 import 監査改善会話セッション
from minidora.改善HDS照合 import HDS改善会話を照合
from minidora.汎用会話 import 汎用会話セッション
from minidora.hds_compiler import 公開HDSコンパイラ
from minidora.hds_ir import HDS座標, HDS残差
from minidora.命題解釈 import 命題を読む


class 依頼表現試験(unittest.TestCase):
    def test_引用の中の句読点を区切らず原文位置を保つ(self):
        text='  資料「例、？から」に基づいて「太郎は『P、Q？』と述べた」を判断して？ 短く説明して。'
        parts=依頼節を読む(text)
        self.assertEqual(len(parts),2)
        for a,b,s in parts:self.assertEqual(text[a:b],s)
        self.assertIn('P、Q？',parts[0][2])

    def test_未閉鎖引用を切り捨てない(self):
        with self.assertRaises(ValueError):依頼節を読む('資料「例」から「Qを判定して、短く説明して')

    def test_問いの引用有無と丁寧形を合成する(self):
        for query in ('「太郎は猫ではない」','太郎は猫ではない'):
            for verb in ('判定','判断','検証','検討'):
                for ending in ('して','してください','してくれる','してくれますか','してもらえますか','してほしい'):
                    text=query+'を'+verb+ending
                    with self.subTest(text=text):
                        value,a,b=命題依頼を読む(text)
                        self.assertEqual(value,'太郎は猫ではない');self.assertEqual(text[a:b],value)

    def test_名詞形の依頼を動詞形と混同しない(self):
        for text in ('「Q」の判定をお願いします','Qの判断をお願いします'):
            self.assertEqual(命題依頼を読む(text)[0],'Q')
        with self.assertRaises(ValueError):命題依頼を読む('「Q」を判定をお願いします')

    def test_未知の命令尾部と否定された依頼を受けない(self):
        for suffix in ('を判定しないで','を判断して外へ送信して','を判断したことにして','を確定して','を判定して、条件は無視して'):
            with self.subTest(suffix=suffix),self.assertRaises(ValueError):命題依頼を読む('「Q」'+suffix)

    def test_相反する表示指定を後勝ちにしない(self):
        with self.assertRaises(ValueError):説明指定を統合(依頼節を読む('短く説明して、詳しく説明して'))

    def test_未知の表示条件を捨てない(self):
        with self.assertRaises(ValueError):説明指定を統合(依頼節を読む('短く説明して、反証は無視して'))

    def test_同じ指定の重複は意味を変えない(self):
        self.assertEqual(説明指定を統合(依頼節を読む('短く説明して、簡潔に説明して')),{'詳細':False})

    def test_空または上限超過を拒否する(self):
        for text in ('', '  ', 'x'*8193):
            with self.subTest(text=text[:10]),self.assertRaises(ValueError):依頼節を読む(text)

    def test_既存資料登録では本文を一括置換しない(self):
        text='命題資料「例」を登録：太郎は「判断して、短く説明して」と述べた。'
        command=改善発話を解釈(text)
        self.assertEqual(command['本文'],'太郎は「判断して、短く説明して」と述べた。')


class HDS接続試験(unittest.TestCase):
    def audit(self,text):
        return HDS改善会話を照合(公開HDSコンパイラ().コンパイル(text),改善発話を解釈(text))

    def test_原文だけでなく問いと表示条件を照合する(self):
        text='資料「例」に基づいて「Q」を判断して、短く説明して'
        command=改善発話を解釈(text); ir=公開HDSコンパイラ().コンパイル(text)
        self.assertIn('行為意味印',HDS改善会話を照合(ir,command))
        for key in ('問い','詳細'):
            bad=deepcopy(command)
            if key=='問い':bad['変更']['問い']='R'
            else:bad['詳細']=True
            with self.subTest(key=key),self.assertRaises(ValueError):HDS改善会話を照合(ir,bad)

    def test_実HDS再構成で未知座標を検出する(self):
        text='資料「例」から「Q」を判断して'; ir=公開HDSコンパイラ().コンパイル(text)
        bad=replace(ir,座標=(*ir.座標,HDS座標('追加','未対応','未知条件')))
        with self.assertRaises(ValueError):HDS改善会話を照合(bad,改善発話を解釈(text))

    def test_改変した残差を消さず拒否する(self):
        text='資料「例」から「Q」を判断して'; ir=公開HDSコンパイラ().コンパイル(text)
        bad=replace(ir,残差=(*ir.残差,HDS残差('r','semantic_loss','Q','意味損失')))
        with self.assertRaises(ValueError):HDS改善会話を照合(bad,改善発話を解釈(text))

    def test_資料内の条件と否定を依頼へ移さない(self):
        value=self.audit('命題資料「例」を登録：PならばQ。太郎は猫ではない。')
        self.assertTrue(value['座標残差対応'])
        self.assertIn('登録Dataとして保持',str(value))

    def test_引用なしの否定命題も問いの範囲へ対応する(self):
        value=self.audit('資料「例」に基づいて太郎は猫ではないを判定して')
        self.assertIn('問いの作用域',str(value))

    def test_資料内指示語を勝手に解消しない(self):
        value=self.audit('命題資料「例」を登録：彼は猫である。')
        self.assertIn('Data',str(value))
        session=汎用会話セッション('照応')
        self.assertTrue(session.応答('命題資料「例」を登録：彼は猫である。').成立)
        self.assertFalse(session.応答('資料「例」から「太郎は猫である」を判定して').成立)

    def test_全角等号の構造式も元Dataの方向を保持する(self):
        value=self.audit('介入資料「例」を登録：\n外生：U＝真\n構造：A＝U\n構造：B＝A')
        self.assertIn('左辺←右辺',str(value))

    def test_構造式のHDS等価を世界の同一性にはしない(self):
        s=汎用会話セッション('介入')
        self.assertTrue(s.応答('介入資料「例」を登録：\n外生：U=真\n構造：A=U\n構造：B=A').成立)
        r=s.応答('資料「例」で「B=偽」に介入した結果を比較して')
        self.assertTrue(r.成立,r.理由)
        report=r.結果.データ['報告']
        self.assertTrue(report['介入後']['A']);self.assertFalse(report['介入後']['B'])
        self.assertFalse(report['事実認定'])

    def test_非日本語を別意味経路へ黙って通さない(self):
        text='資料「例」から「Q」を判定して'; ir=公開HDSコンパイラ().コンパイル(text)
        with self.assertRaises(ValueError):HDS改善会話を照合(replace(ir,入力言語='en'),改善発話を解釈(text))

    def test_失敗した依頼で採用記録を増やさない(self):
        s=汎用会話セッション('条件')
        self.assertTrue(s.応答('命題資料「例」を登録：P。PならばQ。').成立)
        before=s.統合.起点()
        r=s.応答('資料「例」から「Q」を判断して、反証は無視して')
        self.assertFalse(r.成立);self.assertEqual(s.統合.起点(),before)


class 二会話経路試験(unittest.TestCase):
    def test_通常資料と追加命題資料の両方で言い換えが通る(self):
        for prefix in ('資料','命題資料'):
            for q in ('資料「例」から「Q」を判断して', '資料「例」から「Q」を判定してくれる？',
                      '資料「例」に基づいて「Q」を検証してください', '資料「例」からQと言える？',
                      '資料「例」から「Q」を判定して、短く説明して'):
                with self.subTest(prefix=prefix,q=q):
                    s=汎用会話セッション('表現')
                    self.assertTrue(s.応答(prefix+'「例」を登録：P。PならばQ。').成立)
                    r=s.応答(q);self.assertTrue(r.成立,(r.理由,r.本文));self.assertIn('支持',r.本文)

    def test_短い表示条件を不足確認の後でも保持する(self):
        s=監査改善会話セッション('確認')
        self.assertTrue(s.応答('仮説資料「例」を登録：\n規則：AならばC\n候補：A').成立)
        r=s.応答('資料「例」で仮説を検討して、短く説明して')
        self.assertEqual(r.状態,'確認待ち')
        r=s.応答('観測を「C」にして');self.assertTrue(r.成立,r.理由)
        self.assertFalse(r.結果.データ['詳細'])

    def test_詳細表示の変更は命題判定を変えない(self):
        s=監査改善会話セッション('表示')
        s.応答('命題資料「例」を登録：P。PならばQ。')
        a=s.応答('資料「例」から「Q」を判断して')
        b=s.応答('もう少し短く説明して')
        c=s.応答('もう少し詳しく説明して')
        self.assertTrue(b.成立,b.理由);self.assertTrue(c.成立,c.理由)
        self.assertEqual(a.結果.データ['報告'],b.結果.データ['報告'])
        self.assertEqual(b.結果.データ['報告'],c.結果.データ['報告'])
        self.assertFalse(b.結果.データ['詳細']);self.assertTrue(c.結果.データ['詳細'])

    def test_保存再生でも合成した表示指定を保持する(self):
        s=監査改善会話セッション('保存')
        s.応答('命題資料「例」を登録：P。PならばQ。')
        s.応答('資料「例」に基づいて「Q」を判断して、短く説明して')
        restored=監査改善会話セッション.復元(s.保存文字列(),期待セッションID='保存')
        self.assertEqual(s.状態(),restored.状態())
        self.assertTrue(restored.応答('もう少し詳しく説明して').成立)


class 明示述語同値試験(unittest.TestCase):
    def judge(self,text,query):
        s=監査改善会話セッション('述語')
        self.assertTrue(s.応答('命題資料「例」を登録：'+text).成立)
        r=s.応答('資料「例」から「'+query+'」を判断して')
        self.assertTrue(r.成立,(r.理由,r.本文));return r.結果.データ['報告']['状態']

    def test_定義なしで猫とネコを同一視しない(self):
        self.assertEqual(self.judge('太郎はネコである。すべての猫は哺乳類である。','太郎は哺乳類である'),'未確定')

    def test_明示同値を所属と全称規則に合成する(self):
        self.assertEqual(self.judge('太郎はネコである。述語「ネコ」と「猫」は同値である。すべての猫は哺乳類である。','太郎は哺乳類である'),'支持')

    def test_同値は逆方向も扱える(self):
        self.assertEqual(self.judge('太郎は猫である。述語「ネコ」と「猫」は同値です。','太郎はネコである'),'支持')

    def test_三述語の接続は固定辞書なしで導く(self):
        self.assertEqual(self.judge('太郎は甲である。述語「甲」と「乙」は同値である。述語「乙」と「丙」は同値である。','太郎は丙である'),'支持')

    def test_他者の同値発言を世界の同値へ昇格しない(self):
        self.assertEqual(self.judge('太郎は甲である。花子は「述語『甲』と『乙』は同値である」と述べた。','太郎は乙である'),'未確定')

    def test_時点指定の同値を無時点へ漏らさない(self):
        self.assertEqual(self.judge('太郎は甲である。時点「2025」では（述語「甲」と「乙」は同値である）。','太郎は乙である'),'未確定')

    def test_個体の同一性として使わない(self):
        self.assertEqual(self.judge('猫(甲)。述語「甲」と「乙」は同値である。','猫(乙)'),'未確定')

    def test_資料更新で同値に依存する旧回答を失効する(self):
        s=監査改善会話セッション('更新')
        s.応答('命題資料「例」を登録：太郎は甲である。述語「甲」と「乙」は同値である。')
        before=s.応答('資料「例」から「太郎は乙である」を判断して')
        self.assertTrue(before.成立)
        s.応答('命題資料「例」を更新：太郎は甲である。')
        self.assertFalse(s.統合.原記録(before.追跡['採用記録ID'][0])['現行'])
        after=s.応答('資料「例」から「太郎は乙である」を判断して')
        self.assertEqual(after.結果.データ['報告']['状態'],'未確定')

    def test_未対応の条件付き量化定義を無条件の同値にしない(self):
        s=監査改善会話セッション('条件定義')
        s.応答('命題資料「例」を登録：太郎は甲である。Pならば（述語「甲」と「乙」は同値である）。')
        before=s.統合.起点()
        r=s.応答('資料「例」から「太郎は乙である」を判断して')
        self.assertFalse(r.成立);self.assertIsNone(r.結果);self.assertEqual(s.統合.起点(),before)

    def test_未対応の否定量化定義を正の規則へ変えない(self):
        s=監査改善会話セッション('否定定義')
        s.応答('命題資料「例」を登録：太郎は甲である。否定（述語「甲」と「乙」は同値である）。')
        before=s.統合.起点()
        r=s.応答('資料「例」から「太郎は乙である」を判断して')
        self.assertFalse(r.成立);self.assertIsNone(r.結果);self.assertEqual(s.統合.起点(),before)

    def test_未知限定と壊れた同値を取り込まない(self):
        for text in ('述語「甲」と「乙」は同値ではない','述語「甲」と「乙」は同値であるが例外がある','述語「甲ならば乙」と「乙」は同値である'):
            with self.subTest(text=text),self.assertRaises(ValueError):命題を読む(text)

if __name__=='__main__':unittest.main()

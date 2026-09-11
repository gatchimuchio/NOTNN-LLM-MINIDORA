"""命題内容からの導出。支持・反証・未知をラベルや不在で捏造しない。"""
import unittest
from minidora.命題解釈 import 命題を読む, 命題資料を読む
from minidora.命題推論 import 命題推論器, 推論上限


class 命題推論試験(unittest.TestCase):
    def result(self,source,query):
        rows=命題資料を読む(source,'資料')
        e=命題を読む(query)
        self.assertEqual(len(e),1)
        return 命題推論器(rows).判定(e[0].式)
    def status(self,source,query,status):self.assertEqual(self.result(source,query)['判定'],status)
    def test_直接支持(self):self.status('P。','P','支持')
    def test_直接反証(self):self.status('否定(P)。','P','反証')
    def test_支持反証を同時保持(self):self.status('P。否定(P)。','P','矛盾')
    def test_未知は偽ではない(self):self.status('P。','Q','未確定')
    def test_矛盾から任意結論を生成しない(self):self.status('P。否定(P)。','Q','未確定')
    def test_条件導出(self):self.status('P。PならばQ。','Q','支持')
    def test_条件連鎖(self):self.status('P。PならばQ。QならばR。','R','支持')
    def test_後件肯定をしない(self):self.status('Q。PならばQ。','P','未確定')
    def test_前件否定で後件を否定しない(self):self.status('否定(P)。PならばQ。','否定(Q)','未確定')
    def test_連言前件は両方必要(self):self.status('P。PかつQならばR。','R','未確定')
    def test_連言前件が成立(self):self.status('P。Q。PかつQならばR。','R','支持')
    def test_連言結論を分解(self):self.status('P。PならばQかつR。','R','支持')
    def test_選言記載を勝手に片方へしない(self):self.status('PまたはQ。','P','未確定')
    def test_選言導入(self):self.status('P。','PまたはQ','支持')
    def test_選言全体の前件を使える(self):self.status('PまたはQ。(PまたはQ)ならばR。','R','支持')
    def test_連言を否定するには一つの反証で足りる(self):self.status('否定(P)。','PかつQ','反証')
    def test_選言の反証は両方を要する(self):self.status('否定(P)。','PまたはQ','未確定')
    def test_選言反証(self):self.status('否定(P)。否定(Q)。','PまたはQ','反証')
    def test_DeMorganの作用域(self):self.status('否定(PまたはQ)。','否定(P)かつ否定(Q)','支持')
    def test_条件を仮定導入で推移(self):self.status('PならばQ。QならばR。','PならばR','支持')
    def test_条件の反証に実際の前件と否定後件が必要(self):self.status('P。否定(Q)。','PならばQ','反証')
    def test_条件反証の前件不足(self):self.status('否定(Q)。','PならばQ','未確定')
    def test_条件仮定を次の問いへ漏らさない(self):
        e=命題推論器(命題資料を読む('PならばQ。QならばR。','資料'))
        e.判定(命題を読む('PならばR')[0].式)
        self.assertEqual(e.判定(命題を読む('P')[0].式)['判定'],'未確定')
    def test_全称の具体化(self):self.status('すべての猫は哺乳類である。太郎は猫である。','太郎は哺乳類である','支持')
    def test_全称の推移(self):self.status('すべての猫は哺乳類である。すべての哺乳類は動物である。','すべての猫は動物である','支持')
    def test_有限事例を全称化しない(self):self.status('太郎は猫である。太郎は動物である。','すべての猫は動物である','未確定')
    def test_存在から具体的個体を発明しない(self):self.status('一部の猫は鳥である。','太郎は鳥である','未確定')
    def test_存在証拠で存在を導く(self):self.status('太郎は猫である。太郎は鳥である。','一部の猫は鳥である','支持')
    def test_存在の同じ証人を保持(self):self.status('一部の猫は鳥である。','一部の鳥は猫である','支持')
    def test_別の存在証人を同一視しない(self):self.status('一部の猫は鳥である。一部の猫は魚である。','一部の鳥は魚である','未確定')
    def test_全称包含から存在を作らない(self):self.status('すべての猫は鳥である。','一部の猫は鳥である','未確定')
    def test_全称の反例(self):self.status('太郎は猫である。太郎は鳥ではない。','すべての猫は鳥である','反証')
    def test_存在の全称反証(self):self.status('すべてのxについて(猫(x)ならば否定(鳥(x)))。','一部の猫は鳥である','反証')
    def test_全称と反例の衝突(self):self.status('すべての猫は鳥である。太郎は猫である。太郎は鳥ではない。','すべての猫は鳥である','矛盾')
    def test_二項関係の変数束縛(self):self.status('親(太郎,花子)。すべてのxについて(すべてのyについて(親(x,y)ならば保護者(x,y)))。','保護者(太郎,花子)','支持')
    def test_二項関係の左右を入れ替えない(self):self.status('親(太郎,花子)。','親(花子,太郎)','未確定')
    def test_異時点を矛盾にしない(self):self.status('2025年では(P)。2026年では(否定(P))。','2025年では(P)','支持')
    def test_未指定時点へ自動昇格しない(self):self.status('2025年では(P)。','P','未確定')
    def test_時点付き条件(self):self.status('2025年では(P)。2025年では(PならばQ)。','2025年では(Q)','支持')
    def test_他時点の条件を利用しない(self):self.status('2025年では(P)。2026年では(PならばQ)。','2025年では(Q)','未確定')
    def test_可能性と実際を区別(self):self.status('可能性として(P)。','P','未確定')
    def test_義務と実際を区別(self):self.status('義務として(P)。','P','未確定')
    def test_停止予算を成功へしない(self):
        engine=命題推論器(命題資料を読む('P。PならばQ。','資料'),上限=推論上限(操作数=1))
        with self.assertRaises(ValueError):engine.判定(命題を読む('Q')[0].式)
    def test_循環規則は停止する(self):self.status('P。PならばQ。QならばP。','Q','支持')
    def test_根拠グラフが全件閉じる(self):
        r=self.result('P。PならばQ。QならばR。','R')
        for p in r['導出'].values():self.assertTrue(set(p['親'])<=set(r['導出']))
    def test_支持反証の根拠が別(self):
        r=self.result('P。否定(P)。','P');self.assertNotEqual(r['支持'],r['反証'])
    def test_存在と全称の無制限入れ子は停止(self):
        with self.assertRaises(ValueError):self.result('すべてのxについて(あるyについて(親(x,y)))。','P')
    def test_同じ問いの反復で同じ結果(self):
        e=命題推論器(命題資料を読む('P。PならばQ。','資料'));q=命題を読む('Q')[0].式
        self.assertEqual(e.判定(q),e.判定(q))

if __name__=='__main__':unittest.main()

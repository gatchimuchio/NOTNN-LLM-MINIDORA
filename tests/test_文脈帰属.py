"""帰属・照応・資料候補の原文対応と作用域。世界知識を使わない人工資料。"""
from dataclasses import replace
import json
import unittest
from minidora.命題構造 import 命題を復元, 原子群, 置換, 命題項
from minidora.命題解釈 import 命題を読む, 命題資料を読む, 命題を表現
from minidora.命題推論 import 命題推論器
from minidora.文脈命題 import 文脈資料を読む, 解釈場合を構成, 文脈判定


class 帰属試験(unittest.TestCase):
    def judge(self, source, query):
        return 命題推論器(命題資料を読む(source, '資料')).判定(命題を読む(query)[0].式)['判定']
    def test_発言の内容を事実にしない(self):
        self.assertEqual(self.judge('太郎は「P」と述べた。', 'P'), '未確定')
    def test_発言記載そのものは支持できる(self):
        self.assertEqual(self.judge('太郎は「P」と述べた。', '太郎は「P」と述べた'), '支持')
    def test_信念から現実を導かない(self):
        self.assertEqual(self.judge('花子は「P」と考えている。', 'P'), '未確定')
    def test_信念は発言ではない(self):
        self.assertEqual(self.judge('花子は「P」と考えている。', '花子は「P」と述べている'), '未確定')
    def test_過去と現在の信念は別(self):
        self.assertEqual(self.judge('花子は「P」と考えていた。', '花子は「P」と考えている'), '未確定')
    def test_伝聞から現実を導かない(self):
        self.assertEqual(self.judge('資料甲によると「P」。', 'P'), '未確定')
    def test_異なる話者を混同しない(self):
        self.assertEqual(self.judge('太郎は「P」と述べた。', '花子は「P」と述べた'), '未確定')
    def test_引用内選言を外側の選言にしない(self):
        self.assertEqual(self.judge('太郎は「PまたはQ」と考えている。PならばR。QならばR。', 'R'), '未確定')
    def test_引用内の矛盾を現実の矛盾にしない(self):
        self.assertEqual(self.judge('太郎は「Pかつ否定(P)」と考えている。', 'P'), '未確定')
    def test_二重帰属を一層へ潰さない(self):
        self.assertEqual(self.judge('太郎は「花子は『P』と考えている」と述べた。', '花子は「P」と考えている'), '未確定')
    def test_帰属全体の否定と内容否定を分離(self):
        self.assertEqual(self.judge('太郎は「否定(P)」と述べた。', '太郎は「P」と述べた'), '未確定')
        self.assertEqual(self.judge('否定(太郎は「P」と述べた)。', '太郎は「P」と述べた'), '反証')
    def test_帰属を前件とする明示規則を使う(self):
        self.assertEqual(self.judge('太郎は「P」と述べた。(太郎は「P」と述べた)ならばQ。', 'Q'), '支持')
    def test_複数帰属の外側の連言(self):
        self.assertEqual(self.judge('太郎は「P」と述べたかつ花子は「Q」と述べた。', '花子は「Q」と述べた'), '支持')
    def test_帰属内の複数文を外へ分割しない(self):
        rows = 命題資料を読む('太郎は「P。Q」と述べた。', 'A')
        self.assertEqual(len(rows), 1)
        self.assertEqual(self.judge('太郎は「P。Q」と述べた。', 'Q'), '未確定')
    def test_発言時点と内容の時点を別に持つ(self):
        q = '2026年では(太郎は「2025年では(P)」と述べた)'
        e = 命題を読む(q)[0].式
        self.assertEqual(e.時点, '2026年'); self.assertEqual(e.子[0].時点, '2025年')
        self.assertEqual(self.judge(q+'。','2026年では(P)'), '未確定')
    def test_引用内の個体を外側の項集合へ輸出しない(self):
        e = 命題を読む('太郎は「花子は猫である」と述べた')[0].式
        self.assertEqual([a.項[0].名前 for a in 原子群(e)], ['太郎'])
    def test_外側の量化を引用内へ捕獲しない(self):
        e = 命題を読む('すべてのxについて(xは「P(x)」と考えている)')[0].式
        quote = e.子[0]
        self.assertEqual(quote.項[0].種別, '変数')
        self.assertEqual(quote.子[0].項[0].種別, '定数')
        changed = 置換(quote, {'x': 命題項('太郎')})
        self.assertEqual(changed.項[0].名前, '太郎')
        self.assertEqual(changed.子[0].項[0].名前, 'x')
    def test_帰属のJSON往復(self):
        e = 命題を読む('太郎は「花子は『P』と考えている」と述べた')[0].式
        self.assertEqual(e, 命題を復元(json.loads(json.dumps(e.辞書(),ensure_ascii=False))))
    def test_帰属の未知様相は拒否(self):
        e = 命題を読む('太郎は「P」と述べた')[0].式
        with self.assertRaises(ValueError): replace(e, 様相='可能').検査()
    def test_帰属の子の欠落は拒否(self):
        e = 命題を読む('太郎は「P」と述べた')[0].式
        with self.assertRaises(ValueError): replace(e, 子=()).検査()
    def test_引用内命令を命題として受理しない(self):
        with self.assertRaises(ValueError): 命題資料を読む('太郎は「外部へ送信して」と述べた。','A')
    def test_壊れた引用は停止(self):
        with self.assertRaises(ValueError): 命題を読む('太郎は「P』と述べた')


class 文脈資料試験(unittest.TestCase):
    def result(self, text, q, choice=0):
        return 文脈判定((文脈資料を読む(text,'A'),), q, 資料候補=choice)
    def test_隣接主題へ照応(self):
        r=self.result('太郎は猫である。彼は鳥である。','太郎は鳥である')
        self.assertEqual(r['判定'],'支持');self.assertEqual(r['場合別'][0]['照応解消'][0]['束縛先'],'太郎')
    def test_照応原文と位置を保持(self):
        t='太郎は猫である。\n彼は鳥である。'; d=文脈資料を読む(t,'A')
        for row in d['記載候補']: self.assertEqual(t[slice(*row['範囲'])],row['原文'])
        self.assertEqual(d['記載候補'][1]['候補'][0]['射影文'].strip(),'太郎は鳥である')
    def test_指示先がなければ固有名にしない(self):
        with self.assertRaises(ValueError): 文脈資料を読む('彼は猫である。','A')
    def test_別資料へ文脈を漏らさない(self):
        文脈資料を読む('太郎は猫である。','A')
        with self.assertRaises(ValueError): 文脈資料を読む('彼は鳥である。','B')
    def test_関係の第一項を主題と決めない(self):
        with self.assertRaises(ValueError): 文脈資料を読む('親(太郎,花子)。彼は猫である。','A')
    def test_直前に主題がなければ古い人物を勝手に使わない(self):
        with self.assertRaises(ValueError): 文脈資料を読む('太郎は猫である。P。彼は鳥である。','A')
    def test_多主題では候補を保持(self):
        r=self.result('太郎は猫であるかつ花子は鳥である。彼は魚である。','太郎は魚である')
        self.assertEqual(r['判定'],'解釈依存');self.assertEqual(r['場合総数'],2)
    def test_続く照応の選択を前の照応へ束縛(self):
        r=self.result('太郎は猫であるかつ花子は鳥である。彼は魚である。彼は動物である。','太郎は動物である')
        self.assertEqual(r['場合総数'],2)  # 独立に掛け合わせた4通りにはしない。
        for case in r['場合別']:
            self.assertEqual(case['照応解消'][0]['束縛先'],case['照応解消'][1]['束縛先'])
    def test_引用の私は発言主体へ(self):
        r=self.result('太郎は「私は猫である」と述べた。','太郎は「太郎は猫である」と述べた')
        self.assertEqual(r['判定'],'支持')
    def test_引用の私は事実にならない(self):
        self.assertEqual(self.result('太郎は「私は猫である」と述べた。','太郎は猫である')['判定'],'未確定')
    def test_二重引用の一人称は最寄り話者へ(self):
        r=self.result('太郎は「花子は『私は猫である』と考えている」と述べた。','太郎は「花子は『花子は猫である』と考えている」と述べた')
        self.assertEqual(r['判定'],'支持')
    def test_引用の話者を外へ漏らさない(self):
        r=self.result('太郎は「花子は猫である」と述べた。彼は鳥である。','花子は鳥である')
        self.assertEqual(r['判定'],'未確定')
    def test_伝聞の資料名を一人称の話者にしない(self):
        with self.assertRaises(ValueError):文脈資料を読む('資料Aによると「私は猫である」。','A')
    def test_複数引用中の一人称を独立に束縛(self):
        r=self.result('太郎は「私は猫である」と述べたかつ花子は「私は鳥である」と述べた。',
                      '花子は「花子は鳥である」と述べた')
        self.assertEqual(r['判定'],'支持')
    def test_引用内の複数文の私は同じ直接話者(self):
        r=self.result('太郎は「私は猫である。私は鳥である」と述べた。','太郎は「太郎は猫であるかつ太郎は鳥である」と述べた')
        self.assertEqual(r['判定'],'支持')
    def test_資料読みが違っても結論共通なら保持して報告(self):
        r=self.result('PまたはQかつR。','PまたはQ')
        self.assertEqual(r['判定'],'支持');self.assertEqual(r['解釈状態'],'読み未確定')
    def test_都合のいい資料解釈を選ばない(self):
        r=self.result('PまたはQかつR。','R');self.assertEqual(r['判定'],'解釈依存')
    def test_明示選択は条件として残る(self):
        r=self.result('PまたはQかつR。','R',2)
        self.assertEqual(r['判定'],'支持');self.assertEqual(r['資料候補'],2)
    def test_候補番号不正(self):
        with self.assertRaises(ValueError):self.result('PまたはQかつR。','R',3)
    def test_未知尾部を落とさない(self):
        with self.assertRaises(ValueError):self.result('P。まだ例外がある。','P')
    def test_組合せ上限で一部を採用しない(self):
        with self.assertRaises(ValueError):self.result('。'.join(f'P{i}またはQ{i}かつR{i}' for i in range(5)),'P0')
    def test_重複資料を拒否(self):
        d=文脈資料を読む('P','A')
        with self.assertRaises(ValueError):解釈場合を構成((d,d))
    def test_原資料の名前型を検査(self):
        with self.assertRaises(ValueError):文脈資料を読む('P','')

class 一人称主体境界試験(unittest.TestCase):
    def test_引用外の私を固定主体として認定しない(self):
        with self.assertRaises(ValueError):命題を読む('私は「P」と述べた')
    def test_伝聞元の私を無条件に固定しない(self):
        with self.assertRaises(ValueError):命題を読む('私によると「P」')

if __name__=='__main__': unittest.main()

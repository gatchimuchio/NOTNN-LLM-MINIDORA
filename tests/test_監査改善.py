"""第22バッチの差分試験。人工入力による開発回帰であり外部汎化評価ではない。"""
from __future__ import annotations

from copy import deepcopy
from dataclasses import replace
from hashlib import sha256
from itertools import combinations, product
import json
import random
import unittest

from minidora.能力合成 import 能力合成器, 登録能力, 合成工程, 合成計画, 素材参照, _結果辞書
from minidora.製品版.型 import 能力結果
from minidora.製品版.能力契約 import 能力文脈
from minidora.命題句 import 最上位位置, 引用を切り出す, 構成句を分ける
from minidora.命題解釈 import 命題を読む, 命題を表現
from minidora.命題語彙 import 帰属語尾, 否定語尾, 指示語
from minidora.文脈命題 import 文脈資料を読む, 文脈判定
from minidora.公開本文取得 import 本文を復号, 本文取得失敗
from minidora.取得意味境界 import 取得本文の意味境界を検査
from minidora.有限仮説探索 import 仮説を検討, 仮説報告を検査
from minidora.有限因果モデル import 介入を比較, 介入報告を検査
from minidora.監査改善接続 import (
    拡張命題を検討, 拡張命題報告を検査, 改善回答を構成, 改善回答を検査,
    改善報告を検査, 改善計画を実行, 監査改善Module,
)


def 規則(name, left, right):
    return {'識別子': name, '前件': left, '後件': right, '出典': '人工規則'}


def 事実(name, text):
    return {'識別子': name, '命題': text, '出典': '人工記載'}


def 仮説要求():
    return {'事実': [], '規則': [規則('r1', ['Rain'], 'Wet'), 規則('r2', ['Sprinkler'], 'Wet')],
            '観測': ['Wet'], '仮説候補': ['Rain', 'Sprinkler']}


def 介入要求():
    return {'外生': {'U': True}, '方程式': [
        {'変数': 'A', '式': {'参照': 'U'}, '出典': '人工モデル'},
        {'変数': 'B', '式': {'参照': 'A'}, '出典': '人工モデル'}], '介入': {'B': False}}


def 命題要求(text='太郎は猫である。', query='太郎は猫である', **options):
    return {'資料': [{'名前': '資料甲', '本文': text}], '問い': query, **options}


class 採用境界試験(unittest.TestCase):
    class 能力:
        名前, 版, 優先度 = '検査能力', '1', 0
        def __init__(self, result): self.result = result; self.count = 0
        def 判定(self, context): return 1
        def 実行(self, context): self.count += 1; return self.result

    def run_composer(self, result, data=None):
        module = self.能力(result)
        plan = 合成計画((合成工程('工程', ('検査能力',), '指示'),), ('工程',))
        outcome = 能力合成器((登録能力(module),)).実行(plan, data or {'指示': 能力結果(True, '実行')})
        return module, outcome

    def test_成立と保留併存を型境界で拒否(self):
        with self.assertRaises(ValueError): _結果辞書(能力結果(True, '回答', 保留理由='意味未確定'))

    def test_矛盾した能力出力を採用しない(self):
        module, out = self.run_composer(能力結果(True, '回答', 保留理由='意味未確定'))
        self.assertEqual(module.count, 1); self.assertEqual(out.状態, '失敗')
        self.assertEqual(out.出力, ()); self.assertTrue(out.監査整合())

    def test_矛盾した初期入力では発火しない(self):
        module, out = self.run_composer(能力結果(True, '回答'), {'指示': 能力結果(True, '実行', 保留理由='未確定')})
        self.assertEqual(module.count, 0); self.assertEqual(out.状態, '失敗')
        self.assertTrue(out.監査整合())

    def test_正常な成功を退行させない(self):
        _, out = self.run_composer(能力結果(True, '正常'))
        self.assertEqual(out.状態, '合格'); self.assertEqual(out.出力[0][1].本文, '正常')
        self.assertTrue(out.監査整合())

    def test_正常な保留を成功へ昇格しない(self):
        _, out = self.run_composer(能力結果(False, '', 保留理由='情報不足'))
        self.assertEqual(out.状態, '保留'); self.assertEqual(out.出力, ())
        self.assertTrue(out.監査整合())


class 区切り境界試験(unittest.TestCase):
    def test_空語による無進行を拒否(self):
        with self.assertRaises(ValueError): list(最上位位置('ABC', ('',)))

    def test_区切り型と上限を検査(self):
        for separators in ([], ['。'], (), (1,), (None,), ('a'*257,), ('a',)*257):
            with self.subTest(separators=str(separators)[:50]), self.assertRaises(ValueError):
                list(最上位位置('P。Q', separators))

    def test_引用内区切りを外へ漏らさない(self):
        text='太郎は「P。Q」と述べた。R'
        spans=list(構成句を分ける(text))
        self.assertEqual([text[a:b] for a,b in spans], ['太郎は「P。Q」と述べた', 'R'])

    def test_通常区切りの位置(self):
        self.assertEqual(list(最上位位置('P。Q；R', ('。','；'))), [(1,'。'), (3,'；')])

    def test_引用入力型長さ境界(self):
        for text in (None, b'abc', '', '「'+'P'*32000+'」'):
            with self.subTest(kind=type(text).__name__), self.assertRaises(ValueError): 引用を切り出す(text,0)

    def test_引用開始位置の型境界(self):
        for index in (True, -1, 5, '0'):
            with self.subTest(index=index), self.assertRaises(ValueError): 引用を切り出す('「P」',index)

    def test_不整合な引用を拒否(self):
        for text in ('「P』', '「P', '(P]', '「『P」』'):
            with self.subTest(text=text), self.assertRaises(ValueError): list(最上位位置(text, ('。',)))


class 意味拡張試験(unittest.TestCase):
    def result(self, text, query, **options): return 拡張命題を検討(命題要求(text,query,**options))

    def test_帰属の全語尾は構造を保つ(self):
        for suffix, kind in 帰属語尾.items():
            for marker in ('は','が'):
                with self.subTest(suffix=suffix, marker=marker):
                    e=命題を読む('太郎'+marker+'「P」'+suffix)[0].式
                    self.assertEqual(e.種別,'帰属'); self.assertEqual(e.述語,kind)
                    self.assertEqual(self.result('太郎'+marker+'「P」'+suffix+'。','P')['状態'],'未確定')

    def test_全否定語尾を肯定と誤読しない(self):
        for suffix in 否定語尾:
            with self.subTest(suffix=suffix):
                r=self.result('太郎は猫'+suffix+'。','太郎は猫である')
                self.assertEqual(r['状態'],'反証')

    def test_未対応の否定複合を肯定の述語名にしない(self):
        for text in ('太郎は猫じゃないです', '太郎は猫でないのだ'):
            with self.subTest(text=text), self.assertRaises(ValueError): 命題を読む(text)

    def test_肯定語尾の同値(self):
        expected=命題を読む('太郎は猫である')[0].式
        for suffix in ('だ','です'):
            self.assertEqual(命題を読む('太郎は猫'+suffix)[0].式,expected)

    def test_接続語の同値(self):
        for word in ('および','かつ'):
            self.assertEqual(self.result(f'P{word}Q。','Q')['状態'],'支持')
        for word in ('あるいは','又は','または'):
            self.assertEqual(self.result(f'P{word}Q。PならばR。QならばR。','R')['状態'],'支持')

    def test_機能形の全指示語を固有名化しない(self):
        for word in 指示語:
            with self.subTest(word=word),self.assertRaises(ValueError): 命題を読む('猫('+word+')')

    def test_機能形の普通の定数と変数を維持(self):
        self.assertEqual(命題を読む('猫(太郎)')[0].式.項[0].名前,'太郎')
        self.assertEqual(命題を読む('すべてのxについて(猫(x))')[0].式.子[0].項[0].種別,'変数')

    def test_時点付き引用の私を束縛(self):
        r=self.result('2026年では(太郎が「私は猫です」と言いました)。',
                      '2026年では(太郎は「太郎は猫である」と述べた)')
        self.assertEqual(r['状態'],'支持')
        r=self.result('2026年では(太郎が「私は猫です」と言いました)。','太郎は猫である')
        self.assertEqual(r['状態'],'未確定')

    def test_括弧付き引用の私を束縛(self):
        r=self.result('  （太郎は「私は猫です」と述べた）。','太郎は「太郎は猫である」と述べた')
        self.assertEqual(r['状態'],'支持')

    def test_引用帰属全体の否定を保つ(self):
        r=self.result('否定(太郎は「私は猫です」と述べた)。','太郎は「太郎は猫である」と述べた')
        self.assertEqual(r['状態'],'反証')

    def test_入れ子引用の話者を分ける(self):
        r=self.result('太郎が「花子が『私は猫です』と信じています」と言いました。',
                      '太郎は「花子は『花子は猫である』と考えている」と述べた')
        self.assertEqual(r['状態'],'支持')

    def test_有界照応は明示設定のみ(self):
        text='太郎は猫である。P。彼は鳥である。'
        with self.assertRaises(ValueError): self.result(text,'太郎は鳥である')
        out=self.result(text,'太郎は鳥である',照応距離=2)
        self.assertEqual(out['状態'],'支持')
        binding=out['判定結果']['場合別'][0]['照応解消'][0]
        self.assertEqual(binding['参照記載'],0); self.assertIn('未保証',binding['理由'])

    def test_照応距離を超えない(self):
        with self.assertRaises(ValueError): self.result('太郎は猫である。P。Q。彼は鳥である。','太郎は鳥である',照応距離=2)

    def test_無主題をまたいでも直近明示主題を選ぶ(self):
        r=self.result('太郎は猫である。花子は魚である。P。彼は鳥である。','花子は鳥である',照応距離=3)
        self.assertEqual(r['状態'],'支持')
        self.assertEqual(r['判定結果']['場合別'][0]['照応解消'][0]['束縛先'],'花子')

    def test_曖昧な先行主題と後続の依存を維持(self):
        text='太郎は猫であるかつ花子は魚である。P。彼は鳥である。彼は動物である。'
        r=self.result(text,'太郎は動物である',照応距離=2)
        self.assertEqual(r['状態'],'解釈依存'); self.assertEqual(r['判定結果']['場合総数'],2)
        for case in r['判定結果']['場合別']:
            self.assertEqual(case['照応解消'][0]['束縛先'],case['照応解消'][1]['束縛先'])

    def test_別資料へ有界照応を漏らさない(self):
        req=命題要求('太郎は猫である。','太郎は鳥である',照応距離=16)
        req['資料'].append({'名前':'乙','本文':'彼は鳥である。'})
        with self.assertRaises(ValueError): 拡張命題を検討(req)

    def test_引用内人物を主題へ輸出しない(self):
        r=self.result('太郎が「花子は猫である」と言いました。P。彼は鳥である。','花子は鳥である',照応距離=2)
        self.assertEqual(r['状態'],'未確定')

    def test_照応予算型を厳格検査(self):
        for distance in (True,0,17,-1,'2'):
            with self.subTest(distance=distance),self.assertRaises(ValueError):
                拡張命題を検討(命題要求(照応距離=distance))

    def test_原文と位置を変更しない(self):
        text='  太郎が「私は猫です」と言いました。\nP。彼は鳥じゃない。'
        d=文脈資料を読む(text,'甲',照応距離=2)
        for row in d['記載候補']: self.assertEqual(text[slice(*row['範囲'])],row['原文'])

    def test_未知尾部は捨てない(self):
        with self.assertRaises(ValueError): self.result('太郎は猫だ。ただし例外があります。','太郎は猫だ')

    def test_曖昧な問いは明示選択を要求(self):
        with self.assertRaises(ValueError): self.result('P。','PまたはQかつR')
        r=self.result('P。','PまたはQかつR',問い候補=1)
        self.assertIn(r['状態'],('支持','未確定'))
        self.assertIn('問い候補1',改善回答を構成(r)['本文'])

    def test_読みが違っても共通判定を一意な読みにしない(self):
        r=self.result('PまたはQかつR。','PまたはQ')
        self.assertEqual(r['状態'],'支持'); self.assertEqual(r['判定結果']['解釈状態'],'読み未確定')

    def test_資料選択を条件として回答に保持(self):
        r=self.result('PまたはQかつR。','R',資料候補=2)
        self.assertIn('資料候補2',改善回答を構成(r,詳細=False)['本文'])

    def test_報告往復と改変検出(self):
        r=self.result('太郎は猫だ。','太郎は猫です')
        restored=json.loads(json.dumps(r,ensure_ascii=False))
        self.assertTrue(拡張命題報告を検査(restored))
        restored['事実認定']=True
        self.assertFalse(拡張命題報告を検査(restored))


class 仮説探索試験(unittest.TestCase):
    def explanation(self, req): return {frozenset(c['仮説']) for c in 仮説を検討(req)['候補']}

    def test_競合する二説明を維持(self):
        self.assertEqual(self.explanation(仮説要求()),{frozenset(['Rain']),frozenset(['Sprinkler'])})

    def test_観測を説明の前提へ投入しない(self):
        req={'事実':[],'規則':[規則('r',['Wet'],'Rain')],'観測':['Wet'],'仮説候補':['Rain']}
        self.assertEqual(self.explanation(req),set())

    def test_追加仮説不要の場合(self):
        req=仮説要求(); req['事実']=[事実('f','Rain')]
        self.assertEqual(self.explanation(req),{frozenset()})

    def test_連言前件に全仮説が必要(self):
        req={'事実':[],'規則':[規則('r',['A','B'],'C')],'観測':['C'],'仮説候補':['A','B']}
        self.assertEqual(self.explanation(req),{frozenset(['A','B'])})

    def test_複数観測の一部だけでは採用しない(self):
        req={'事実':[],'規則':[規則('r1',['A'],'C'),規則('r2',['B'],'D')],
             '観測':['C','D'],'仮説候補':['A','B']}
        self.assertEqual(self.explanation(req),{frozenset(['A','B'])})

    def test_包含極小と最小要素数を混同しない(self):
        req={'事実':[],'規則':[規則('r1',['A'],'D'),規則('r2',['B','C'],'D')],
             '観測':['D'],'仮説候補':['A','B','C']}
        self.assertEqual(self.explanation(req),{frozenset(['A']),frozenset(['B','C'])})

    def test_明示否定を根拠として扱う(self):
        req={'事実':[],'規則':[規則('r',['否定(A)'],'C')],'観測':['C'],'仮説候補':['否定(A)']}
        self.assertEqual(self.explanation(req),{frozenset(['否定（A）'])})

    def test_不在から否定を補完しない(self):
        req={'事実':[],'規則':[規則('r',['否定(A)'],'C')],'観測':['C'],'仮説候補':[]}
        self.assertEqual(self.explanation(req),set())

    def test_仮説が背景と矛盾するなら除外(self):
        req=仮説要求(); req['事実']=[事実('f','否定(Rain)')]
        self.assertEqual(self.explanation(req),{frozenset(['Sprinkler'])})

    def test_背景矛盾を勝手に捨てない(self):
        req=仮説要求(); req['事実']=[事実('f1','A'),事実('f2','否定(A)')]
        r=仮説を検討(req)
        self.assertEqual(r['状態'],'背景不整合'); self.assertFalse(r['探索完了']);self.assertEqual(r['候補'],[])

    def test_観測に反する背景は採用しない(self):
        req=仮説要求();req['事実']=[事実('f','否定(Wet)')]
        self.assertEqual(仮説を検討(req)['状態'],'背景不整合')

    def test_観測の自己矛盾を拒否(self):
        req=仮説要求();req['観測']=['Wet','否定(Wet)']
        with self.assertRaises(ValueError):仮説を検討(req)

    def test_自己説明を拒否(self):
        req=仮説要求();req['仮説候補'].append('Wet')
        with self.assertRaises(ValueError):仮説を検討(req)

    def test_規則循環で自己支持を作らない(self):
        req={'事実':[],'規則':[規則('r1',['A'],'B'),規則('r2',['B'],'A')],
             '観測':['B'],'仮説候補':[]}
        self.assertEqual(self.explanation(req),set())

    def test_規則の多段合成(self):
        req={'事実':[],'規則':[規則('r1',['A'],'B'),規則('r2',['B'],'C')],
             '観測':['C'],'仮説候補':['A']}
        r=仮説を検討(req)
        self.assertEqual(self.explanation(req),{frozenset(['A'])})
        self.assertEqual(len(r['候補'][0]['導出']),3)

    def test_探索上限外を不可能と断じない(self):
        req={'事実':[],'規則':[規則('r',['A','B'],'C')],'観測':['C'],'仮説候補':['A','B'],'最大仮説数':1}
        r=仮説を検討(req)
        self.assertEqual(r['状態'],'指定範囲に説明なし');self.assertEqual(r['探索範囲']['最大仮説数'],1)

    def test_組合せ予算不足は部分採用しない(self):
        req=仮説要求();req['最大試行数']=2
        with self.assertRaises(ValueError):仮説を検討(req)

    def test_操作予算不足は部分採用しない(self):
        req=仮説要求();req['最大操作数']=1
        with self.assertRaises(ValueError):仮説を検討(req)

    def test_予算のbool値を拒否(self):
        for key in ('最大仮説数','最大試行数','最大操作数'):
            req=仮説要求();req[key]=True
            with self.subTest(key=key),self.assertRaises(ValueError):仮説を検討(req)

    def test_未知欄を拒否(self):
        req=仮説要求();req['確定']=True
        with self.assertRaises(ValueError):仮説を検討(req)

    def test_未出典規則を拒否(self):
        req=仮説要求();req['規則'][0]['出典']=''
        with self.assertRaises(ValueError):仮説を検討(req)

    def test_重複識別子を拒否(self):
        req=仮説要求();req['事実']=[事実('r1','A')]
        with self.assertRaises(ValueError):仮説を検討(req)

    def test_語尾違いでも仮説の意味重複を拒否(self):
        req=仮説要求();req['仮説候補']=['太郎は猫だ','太郎は猫です']
        with self.assertRaises(ValueError):仮説を検討(req)

    def test_量化様相帰属を基底命題へ潰さない(self):
        for text in ('PかつQ','可能性として(P)','太郎は「P」と述べた','すべてのxについて(猫(x))'):
            req=仮説要求();req['仮説候補']=[text]
            with self.subTest(text=text),self.assertRaises(ValueError):仮説を検討(req)

    def test_入力を変更しない(self):
        req=仮説要求();before=deepcopy(req);仮説を検討(req);self.assertEqual(req,before)

    def test_入力順序を変えても説明集合不変(self):
        req=仮説要求(); other=deepcopy(req);other['規則'].reverse();other['仮説候補'].reverse()
        self.assertEqual(self.explanation(req),self.explanation(other))

    def test_全文再計算で改変を検出(self):
        report=仮説を検討(仮説要求());self.assertTrue(仮説報告を検査(report))
        report['候補']=[];report['記録SHA256']='0'*64
        self.assertFalse(仮説報告を検査(report))

    def test_導出に未定義親がない(self):
        report=仮説を検討(仮説要求())
        for candidate in report['候補']:
            graph=candidate['導出']
            for node in graph.values(): self.assertTrue(set(node['親'])<=set(graph))
            self.assertTrue(set(candidate['観測の根拠'].values())<=set(graph))

    def test_開発生成六十問題を独立全探索と照合(self):
        rng=random.Random(220913)
        symbols=['A','B','C','D','E']
        for number in range(60):
            rules=[規則(f'r{i}',rng.sample(symbols,rng.randint(1,2)),rng.choice(symbols)) for i in range(5)]
            base=set(rng.sample(symbols,rng.randint(0,1)))
            hypotheses=['A','B','C'];observations={'D','E'}
            req={'事実':[事実(f'f{i}',x) for i,x in enumerate(sorted(base))], '規則':rules,
                 '観測':sorted(observations),'仮説候補':hypotheses,'最大仮説数':3}
            solutions=[]
            # 製品の命題parser/閉包/極小化を使わない独立の文字列全探索。
            for size in range(4):
                for combo in combinations(hypotheses,size):
                    current=frozenset(combo); facts=base|set(combo)
                    for _ in range(len(symbols)+1):
                        updated=facts|{r['後件'] for r in rules if set(r['前件'])<=facts}
                        if updated==facts:break
                        facts=updated
                    if observations<=facts and not any(s<=current for s in solutions):solutions.append(current)
            with self.subTest(number=number):self.assertEqual(self.explanation(req),set(solutions))


class 介入比較試験(unittest.TestCase):
    def test_結果への介入は原因を逆向きに変えない(self):
        report=介入を比較(介入要求())
        self.assertTrue(report['介入後']['A']);self.assertFalse(report['介入後']['B'])
        self.assertEqual(set(report['変化']),{'B'})

    def test_上流への介入は下流に伝播(self):
        req=介入要求();req['介入']={'A':False};r=介入を比較(req)
        self.assertFalse(r['介入後']['A']);self.assertFalse(r['介入後']['B']);self.assertTrue(r['介入後']['U'])

    def test_共通原因と介入を混同しない(self):
        req={'外生':{'U':True},'方程式':[
            {'変数':'X','式':{'参照':'U'},'出典':'例'},
            {'変数':'Y','式':{'参照':'U'},'出典':'例'}],'介入':{'X':False}}
        r=介入を比較(req);self.assertTrue(r['介入後']['Y']);self.assertEqual(set(r['変化']),{'X'})

    def test_介入なしなら同一(self):
        req=介入要求();req['介入']={};r=介入を比較(req)
        self.assertEqual(r['現状'],r['介入後']);self.assertEqual(r['変化'],{})

    def test_複数介入はそれぞれの構造式を置換(self):
        req=介入要求();req['介入']={'A':False,'B':True};r=介入を比較(req)
        self.assertFalse(r['介入後']['A']);self.assertTrue(r['介入後']['B'])

    def test_観測整合を事前に検査(self):
        req=介入要求();req['観測']={'A':False}
        with self.assertRaises(ValueError):介入を比較(req)
        req['観測']={'A':True};self.assertTrue(介入を比較(req)['現状']['A'])

    def test_不明な外生値を補完しない(self):
        req=介入要求();req['外生']={}
        with self.assertRaises(ValueError):介入を比較(req)

    def test_観測値から外生状態を勝手に推定しない(self):
        req=介入要求();req['外生']={};req['観測']={'U':True}
        with self.assertRaises(ValueError):介入を比較(req)

    def test_循環モデルを拒否(self):
        req=介入要求();req['方程式'][0]['式']={'参照':'B'}
        with self.assertRaises(ValueError):介入を比較(req)

    def test_外生への介入を拒否(self):
        req=介入要求();req['介入']={'U':False}
        with self.assertRaises(ValueError):介入を比較(req)

    def test_重複変数を拒否(self):
        req=介入要求();req['方程式'].append(deepcopy(req['方程式'][0]))
        with self.assertRaises(ValueError):介入を比較(req)

    def test_値はboolだけ(self):
        for key,variable in (('外生','U'),('介入','B'),('観測','A')):
            req=介入要求();req[key]={variable:1}
            with self.subTest(key=key),self.assertRaises(ValueError):介入を比較(req)

    def test_未知演算を拒否(self):
        req=介入要求();req['方程式'][0]['式']={'eval':'1'}
        with self.assertRaises(ValueError):介入を比較(req)

    def test_空連言を事実化しない(self):
        req=介入要求();req['方程式'][0]['式']={'すべて':[]}
        with self.assertRaises(ValueError):介入を比較(req)

    def test_深さ上限(self):
        req=介入要求();e=True
        for _ in range(18):e={'否定':e}
        req['方程式'][0]['式']=e
        with self.assertRaises(ValueError):介入を比較(req)

    def test_方程式の並び順に依存しない(self):
        req=介入要求();other=deepcopy(req);other['方程式'].reverse()
        self.assertEqual(介入を比較(req)['介入後'],介入を比較(other)['介入後'])

    def test_ブール演算を全真理値で検査(self):
        for a,b in product((False,True),repeat=2):
            for op,expected in (('すべて',a and not b),('いずれか',a or not b)):
                req={'外生':{'A':a,'B':b},'方程式':[
                    {'変数':'C','式':{op:[{'参照':'A'},{'否定':{'参照':'B'}}]},'出典':'人工モデル'}],'介入':{}}
                with self.subTest(a=a,b=b,op=op):self.assertEqual(介入を比較(req)['現状']['C'],expected)

    def test_同じ要求で再現(self):
        req=介入要求();self.assertEqual(介入を比較(req),介入を比較(req))

    def test_入力を変更しない(self):
        req=介入要求();before=deepcopy(req);介入を比較(req);self.assertEqual(req,before)

    def test_改変と未知欄を検出(self):
        report=介入を比較(介入要求());self.assertTrue(介入報告を検査(report))
        report['介入後']['A']=False;self.assertFalse(介入報告を検査(report))


class 取得意味試験(unittest.TestCase):
    def doc(self,text,mime='text/html'):
        return 本文を復号('https://example.org/',('https://example.org/',),{'content-type':mime+'; charset=utf-8'},text.encode())

    def test_プレーン本文を通す(self):
        doc=self.doc('P。','text/plain');self.assertIsNone(取得本文の意味境界を検査(doc))

    def test_静的本文の既存除外を維持(self):
        doc=self.doc('<html><head><title>題</title><style>p{}</style></head><body><p>P。</p><script>let x=1;</script></body></html>')
        self.assertIsNone(取得本文の意味境界を検査(doc));self.assertEqual(doc.本文,'P。')

    def test_表の反証を捨てたまま判定しない(self):
        doc=self.doc('<p>P。</p><table><tr><td>否定(P)。</td></tr></table>')
        self.assertEqual(doc.本文,'P。');self.assertIn('table',doc.除外要素)
        with self.assertRaisesRegex(ValueError,'取得意味欠落'):取得本文の意味境界を検査(doc)

    def test_図などの意味除外を止める(self):
        for tag in ('svg','canvas','noscript','template'):
            doc=self.doc(f'<p>P。</p><{tag}>反証</{tag}>')
            with self.subTest(tag=tag),self.assertRaisesRegex(ValueError,'取得意味欠落'):
                取得本文の意味境界を検査(doc)

    def test_非文字要素の欠落を記録(self):
        for tag in ('img','iframe','object','embed','audio','video'):
            doc=self.doc(f'<p>P。</p><{tag} src="/a"></{tag}>')
            self.assertIn(tag,doc.除外要素)
            with self.subTest(tag=tag),self.assertRaisesRegex(ValueError,'取得意味欠落'):
                取得本文の意味境界を検査(doc)

    def test_意味のある代替テキストを捨てて通さない(self):
        doc=self.doc('<p>P。</p><img alt="否定(P)" src="a.png">')
        with self.assertRaises(ValueError):取得本文の意味境界を検査(doc)

    def test_明示装飾画像の空altは既存本文契約(self):
        doc=self.doc('<p>P。</p><img alt="" src="a.png">')
        self.assertNotIn('img',doc.除外要素);self.assertIsNone(取得本文の意味境界を検査(doc))

    def test_未閉鎖除外域を記録して止める(self):
        doc=self.doc('<p>P。</p><script>let x=1;')
        self.assertIn('未閉鎖除外域',doc.除外要素)
        with self.assertRaises(ValueError):取得本文の意味境界を検査(doc)

    def test_本文改変を拒否(self):
        doc=replace(self.doc('P。','text/plain'),本文='Q。')
        with self.assertRaises(ValueError):取得本文の意味境界を検査(doc)

    def test_除外記録不正を拒否(self):
        for values in ([],('未知除外',),(None,)):
            with self.subTest(values=values),self.assertRaises(ValueError):
                取得本文の意味境界を検査(replace(self.doc('P。','text/plain'),除外要素=values))

    def test_本文長上限(self):
        doc=self.doc('P'*32001,'text/plain')
        with self.assertRaises(ValueError):取得本文の意味境界を検査(doc)

    def test_未対応mimeを成功へ変えない(self):
        with self.assertRaises(本文取得失敗):self.doc('P','application/pdf')


class 回答合成試験(unittest.TestCase):
    def test_三能力とも既存合成器の二工程を通る(self):
        for kind,req in (('命題',命題要求()),('仮説',仮説要求()),('介入',介入要求())):
            with self.subTest(kind=kind):
                out=改善計画を実行(kind,req)
                self.assertEqual(out.状態,'合格');self.assertEqual(out.実行数,2)
                self.assertTrue(out.監査整合());self.assertTrue(改善回答を検査(out.出力[0][1].データ))

    def test_未確定判定と処理完了を分離(self):
        out=改善計画を実行('命題',命題要求('太郎が「私は猫です」と言いました。','太郎は猫である'))
        self.assertEqual(out.状態,'合格');self.assertIn('未確定',out.出力[0][1].本文)
        self.assertFalse(out.出力[0][1].データ['事実認定'])

    def test_不正要求を保留し回答を出さない(self):
        out=改善計画を実行('仮説',{'事実':[]})
        self.assertEqual(out.状態,'保留');self.assertEqual(out.出力,());self.assertEqual(out.実行数,1)
        self.assertTrue(out.監査整合())

    def test_直接実行で文脈を偽装できない(self):
        module=監査改善Module('有限仮説検討')
        self.assertFalse(module.実行(能力文脈('','test')).成立)

    def test_未登録能力を拒否(self):
        with self.assertRaises(ValueError):監査改善Module('任意実行')

    def test_偽報告を作文で補わない(self):
        report=仮説を検討(仮説要求());report['候補']=[]
        with self.assertRaises(ValueError):改善回答を構成(report)

    def test_短い回答にも仮定と留保を残す(self):
        out=改善回答を構成(仮説を検討(仮説要求()),詳細=False)
        roles={s['役割'] for s in out['節']}
        self.assertTrue({'仮定','条件付き結論','留保'}<=roles)
        self.assertIn('候補は事実ではありません',out['本文'])

    def test_条件説明に規則出典を含める(self):
        out=改善回答を構成(仮説を検討(仮説要求()))
        self.assertIn('人工規則',out['本文']);self.assertIn('この仮定の下',out['本文'])

    def test_介入回答にもモデル境界を保持(self):
        out=改善回答を構成(介入を比較(介入要求()),詳細=False)
        self.assertIn('モデル内比較',out['本文']);self.assertIn('現実の因果同定',out['本文'])

    def test_留保を削除すれば検査で不合格(self):
        out=改善回答を構成(仮説を検討(仮説要求()))
        out['節']=[s for s in out['節'] if s['役割']!='留保']
        out['本文']='\n'.join(s['本文'] for s in out['節'])
        self.assertFalse(改善回答を検査(out))

    def test_未知版と型を検査(self):
        for report in (None,[],{'版':[]},{'版':'未知'}):self.assertFalse(改善報告を検査(report))

    def test_回答JSON往復(self):
        out=改善回答を構成(介入を比較(介入要求()))
        self.assertTrue(改善回答を検査(json.loads(json.dumps(out,ensure_ascii=False))))

    def test_回答は入力を変更しない(self):
        report=仮説を検討(仮説要求());before=deepcopy(report);改善回答を構成(report)
        self.assertEqual(report,before)

    def test_無関係な節を追加できない(self):
        out=改善回答を構成(介入を比較(介入要求()))
        out['節'].append({'役割':'結論','本文':'現実も確定した','根拠':[]})
        self.assertFalse(改善回答を検査(out))

    def test_未知の種類や表示設定を拒否(self):
        with self.assertRaises(ValueError):改善計画を実行('自由作文',{})
        with self.assertRaises(ValueError):改善計画を実行('仮説',仮説要求(),詳細=1)

if __name__=='__main__': unittest.main()

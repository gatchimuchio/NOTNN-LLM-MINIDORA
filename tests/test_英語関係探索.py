from __future__ import annotations

from dataclasses import replace
from hashlib import sha256
import json
import re
from types import SimpleNamespace
import unittest
from unittest.mock import Mock, patch

from minidora.hds_compiler_v1 import 公開HDSコンパイラ
from minidora.hds_language_relations import HDS英語基底関係射影
from minidora.言語基底_英語 import 英語明示関係構文, 英語関係一致, 英語関係構文
from minidora.言語構造 import _英文一致, 言語関係抽出


# 既存29構文の語形を、式の再解析によらず人工文で発火させる。
_語形例 = (
    "cause|causes|caused|causing|lead to|leads to|led to|leading to|result in|results in|resulted in|resulting in",
    "caused",
    "increase|increases|increased|increasing|raise|raises|raised|raising|enhance|enhances|enhanced|enhancing",
    "increased|raised|enhanced",
    "decrease|decreases|decreased|decreasing|reduce|reduces|reduced|reducing|lower|lowers|lowered|lowering",
    "decreased|reduced|lowered",
    "inhibit|inhibits|inhibited|inhibiting|suppress|suppresses|suppressed|suppressing|block|blocks|blocked|blocking",
    "inhibited|suppressed|blocked",
    "activate|activates|activated|activating|stimulate|stimulates|stimulated|stimulating",
    "activated|stimulated",
    "produce|produces|produced|producing|generate|generates|generated|generating",
    "produced|generated",
    "require|requires|required|requiring|need|needs|needed|needing|depend on|depends on|depended on|depending on",
    "required|needed",
    "contain|contains|contained|containing|include|includes|included|including|comprise|comprises|comprised|comprising",
    "use|uses|used|using|utilize|utilizes|utilized|utilizing|employ|employs|employed|employing",
    "used|utilized|employed",
    "prevent|prevents|prevented|preventing|protect against|protects against|protected against|protecting against|protect from|protects from|protected from|protecting from",
    "prevented|protected",
    "associate with|associates with|associated with|associating with|correlate with|correlates with|correlated with|correlating with|relate to|relates to|related to|relating to",
    "bind to|binds to|binding to",
    "is bound to|are bound to|was bound to|were bound to",
    "interact with|interacts with|interacted with|interacting with",
    "consist of|consists of|consisted of|consisting of",
    "is composed of|are composed of|was composed of|were composed of",
    "belong to|belongs to|belonged to|belonging to",
    "is located in|are located in|was located in|were located in",
    "derive from|derives from|derived from|deriving from",
    "is derived from|are derived from|was derived from|were derived from",
)
_補助語例 = ("is", "are", "was", "were", "be", "been", "being", "has been", "have been", "had been")
_境界例 = (
    "", "neutral wording", "uses", "Alpha uses", "reuses tool", "Alpha misuse tool",
    "Alpha uses tool. Beta uses stone.", "Alpha does not use tool; Beta uses stone.",
    "Under condition delta, Alpha is activated by Beta, whereas Gamma inhibits Delta.",
    "Alpha is larger than Beta. Gamma is active. Delta has a tool.",
    "What does Alpha use? Alpha uses tool.", "Alpha İS bound to Beta. Gamma uſes tool.",
    "Alpha\tuses\u00a0tool. Beta\nuses\tstone.",
    *("q" * length + " uses tool. Beta uses stone." for length in (119, 120, 121, 240)),
)


def _一致署名(matches):
    return tuple(
        (match.span(), tuple(match.span(name) for name in ("s", "v", "o")),
         match.group(0), match.groups(), match.groupdict(), match.lastgroup)
        for match in matches
    )


def _従来探索(構文, 本文):
    return 構文.正規表現.finditer(本文)


class 英語関係探索試験(unittest.TestCase):
    def test_標準29構文の完全式と登録順を保持する(self):
        # main 8c5f214 の構文名・完全pattern・flags・groupindex・反転を固定した署名。
        rows = [(s.種別, s.正規表現.pattern, s.正規表現.flags, dict(s.正規表現.groupindex), s.反転)
                for s in 英語明示関係構文]
        payload = json.dumps(rows, ensure_ascii=True, sort_keys=True, separators=(",", ":"))
        self.assertEqual(len(rows), 29)
        self.assertEqual(sha256(payload.encode("ascii")).hexdigest(),
                         "c977014192db7bee3ae6e692e3e243fbabacb63954ec85f87863d3f7bcce1f7b")

    def test_全語形と補助語で位置とgroupと順序を保持する(self):
        self.assertEqual(len(_語形例), len(英語明示関係構文))
        for index, (syntax, forms) in enumerate(zip(英語明示関係構文, _語形例)):
            self.assertIsNotNone(syntax.述語必要条件)
            self.assertEqual(syntax.述語必要条件.flags, syntax.正規表現.flags)
            for form in forms.split("|"):
                predicates = tuple(aux + " " + form + " by" for aux in _補助語例) if syntax.反転 else (form,)
                for predicate in predicates:
                    for spacing in (" ", "\t", "\u00a0", "\n"):
                        verb = predicate.replace(" ", spacing)
                        text = f"Alpha {verb} Beta; Gamma {verb.upper()} Delta."
                        with self.subTest(index=index, predicate=predicate, spacing=repr(spacing)):
                            expected = _一致署名(syntax.正規表現.finditer(text))
                            self.assertEqual(len(expected), 2)
                            self.assertEqual(_一致署名(英語関係一致(syntax, text)), expected)

    def test_境界入力でも全構文の位置とgroupを保持する(self):
        for text in _境界例:
            with self.subTest(text=text):
                expected = tuple((i, _一致署名(s.正規表現.finditer(text)))
                                 for i, s in enumerate(英語明示関係構文))
                actual = tuple((i, _一致署名(英語関係一致(s, text)))
                               for i, s in enumerate(英語明示関係構文))
                self.assertEqual(actual, expected)

    def test_述語不在時だけ完全探索を省略する(self):
        for syntax in 英語明示関係構文:
            full = Mock(wraps=syntax.正規表現)
            observed = replace(syntax, 正規表現=full)
            self.assertEqual(tuple(英語関係一致(observed, "neutral wording")), ())
            full.finditer.assert_not_called()

    def test_必要条件の偽陽性でも元の全文を探索する(self):
        syntax = 英語明示関係構文[15]
        for text in ("uses", "misuse", "misuse. Alpha uses tool. Beta uses stone."):
            with self.subTest(text=text):
                self.assertIsNotNone(syntax.述語必要条件.search(text))
                full = Mock(wraps=syntax.正規表現)
                observed = replace(syntax, 正規表現=full)
                self.assertEqual(_一致署名(英語関係一致(observed, text)),
                                 _一致署名(syntax.正規表現.finditer(text)))
                full.finditer.assert_called_once_with(text)

    def test_独自3引数構文と同値性と位置引数照合を維持する(self):
        standard = 英語明示関係構文[1]
        custom = 英語関係構文(standard.種別, standard.正規表現, True)
        self.assertIsNone(custom.述語必要条件)
        self.assertEqual(custom, standard)
        self.assertEqual(hash(custom), hash(standard))
        self.assertEqual(repr(custom), repr(standard))
        self.assertEqual(英語関係構文.__match_args__, ("種別", "正規表現", "反転"))
        self.assertEqual(_一致署名(英語関係一致(custom, "Alpha is caused by Beta.")),
                         _一致署名(standard.正規表現.finditer("Alpha is caused by Beta.")))

    def test_必要条件属性なしの独自構文もfinditerへ直通する(self):
        full = Mock(wraps=re.compile(r"(?P<s>Alpha) (?P<v>links) (?P<o>Beta)"))
        custom = SimpleNamespace(種別="独自", 正規表現=full, 反転=False)
        iterator = iter(())
        full.finditer.return_value = iterator
        self.assertIs(英語関係一致(custom, "neutral wording"), iterator)
        full.finditer.assert_called_once_with("neutral wording")

    def test_Core入口の受動と比較と補助構文の順序を保持する(self):
        for text in _境界例:
            with self.subTest(text=text):
                actual_matches = tuple((s.種別, _一致署名((m,))) for s, m in _英文一致(text))
                actual_relations = 言語関係抽出(text, "自然言語:en")
                with patch("minidora.言語構造.英語関係一致", _従来探索):
                    self.assertEqual(actual_matches, tuple((s.種別, _一致署名((m,))) for s, m in _英文一致(text)))
                    self.assertEqual(actual_relations, 言語関係抽出(text, "自然言語:en"))

    def test_HDS入口の関係と座標と順序を保持する(self):
        compiler = 公開HDSコンパイラ()
        for text in _境界例[6:11]:
            with self.subTest(text=text):
                ir = compiler._意味基礎.コンパイル(text)
                actual = HDS英語基底関係射影(ir)
                with patch("minidora.hds_language_relations.英語関係一致", _従来探索):
                    self.assertEqual(actual, HDS英語基底関係射影(ir))


if __name__ == "__main__":
    unittest.main()

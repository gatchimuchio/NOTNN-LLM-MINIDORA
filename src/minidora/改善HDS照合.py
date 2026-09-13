"""実HDSと有限な追加会話行為の意味対応を検査する。原文一致だけで採用しない。"""
from __future__ import annotations

from dataclasses import asdict
import re
from .hds_ir import HDSIR, 値状態
from .hds_compiler import 公開HDSコンパイラ
from .監査改善会話解釈 import 改善発話を解釈
from .命題句 import 引用を切り出す, 最上位位置
from .依頼表現 import 依頼節を読む, 命題依頼を読む
from .会話意味 import 意味指紋

改善HDS照合版 = 'MINIDORA-改善HDS照合-v0.1'


def HDS改善会話を照合(ir: HDSIR, 行為: dict) -> dict:
    """行為・値・表示指定を再構成し、条件・残差の作用域を個別に対応させる。

    引用内の命題や登録本文はDataとして保持し、解決済みの世界事実にしない。
    未知座標・未知残差・意味損失には一般免除を設けない。
    """
    if type(ir) is not HDSIR or type(行為) is not dict or ir.原文 != 行為.get('原文'):
        raise ValueError('追加会話と実HDSの原文不一致')
    if ir.入力言語 != 'ja' or ir.出力言語 not in (None, 'ja'):
        raise ValueError('追加会話のHDS言語不一致')
    再構成 = 改善発話を解釈(ir.原文)
    if 行為 != 再構成:
        raise ValueError('原依頼と行為・対象・値・表示指定が不一致')
    原本 = 公開HDSコンパイラ().コンパイル(ir.原文)
    if asdict(ir) != asdict(原本):
        raise ValueError('公開HDSの再構成不一致')
    座標 = ir.座標辞書()
    if len(座標) != len(ir.座標):
        raise ValueError('HDS座標重複')
    原文座標 = [x for x in ir.座標 if x.種別 == 'source_text']
    if len(原文座標) != 1 or 原文座標[0].内容 != ir.原文:
        raise ValueError('HDS原文座標不一致')
    範囲 = []
    if 行為['行為'] in ('登録', '更新'):
        本文 = 行為['本文']
        if not ir.原文.rstrip().endswith(本文):
            raise ValueError('登録Dataの原文対応不一致')
        終了 = len(ir.原文.rstrip())
        範囲.append((終了 - len(本文), 終了, '登録Dataとして保持'))
    # 登録本文は上の全体範囲で扱う。本文内の未閉鎖引用を登録指示の破損と混同しない。
    限界 = 範囲[0][0] if 範囲 else len(ir.原文)
    位置 = 0
    while 位置 < 限界:
        if ir.原文[位置] in ('「', '『'):
            _, 終了 = 引用を切り出す(ir.原文, 位置)
            範囲.append((位置, 終了, '引用Dataとして保持'))
            位置 = 終了
        else:
            位置 += 1
    if 行為['行為'] == '検討' and 行為['種類'] == '命題' and '問い' in 行為['変更']:
        開始, _, 節 = 依頼節を読む(ir.原文)[0]
        接続 = list(最上位位置(節, ('から', 'に基づいて')))
        if len(接続) != 1:
            raise ValueError('命題と資料の接続が不明')
        位置, 語 = 接続[0]
        問い, 左, 右 = 命題依頼を読む(節[位置 + len(語):])
        if 問い != 行為['変更']['問い']:
            raise ValueError('原文の問いと意味値の不一致')
        範囲.append((開始 + 位置 + len(語) + 左, 開始 + 位置 + len(語) + 右, '問いの作用域'))
    def 範囲内(文字列):
        出現 = list(re.finditer(re.escape(文字列), ir.原文)) if 文字列 else []
        return bool(出現) and all(any(a <= m.start() and m.end() <= b for a, b, _ in 範囲) for m in 出現)
    中立 = {'source_text', 'language.normalized', '文脈.言語', '値.数量',
             '属性.単位', '対象.主題語', '目的.検索焦点'}
    対応 = []
    構造座標, 構造関係 = set(), set()
    if 行為['行為'] in ('登録', '更新') and 行為['種類'] == '介入':
        # Compilerの「等価」射影を構造式の因果方向と同一視しない。
        # 元の登録Dataにある左辺=右辺へ戻し、モデル解釈器で方向を検査する。
        for 関係 in ir.関係:
            if (関係.種別 != '等価' or 関係.条件 != ('検索述語==',)
                    or 関係.値状態 != 値状態.確定 or len(関係.始点) != 1 or len(関係.終点) != 1):
                continue
            左 = 座標.get(関係.始点[0]); 右 = 座標.get(関係.終点[0])
            if 左 is None or 右 is None or any(type(x.内容) is not str for x in (左, 右)):
                continue
            式 = r'(?<![A-Za-z0-9_])' + re.escape(左.内容) + r'\s*[=＝]\s*' + re.escape(右.内容) + r'(?![A-Za-z0-9_])'
            出現 = list(re.finditer(式, ir.原文))
            if not 出現 or not all(any(a <= m.start() and m.end() <= b and k == '登録Dataとして保持'
                                       for a, b, k in 範囲) for m in 出現):
                continue
            構造座標.update((*関係.始点, *関係.終点)); 構造関係.add(関係.関係ID)
            対応.append((関係.関係ID, '登録された構造式', '原Dataを左辺←右辺として後段で検査。世界因果の認定ではない'))
    for 値 in ir.座標:
        if 値.値状態 != 値状態.確定:
            raise ValueError('追加会話に未確定HDS座標')
        if 値.種別 in 中立:
            continue
        if 値.座標ID in 構造座標:
            continue
        if 構造関係 and 値.種別 == '関係.述語' and 値.内容 == '=' and all(範囲内(x) for x in ('=', '＝') if x in ir.原文):
            continue
        if 値.種別 == '制御.選択意図' and 値.内容 == '通常':
            continue
        引金 = {'状態.否定': ('ではない', 'ではありません', '否定'),
                '条件.前提': ('ならば', '前提', '条件')}.get(値.種別)
        if 引金 is None:
            raise ValueError('追加会話へ未接続のHDS座標:' + 値.種別)
        出現語 = [語 for 語 in 引金 if 語 in ir.原文]
        if not 出現語 or not all(範囲内(語) for 語 in 出現語):
            raise ValueError('Data範囲外の否定・条件が未解消')
        対応.append((値.座標ID, 値.種別, 'Dataの作用域へ対応。真偽は後段で検討'))
    for 関係 in ir.関係:
        if 関係.関係ID in 構造関係:
            continue
        if (関係.種別 != '数量単位' or 関係.条件 or 関係.値状態 != 値状態.確定
                or any(k not in 座標 for k in (*関係.始点, *関係.終点))):
            raise ValueError('追加会話に未接続のHDS関係')
    保持理由 = set()
    for 残差 in ir.残差:
        if 残差.種別 != '未解共参照' or 残差.影響座標 or not 範囲内(残差.原文):
            raise ValueError('追加会話に未解消のHDS残差:' + 残差.種別)
        対応.append((残差.残差ID, 残差.種別, 'Data内の未解決参照として後段へ保持'))
        保持理由.add(残差.理由)
    if any(損失 not in 保持理由 for 作用 in ir.意味作用履歴 for 損失 in 作用.損失):
        raise ValueError('追加会話に未解消のHDS意味損失')
    return {'版': 改善HDS照合版, '行為意味印': 意味指紋(行為),
            'Data作用域': 範囲, '座標残差対応': 対応,
            '範囲': '有限会話文法の全消費と実HDSの対応。一般自然言語理解ではない'}

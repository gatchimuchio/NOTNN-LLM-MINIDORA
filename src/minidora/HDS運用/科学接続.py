"""既存科学能力群を候補報告の作用として接続する。正答認定へ読み替えない。"""
from __future__ import annotations
from dataclasses import asdict
import math

from ..科学専門能力 import 科学専門能力解決
from ..能力結果復元 import 能力結果を復元
from ..能力合成 import 登録能力, _符号化
from ..製品版.型 import 能力結果
from ..役割計画 import 役割作用
from ..会話意味 import 意味目的
from .契約 import JSONを読む, 内容署名


class 科学候補報告モジュール:
    名前 = '科学候補報告'
    版 = 'HDS科学候補接続-v1'
    優先度 = 0

    def 判定(self, 文脈):
        return 1.0

    def 実行(self, 文脈):
        try:
            aux = 文脈.補助
            if type(aux) is not dict or aux.get('合成設定') != {} or len(aux.get('合成入力', ())) != 1:
                raise ValueError('科学問題の単一資料と空設定が必要')
            元 = 能力結果を復元(aux['合成入力'][0]['結果'])
            入力 = 元.データ if set(元.データ) == {'問題', '選択肢'} else JSONを読む(元.本文, 上限=100000)
            if type(入力) is not dict or set(入力) != {'問題', '選択肢'}:
                raise ValueError('問題と選択肢だけを受け取る。正解情報は受理しない')
            if type(入力['問題']) is not str or not 1 <= len(入力['問題']) <= 16000:
                raise ValueError('問題文の型・上限')
            選択肢 = 入力['選択肢']
            if type(選択肢) not in (list, tuple) or not 2 <= len(選択肢) <= 16:
                raise ValueError('選択肢の型・数')
            if any(type(x) is not str or not 1 <= len(x) <= 4096 for x in 選択肢):
                raise ValueError('選択肢本文の型・上限')
            候補 = 科学専門能力解決(入力['問題'], tuple(選択肢))
            報告 = None
            if 候補 is not None:
                if type(候補.index) is not int or not 0 <= 候補.index < len(選択肢):
                    raise ValueError('科学候補の添字不正')
                if type(候補.信頼度) not in (int, float) or not math.isfinite(候補.信頼度):
                    raise ValueError('科学候補の数値不正')
                報告 = {'候補番号': 候補.index + 1, '候補本文': 選択肢[候補.index],
                        '作用': 候補.解決器, '計算値': 候補.value,
                        '局所判定値': 候補.信頼度, '理由': 候補.reason}
                本文 = f'既存科学能力の候補は{候補.index + 1}番「{選択肢[候補.index]}」です。作用：{候補.解決器}。'
            else:
                本文 = '既存科学能力から適用可能で一致する候補は得られませんでした。'
            限界 = 'これは候補生成の報告です。局所判定値は校正済み正答確率ではなく、一般的な意味理解・独立検証・最終正答の認定ではありません。'
            資料 = {'版': self.版, '種別': '科学候補報告', '原要求': 入力,
                    '原要求印': 内容署名(入力), '候補': 報告, '限界': 限界}
            _符号化(資料)
            return 能力結果(True, 本文 + '\n' + 限界, 根拠=('既存科学専門能力の実行結果',), 参照=元.参照, データ=資料)
        except (ValueError, TypeError, KeyError, AttributeError, OverflowError) as exc:
            return 能力結果(False, '', 保留理由='科学候補入力不正:' + str(exc))

    def 登録(self):
        return 登録能力(self)


def 科学作用群():
    return (役割作用('科学候補の構成', '科学候補報告', '科学候補報告',
        lambda p: (('問題', 意味目的('原資料', {'資料': p['資料']})),),
        lambda p: {}, lambda p: set(p) == {'資料'},
        不成立条件=('入力契約外',), 保持事項=('問題', '選択肢', '候補と正答の区別')),)

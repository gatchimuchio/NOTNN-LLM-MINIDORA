"""HDS通常運用の会話入口。採否はHDSに委ね、採用された状態差だけを保存する。"""
from __future__ import annotations
from copy import deepcopy
from dataclasses import asdict
import json
from threading import Lock

from ..HDS実行主体 import HDS実行主体, HDS実行状態, HDS終端
from ..統合駆動_v2 import HDS運用政策, HDS検証器
from .契約 import 内容署名 as 署名
from ..能力合成 import 合成計画, _符号化
from ..会話意味 import 意味目的
from .契約 import (名前を検査, 資料を正規化, 成果を復元, 計画を保存,
                   JSONを読む, 運用応答, 運用版, 組の位置, 組を復元)
from .能力目録 import 運用能力目録
from .要求構成 import 運用要求構成器, 会話要求を復元
from .作用 import (入力名, 回答名, 完了状態, 未完残差, 現在案,
    要求構成作用, 能力実行作用, 計画修復作用, 回答確定作用, 最終回答を検査, 停止対応作用)


class HDS運用セッション:
    def __init__(self, セッションID='default', *, 資料=None, 外部読取許可=False,
                 取得器=None, 再利用=True, 追加能力=(), 追加作用=(), 構文化器=None,
                 最大作用回数=128):
        名前を検査(セッションID)
        if type(外部読取許可) is not bool or type(再利用) is not bool:
            raise ValueError('外部許可と再利用はboolが必要')
        if type(最大作用回数) is not int or not 4 <= 最大作用回数 <= 512:
            raise ValueError('作用数上限は4〜512')
        self.セッションID = セッションID
        self.外部読取許可 = 外部読取許可
        self.最大作用回数 = 最大作用回数
        self.目録 = 運用能力目録(セッションID, 外部読取許可=外部読取許可,
            取得器=取得器, 再利用=再利用, 追加能力=追加能力, 追加作用=追加作用)
        self.構成器 = 運用要求構成器(self.目録, 構文化器=構文化器)
        self._資料 = 資料を正規化(資料 or {})
        self._前回 = None
        self._最後要求 = None
        self._保留要求 = None
        self._履歴 = []
        self._根 = 署名((運用版, セッションID, self._資料))
        self._世代 = 0
        self._ロック = Lock()

    def 能力一覧(self):
        return self.目録.一覧()

    def 資料一覧(self):
        with self._ロック:
            return {k: 成果を復元(v) for k, v in self._資料.items()}

    def 応答(self, 原文, *, 意味目的_=None, 明示計画=None, 計画資料=None, 停止確認=None):
        if not self._ロック.acquire(blocking=False):
            raise RuntimeError('同一セッションで処理中')
        try:
            return self._応答(原文, 意味目的_, 明示計画, 計画資料, 停止確認)
        finally:
            self._ロック.release()

    def _応答(self, 原文, 目的, 計画, 計画資料, 停止確認=None):
        if 停止確認 is not None and not callable(停止確認):
            raise ValueError("停止確認は呼出可能関数が必要")
        if type(原文) is not str or not 原文.strip() or len(原文) > 8192:
            raise ValueError('依頼は1〜8192文字')
        if 目的 is not None and 計画 is not None:
            raise ValueError('意味目的と明示計画を同時指定しない')
        if 目的 is not None and type(目的) is not 意味目的:
            raise ValueError('意味目的型が必要')
        if 目的 is not None:
            目的.鍵()
        if 計画 is None and 計画資料 is not None:
            raise ValueError('計画なしで計画資料を指定しない')
        if len(self._履歴) >= 128 and 原文 not in ('/初期化', '会話を初期化して'):
            return 運用応答('SUSPEND', '会話記録の上限です。保存後に初期化してください。', ('会話容量上限',))
        入力 = {'原文': 原文, 'セッションID': self.セッションID, '資料': deepcopy(self._資料),
                '外部許可': self.外部読取許可, '前回': deepcopy(self._前回),
                '最後要求': deepcopy(self._最後要求), '保留要求': deepcopy(self._保留要求),
                '世代': self._世代, '履歴根': self._根}
        if 目的 is not None:
            入力['意味目的'] = asdict(目的)
        if 計画 is not None:
            if type(計画) is not 合成計画:
                raise TypeError('合成計画型が必要')
            入力['明示計画'] = 計画を保存(計画, 計画資料 or {})
        作用群 = (要求構成作用(self.構成器),
            *(能力実行作用(self.目録, 名) for 名 in self.目録.登録),
            計画修復作用(self.構成器), 回答確定作用(self.目録))
        if 停止確認 is not None:
            作用群 = tuple(停止対応作用(x, 停止確認) for x in 作用群)

        def 最終検証(状態, _):
            if 停止確認 is not None:
                停止 = 停止確認()
                if type(停止) is not bool:
                    raise TypeError("停止確認はboolが必要")
                if 停止:
                    return False
            return 最終回答を検査(状態, self.目録)

        政策 = HDS運用政策(許可権限=('外部読取',) if self.外部読取許可 else (), 自動形成=False)
        # 既存の単一通常循環が、計画・能力・修復・回答の次作用を選ぶ。
        主体 = HDS実行主体(作用群, 最大作用回数=self.最大作用回数, 政策=政策,
            最終検証器=(HDS検証器('HDS運用/原要求成果照合',
                          最終検証, 運用版),))
        初期 = HDS実行状態(目的=(原文,), 要求状態=frozenset({完了状態}),
                    残差=frozenset({未完残差}), 成果=((入力名, 入力),))
        実行 = 主体.実行(初期)
        成果 = dict(実行.状態.成果)
        原因 = tuple(dict.fromkeys(str(x) for x in 実行.理由))
        if 実行.終端 == HDS終端.採用:
            束 = 成果[回答名]
            # 検証済みHDS成果の保存。ここで独自の候補選択や採否を行わない。
            if 束['種別'] == '初期化':
                self._資料 = {}
                self._前回 = self._最後要求 = self._保留要求 = None
                self._履歴 = []
                self.目録.再利用庫.消去()
            elif 束['種別'] in ('登録', '更新'):
                self._資料 = {**self._資料, **deepcopy(束['資料変更'])}
            elif 束['種別'] == '処理':
                self._前回 = deepcopy(束)
                案 = 現在案(実行.状態)[1]
                if not 案.get('再表現元'):
                    self._最後要求 = deepcopy(束['意味'])
                self._保留要求 = None
            本文 = 束['本文']
            出力 = tuple((k, 成果を復元(v)) for k, v in 束['出力'].items())
        else:
            診断 = 成果.get('要求診断', {})
            if 診断.get('保留要求'):
                self._保留要求 = deepcopy(診断['保留要求'])
            理由 = 診断.get('理由') or (実行.阻害履歴[-1].詳細 if 実行.阻害履歴 else '') or next((str(x) for h in reversed(実行.履歴) for x in h.理由), '')
            if not 理由:
                理由 = 実行.停止種別.value
            本文 = '依頼を完了できませんでした。' + 理由
            出力 = ()  # 途中成果を利用者向けの成功出力にしない。
            原因 = tuple(dict.fromkeys((*原因, 理由)))
        記録 = {'原文': 原文, '本文': 本文, '状態': 実行.終端.value, '前根': self._根,
                '実行署名': 実行.状態.状態署名, '世代': self._世代}
        self._根 = 署名(記録)
        self._履歴.append({**記録, '根': self._根})
        self._世代 += 1
        return 運用応答(実行.終端.value, 本文, 原因, 実行, 出力)

    def 保存(self):
        with self._ロック:
            内容 = {'版': 運用版, 'セッションID': self.セッションID,
                '能力契約': self.目録.契約印, '資料': self._資料, '前回': self._前回,
                '最後要求': self._最後要求, '保留要求': self._保留要求,
                '履歴': self._履歴, '根': self._根, '世代': self._世代}
            位置 = 組の位置(内容)
            本文 = json.dumps({'内容': 内容, '組位置': 位置, '整合印': 署名((内容, 位置))}, ensure_ascii=False,
                              allow_nan=False, separators=(',', ':'))
            if len(本文.encode('utf-8')) > 8_000_000:
                raise ValueError('保存容量上限')
            return 本文

    @classmethod
    def 復元(cls, 本文, *, 外部読取許可=False, **構成):
        値 = JSONを読む(本文)
        if type(値) is not dict or set(値) != {'内容', '組位置', '整合印'}:
            raise ValueError('保存外形不正')
        if 署名((値['内容'], 値['組位置'])) != 値['整合印']:
            raise ValueError('保存整合印不一致')
        内容 = 組を復元(値['内容'], 値['組位置'])
        if type(内容) is not dict or set(内容) != {'版', 'セッションID', '能力契約', '資料',
                '前回', '最後要求', '保留要求', '履歴', '根', '世代'}:
            raise ValueError('保存項目不正')
        if 内容['版'] != 運用版:
            raise ValueError('保存版又は整合印不一致')
        if type(内容['世代']) is not int or 内容['世代'] < 0 or type(内容['履歴']) is not list or len(内容['履歴']) > 128:
            raise ValueError('会話世代・履歴不正')
        # 外部許可・実行コード・呼出可能関数を保存内容から復元しない。
        復元 = cls(内容['セッションID'], 資料={k: 成果を復元(v) for k, v in 内容['資料'].items()},
                   外部読取許可=外部読取許可, **構成)
        if 復元.目録.契約印 != 内容['能力契約']:
            raise ValueError('保存時と能力契約が異なる')
        for 名 in ('最後要求', '保留要求'):
            if 内容[名] is not None:
                会話要求を復元(内容[名])
        前回 = 内容['前回']
        if 前回 is not None:
            if type(前回) is not dict or 前回.get('種別') != '処理':
                raise ValueError('保存された前回成果不正')
            for v in 前回['出力'].values():
                成果を復元(v)
            for k, v in 前回['内容成果']:
                名前を検査(k)
                成果を復元(v)
            for k, v in 前回['依存資料'].items():
                名前を検査(k)
                if type(v) is not str or len(v) != 64:
                    raise ValueError('依存資料印不正')
        前根 = None
        for 記録 in 内容['履歴']:
            if type(記録) is not dict or set(記録) != {'原文', '本文', '状態', '前根', '実行署名', '世代', '根'}:
                raise ValueError('履歴形式不正')
            if 前根 is not None and 記録['前根'] != 前根:
                raise ValueError('履歴連鎖不一致')
            if 署名({k: v for k, v in 記録.items() if k != '根'}) != 記録['根']:
                raise ValueError('履歴整合印不一致')
            前根 = 記録['根']
        if 前根 is not None and 前根 != 内容['根']:
            raise ValueError('履歴根不一致')
        復元._前回, 復元._最後要求, 復元._保留要求 = 前回, 内容['最後要求'], 内容['保留要求']
        復元._履歴, 復元._根, 復元._世代 = 内容['履歴'], 内容['根'], 内容['世代']
        return 復元

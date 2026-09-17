"""既存製品UI・監査台帳へのHDS運用接続。既存製品の既定経路は変更しない。"""
from __future__ import annotations
from threading import Lock
from ..製品版.監査 import 監査台帳
from ..製品版.型 import 製品応答
from ..能力合成 import _参照結合
from .契約 import 名前を検査, 運用版
from .セッション import HDS運用セッション


class HDS運用製品:
    def __init__(self, *, 監査台帳_=None, 最大セッション数=16, **構成):
        if type(最大セッション数) is not int or not 1 <= 最大セッション数 <= 64:
            raise ValueError('セッション上限は1〜64')
        self.監査台帳 = 監査台帳_ if 監査台帳_ is not None else 監査台帳()
        self._構成 = 構成
        self._最大 = 最大セッション数
        self._セッション = {}
        self._索引ロック = Lock()

    def _対象(self, 名):
        名前を検査(名)
        with self._索引ロック:
            if 名 not in self._セッション:
                if len(self._セッション) >= self._最大:
                    raise ValueError('セッション数上限')
                self._セッション[名] = {'実体': HDS運用セッション(名, **self._構成),
                                         'ロック': Lock(), '監査根': ''}
            return self._セッション[名]

    def 能力一覧(self):
        # 一覧取得によって利用者セッションを増やさない。
        with self._索引ロック:
            if self._セッション:
                対象 = next(iter(self._セッション.values()))['実体']
            else:
                対象 = HDS運用セッション('能力照会', **self._構成)
        return tuple(x['名前'] for x in 対象.能力一覧())

    def 応答(self, 原文, *, セッションID='default'):
        項 = self._対象(セッションID)
        if not 項['ロック'].acquire(blocking=False):
            raise RuntimeError('同一セッションで処理中')
        try:
            結果 = 項['実体'].応答(原文)
            監査 = self.監査台帳.開始(原文, セッションID, 項['監査根'])
            監査.経路設定('HDS通常運用')
            追跡 = 結果.辞書化()
            監査.記録('HDS通常循環', 'HDS運用', 運用版, {'原文': 原文}, 追跡)
            記録 = 監査.確定(結果.本文, 結果.状態)
            項['監査根'] = 記録.ルートハッシュ
            参照 = _参照結合(r for _, v in 結果.出力 for r in v.参照)
            return 製品応答(セッションID, 結果.本文, 結果.状態, 'HDS通常運用',
                記録.追跡ID, 記録.ルートハッシュ, 参照,
                tuple(x['名前'] for x in 項['実体'].能力一覧()),
                {'HDS': 追跡.get('HDS'), '理由': list(結果.理由)})
        finally:
            項['ロック'].release()

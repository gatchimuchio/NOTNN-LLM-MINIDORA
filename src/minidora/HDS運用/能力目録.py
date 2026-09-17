"""既存能力の登録・契約読取。目録は回答者でも第二の採否主体でもない。"""
from __future__ import annotations
from types import MappingProxyType
from ..能力合成 import 登録能力
from ..統合能力 import 統合能力群
from ..純粋結果庫 import 純粋結果庫
from ..長文脈管理 import 長文脈庫
from ..能力意味カタログ import 能力意味カタログ
from ..目的計画 import 目的計画器
from ..役割計画 import 役割計画器
from ..会話能力接続 import 会話能力群
from ..会話作用契約 import 会話作用群
from ..集合会話接続 import 数量集合モジュール, 集合作用群
from ..命題能力接続 import 命題能力群, 命題作用群
from ..文脈命題接続 import 文脈命題能力群, 文脈命題作用群
from ..監査改善計画 import 改善統合能力群, 改善作用群
from ..知識取得 import 知識取得器
from ..製品版.検索 import SearXNG検索供給器
from .契約 import 内容署名 as 署名
from .契約 import 名前を検査
from .科学接続 import 科学候補報告モジュール, 科学作用群


class 運用能力目録:
    def __init__(self, セッションID: str, *, 外部読取許可=False, 取得器=None,
                 再利用=True, 追加能力=(), 追加作用=()):
        if type(外部読取許可) is not bool or type(追加能力) is not tuple or type(追加作用) is not tuple:
            raise ValueError('目録構成の型不正')
        self.原記録庫 = 長文脈庫(セッションID)
        self.再利用庫 = 純粋結果庫(有効=再利用)
        取得器 = 取得器 if 取得器 is not None else 知識取得器(SearXNG検索供給器())
        基底 = 統合能力群(self.原記録庫, self.再利用庫,
                           外部読取許可=外部読取許可, 取得器=取得器)
        追加 = (*会話能力群(取得器, 外部許可=外部読取許可), 数量集合モジュール().登録(),
                *命題能力群(), *文脈命題能力群(), *改善統合能力群(), 科学候補報告モジュール().登録(), *追加能力)
        self.登録 = {}
        for 項 in (*基底, *追加):
            if type(項) is not 登録能力 or type(項.外部読取) is not bool:
                raise ValueError('登録能力契約が必要')
            名 = 名前を検査(項.モジュール.名前)
            名前を検査(項.モジュール.版)
            if 名 in self.登録:
                raise ValueError('能力名の重複:' + 名)
            if not callable(getattr(項.モジュール, '実行', None)) or not callable(getattr(項.モジュール, '判定', None)):
                raise ValueError('能力の実行・判定関数が必要')
            self.登録[名] = 項
        self.登録 = MappingProxyType(self.登録)
        self.固定一覧 = self.一覧()
        self.目的計画 = 目的計画器(能力意味カタログ(self.一覧(基底)))
        self.役割作用 = (*会話作用群(), *集合作用群(), *命題作用群(),
                         *文脈命題作用群(), *改善作用群(), *科学作用群(), *追加作用)
        self.役割計画 = 役割計画器(self.役割作用, self.固定一覧)
        self.契約印 = 署名((self.固定一覧, self.目的計画.カタログ.ハッシュ, self.役割計画.契約印))

    def 一覧(self, 群=None):
        return tuple({'名前': x.モジュール.名前, '版': x.モジュール.版, '外部読取': x.外部読取}
                     for x in (self.登録.values() if 群 is None else 群))

    def 契約を検査(self):
        if self.一覧() != self.固定一覧:
            raise ValueError('実行中に能力名・版・権限が変化した')
        if 署名((self.固定一覧, self.目的計画.カタログ.ハッシュ, self.役割計画.契約印)) != self.契約印:
            raise ValueError('意味契約の変更')

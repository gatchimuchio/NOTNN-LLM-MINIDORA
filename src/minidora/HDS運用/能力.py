"""既存能力をHDSへ供給する一つの目録。登録は信頼済み実装からだけ行う。"""
from __future__ import annotations
from copy import deepcopy
from ..能力合成 import 能力合成器, 登録能力, _文脈辞書
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
from .値 import 指紋, 運用版
from .科学 import 科学能力接続, 科学作用契約


class 運用能力目録:
    def __init__(self, セッションID, *, 外部読取許可=False, 取得器=None,
                 追加能力=(), 追加役割作用=(), 再利用=True):
        if type(外部読取許可) is not bool:
            raise TypeError("外部読取許可はbool")
        backend = 取得器 if 取得器 is not None else 知識取得器(SearXNG検索供給器())
        self.原記録庫 = 長文脈庫(セッションID)
        self.再利用庫 = 純粋結果庫(有効=再利用)
        base = 統合能力群(self.原記録庫, 純粋結果庫(有効=False),
                         外部読取許可=外部読取許可, 取得器=backend)
        extra = (*会話能力群(backend, 外部許可=外部読取許可), 数量集合モジュール().登録(),
                 *命題能力群(), *文脈命題能力群(), *改善統合能力群(), 科学能力接続().登録(), *追加能力)
        self.登録 = tuple((*base, *extra))
        self.構造検査器 = 能力合成器(self.登録)
        self._能力 = {r.モジュール.名前: r for r in self.登録}
        self._一覧 = self.一覧()
        self.単体目的 = 目的計画器(能力意味カタログ(tuple(self._記述(r) for r in base)))
        self.役割作用 = (*会話作用群(), *集合作用群(), *命題作用群(),
                         *文脈命題作用群(), *改善作用群(), *科学作用契約(), *追加役割作用)
        self.複数目的 = 役割計画器(self.役割作用, self._一覧)
        # 既存の純粋部品だけを明示する。追加能力は既定では再利用しない。
        self._純粋 = {r.モジュール.名前 for r in base
                      if not r.外部読取 and r.モジュール.名前 not in ("多段解決", "長文脈選択")}
        self._純粋.update(r.モジュール.名前 for r in extra[:-len(追加能力) or None] if not r.外部読取)
        self.ハッシュ = 指紋({"版": 運用版, "登録": self._一覧,
                            "役割契約": self.複数目的.契約印,
                            "単体契約": self.単体目的.カタログ.ハッシュ,
                            "再利用対象": sorted(self._純粋)})

    @staticmethod
    def _記述(r):
        return {"名前": r.モジュール.名前, "版": r.モジュール.版, "外部読取": r.外部読取}

    def 一覧(self):
        return tuple(self._記述(r) for r in self.登録)

    def 照合(self):
        if self.一覧() != self._一覧:
            raise ValueError("運用中に能力登録又は版が変更された")

    def 取得(self, name):
        self.照合()
        if name not in self._能力:
            raise ValueError("未登録能力:" + name)
        return self._能力[name]

    def 再利用鍵(self, name, 文脈):
        registration = self.取得(name)
        if name not in self._純粋 or registration.外部読取:
            return None
        # 個別能力に渡る全意味入力を含む。工程名は命令ではなく接続住所。
        # 住所自体も文脈に含めるため、契約外に同一視しない。
        return 指紋({"能力": name, "版": registration.モジュール.版,
                    "目録": self.ハッシュ, "文脈": _文脈辞書(文脈)})

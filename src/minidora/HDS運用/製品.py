"""既存CLI/API/画面から同じHDS通常運用を呼ぶ。別のrouterは置かない。"""
from __future__ import annotations
from threading import RLock
from ..製品版.型 import 製品応答
from ..製品版.監査 import 監査台帳
from .セッション import HDS運用セッション
from .値 import 運用版, 文字を検査


class HDS製品ミニドラ:
    def __init__(self, *, 外部読取許可=False, 取得器=None, 監査台帳_=None, 最大セッション数=64):
        if type(外部読取許可) is not bool:
            raise TypeError("外部読取許可はbool")
        if type(最大セッション数) is not int or not 1 <= 最大セッション数 <= 256:
            raise ValueError("セッション数上限")
        self.監査台帳 = 監査台帳_ if 監査台帳_ is not None else 監査台帳()
        self._許可, self._取得器, self._上限 = 外部読取許可, 取得器, 最大セッション数
        self._会話, self._前監査 = {}, {}
        self._ロック = RLock()
        self._会話ロック = {}

    def 能力一覧(self):
        return ("HDS単一主体の依頼解釈・目的計画・能力工程・最終採否", "数式・JSON/CSV・文書処理",
                "数量比較・集計と条件訂正", "提供知識・本文・命題・仮説・介入の検討",
                "条件付き回復・再表現・資料更新・保存復元", "工程別監査")

    def セッション(self, ID):
        文字を検査(ID, "セッションID", 128)
        with self._ロック:
            if ID not in self._会話:
                if len(self._会話) >= self._上限:
                    raise ValueError("セッション数上限")
                self._会話[ID] = HDS運用セッション(ID, 外部読取許可=self._許可, 取得器=self._取得器)
                self._会話ロック[ID] = RLock()
            return self._会話[ID]

    def 応答(self, 入力文, *, セッションID="default"):
        session = self.セッション(セッションID)
        with self._会話ロック[セッションID]:
            audit = self.監査台帳.開始(入力文, セッションID, self._前監査.get(セッションID, ""))
            audit.経路設定("HDS通常運用")
            結果 = session.応答(入力文, 外部読取許可=self._許可)
            for row in (結果.追跡 or {}).get("作用", ()):
                audit.記録("HDS作用", row["作用ID"], 運用版,
                    {"署名": row["作用入力署名"]},
                    {"状態": row["作用状態"], "状態差": row["状態差"], "理由": row["理由"]})
            audit.記録("HDS終端", "HDS実行主体", 運用版, 入力文,
                         {"状態": 結果.状態, "本文": 結果.本文, "理由": 結果.理由})
            status = "APPROVE" if 結果.成立 else "FAIL" if 結果.状態 == "FAIL" else "SUSPEND"
            record = audit.確定(結果.本文, status)
            self._前監査[セッションID] = record.ルートハッシュ
            return 製品応答(セッションID, 結果.本文, status, "HDS通常運用", record.追跡ID,
                    record.ルートハッシュ, 結果.結果.参照 if 結果.結果 else (),
                    tuple(row["能力"] for row in (結果.追跡 or {}).get("能力試行", ())),
                    {"HDS": 結果.追跡, "HDS終端": 結果.状態})

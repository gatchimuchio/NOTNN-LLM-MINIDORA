"""実HDS→目的IR→作用契約の経路探索→既存統合セッションを閉じる追加入口。"""
from __future__ import annotations
from dataclasses import dataclass
from threading import Lock
from .統合実行 import 統合セッション, 統合応答
from .能力意味カタログ import 能力意味カタログ
from .目的計画 import 目的計画器, 目的計画結果
from .HDS目的射影 import HDSから目的要求, 目的射影結果
from .hds_compiler import 公開HDSコンパイラ

@dataclass(frozen=True, slots=True)
class 目的会話応答:
    状態: str
    本文: str
    理由: str = ''
    射影: 目的射影結果 | None = None
    計画: 目的計画結果 | None = None
    実行: 統合応答 | None = None

    @property
    def 成立(self):
        return self.状態 == '合格' and self.実行 is not None and self.実行.成立

    def 辞書化(self):
        return {'状態': self.状態, '本文': self.本文, '理由': self.理由,
                'HDS原文': self.射影.HDS保持.原文 if self.射影 and self.射影.HDS保持 else None,
                '局所解消': self.射影.局所解消 if self.射影 else (),
                '計画経路': self.計画.作用経路 if self.計画 else (),
                '実行': self.実行.辞書化() if self.実行 else None}


class 目的会話セッション:
    """標準チャットを置換しない追加入口。実行器・採用状態は既存の一つを共有する。"""
    def __init__(self, セッションID: str, *, 統合: 統合セッション | None = None):
        self.統合 = 統合 if 統合 is not None else 統合セッション(セッションID)
        if type(self.統合) is not 統合セッション or self.統合.起点().セッションID != セッションID:
            raise ValueError('統合セッションの所有が不一致')
        self.カタログ = 能力意味カタログ(self.統合.能力一覧())
        self._計画器 = 目的計画器(self.カタログ)
        self._ロック = Lock()

    def 応答(self, 原文: str, 資料=None, *, 停止要求=None) -> 目的会話応答:
        if not self._ロック.acquire(blocking=False):
            return 目的会話応答('保留', '', '同じ目的会話の処理中')
        projection = plan = None
        try:
            start, history = self.統合.採用履歴スナップショット()
            current = 能力意味カタログ(self.統合.能力一覧())
            if current.ハッシュ != self.カタログ.ハッシュ:
                raise ValueError('意味カタログの変更')
            self.統合._停止(停止要求)
            if type(原文) is not str or not 原文.strip() or len(原文) > 8192:
                raise ValueError('依頼文の範囲外')
            ir = 公開HDSコンパイラ().コンパイル(原文)
            prior = history[-1]['出力'] if history else ()
            projection = HDSから目的要求(ir, {} if 資料 is None else 資料, 前回成果=prior)
            if not projection.成立:
                return 目的会話応答('保留', '', projection.理由, projection)
            self.統合._停止(停止要求)
            plan = self._計画器.計画する(projection.要求)
            if not plan.成立:
                return 目的会話応答('保留', '', plan.理由, projection, plan)
            prepared = self.統合.準備(plan.計画, plan.Data, 依頼文=原文)
            if prepared.起点 != start:
                return 目的会話応答('保留', '', '解釈後に会話状態が変化', projection, plan)
            result = self.統合.実行(prepared, 停止要求=停止要求)
            return 目的会話応答(result.状態, result.本文, result.理由, projection, plan, result)
        except (ValueError, TypeError, KeyError, AttributeError, RecursionError, InterruptedError) as exc:
            state = '中止' if isinstance(exc, InterruptedError) else '保留'
            return 目的会話応答(state, '', str(exc), projection, plan)
        finally:
            self._ロック.release()

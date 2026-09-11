"""目的と条件を固定した実行監督。回復可能な資料不足だけを再計画する。

既に行ったGETは取り消さない。同一要求内の取得成功だけを再参照できる。
資料の命令、任意の例外文、矛盾を再計画の許可として扱わない。
"""
from __future__ import annotations
from copy import deepcopy
from dataclasses import dataclass, asdict
from hashlib import sha256
from .複数素材計画 import 複数素材計画器
from .会話失敗 import 失敗署名
from .能力合成 import _符号化

@dataclass(frozen=True, slots=True)
class 監督結果:
    状態: str
    本文: str
    理由: str
    試行: tuple[dict, ...]
    実行: object = None
    失敗: 失敗署名 | None = None

    @property
    def 成立(self): return self.状態 == '合格' and self.実行 is not None and self.実行.成立


class 会話実行監督:
    def __init__(self, 統合, 計画器: 複数素材計画器, *, 最大試行数=4):
        if type(最大試行数) is not int or not 1 <= 最大試行数 <= 8:
            raise ValueError('再計画予算不正')
        if type(計画器) is not 複数素材計画器: raise ValueError('複数素材計画器が必要')
        self.統合, self.計画器, self.最大試行数 = 統合, 計画器, 最大試行数

    def 実行(self, 目的, 素材, 設定, 原文, *, 外部読取許可=False, 停止要求=None):
        start = self.統合.起点()
        materials, settings = deepcopy(素材), deepcopy(設定)
        fixed = sha256(_符号化([asdict(目的), settings])).hexdigest()
        blocked, seen, attempts = [], set(), []
        last = failure = None
        try:
            for _ in range(self.最大試行数):
                failure = None  # 前の試行の原因で新しい失敗を説明しない。
                self.統合._停止(停止要求)
                if start != self.統合.起点(): raise ValueError('再計画中に会話状態が変化')
                if sha256(_符号化([asdict(目的), settings])).hexdigest() != fixed:
                    raise ValueError('再計画で目的条件が変化')
                plan = self.計画器.計画する(目的, materials, settings, 外部読取許可=外部読取許可, 禁止=tuple(blocked))
                signature = sha256(_符号化([asdict(plan.計画), [(k, asdict(v)) for k, v in plan.工程意味.values()]])).hexdigest()
                if signature in seen: raise ValueError('同じ失敗計画を反復しません')
                seen.add(signature)
                prepared = self.統合.準備(plan.計画, plan.Data, 依頼文=原文)
                if prepared.起点 != start: raise ValueError('準備中に会話状態が変化')
                last = self.統合.実行(prepared, 外部読取許可=外部読取許可, 停止要求=停止要求)
                record = {'状態': last.状態, '経路': [r[0] for r in plan.工程意味.values()],
                          '予定費用': plan.費用, '理由': last.理由, '目的条件hash': fixed,
                          '実行hash': last.実行.ルートハッシュ if last.実行 else '', '取得済再参照': [],
                          '計画hash': signature, '実行履歴': [asdict(r) for r in last.実行.履歴] if last.実行 else []}
                attempts.append(record)
                if last.成立:
                    return 監督結果('合格', last.本文, '', tuple(deepcopy(attempts)), last)
                if last.状態 in ('中止', '失敗') or last.実行 is None or not last.実行.履歴:
                    break
                terminal = last.実行.履歴[-1]
                rule_id, state = plan.工程意味[terminal.工程]
                rule = self.計画器.作用[rule_id]
                # 新しい記載解釈の登録された診断だけを回復判定へ用いる。
                failure = 失敗署名.復元(terminal.理由) if terminal.能力 == '会話記載解釈' else None
                record['失敗署名'] = asdict(failure) if failure else None
                if (failure is None or failure.種類 not in rule.回復可能
                        or failure.対象 not in state.対象 or not 外部読取許可):
                    break
                blocked.append((rule_id, state))
                # 同一ターン・同一条件で取得済みの本文を保存。次の要求へは持ち越さない。
                for sid, value in last.実行.中間結果:
                    producer, produced = plan.工程意味[sid]
                    if self.計画器.作用[producer].外部読取:
                        materials[produced] = deepcopy(value)
                        record['取得済再参照'].append(asdict(produced))
            reason = failure.詳細 if failure else last.理由 if last else '実行経路がありません'
            return 監督結果(last.状態 if last else '保留', '', reason, tuple(deepcopy(attempts)), last, failure)
        except (ValueError, TypeError, KeyError, AttributeError, RecursionError, InterruptedError) as exc:
            return 監督結果('中止' if isinstance(exc, InterruptedError) else '保留', '', str(exc),
                              tuple(deepcopy(attempts)), last, failure)

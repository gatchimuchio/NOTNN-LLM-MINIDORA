"""比較・照会・既存目的実行を、一つの採用状態と確認会話へ接続する。

有限の会話行為実装。入力記録、確認待ちの目的、採用した成果を区別する。
一般的な自由作文・意味理解・因果推論の完成ではない。
"""
from __future__ import annotations
from copy import deepcopy
from dataclasses import asdict, dataclass
from threading import Lock
from .hds_compiler import 公開HDSコンパイラ
from .会話要求 import 会話を解釈
from .会話能力 import 会話追加能力
from .会話計画接続 import 会話計画作用, 会話目的を準備
from .複数素材計画 import 複数素材計画器
from .会話実行監督 import 会話実行監督
from .統合実行 import 統合セッション
from .能力意味カタログ import 能力意味カタログ
from .HDS目的射影 import HDSから目的要求
from .目的計画 import 目的計画器
from .能力合成 import 合成計画, 合成工程, 素材参照, _結果辞書, _符号化
from .製品版.型 import 能力結果
from .応答構成 import 能力結果を復元

汎用会話版 = 'MINIDORA-汎用会話-v0.1'

@dataclass(frozen=True, slots=True)
class 会話応答:
    状態: str
    本文: str
    理由: str = ''
    情報: dict | None = None
    実行: object = None

    @property
    def 成立(self): return self.状態 == '合格' and self.実行 is not None and self.実行.成立
    def 辞書化(self):
        return {'状態': self.状態, '本文': self.本文, '理由': self.理由, '情報': deepcopy(self.情報 or {}),
                '実行': self.実行.辞書化() if self.実行 else None}


class 汎用会話セッション:
    def __init__(self, セッションID, *, 外部読取許可=False, 取得器=None, 最大会話数=128):
        if type(最大会話数) is not int or not 1 <= 最大会話数 <= 512:
            raise ValueError('会話記録予算不正')
        self.統合 = 統合セッション(セッションID, 外部読取許可=外部読取許可,
            取得器=取得器, 追加能力=会話追加能力())
        extra = {r.Module.名前: r.Module.版 for r in 会話追加能力()}
        registered = self.統合.能力一覧()
        if any(r['名前'] in extra and (r['版'] != extra[r['名前']] or r['外部読取']) for r in registered):
            raise ValueError('会話能力の版又は権限不一致')
        self._カタログ = 能力意味カタログ(tuple(r for r in registered if r['名前'] not in extra))
        self._計画器 = 目的計画器(self._カタログ)
        self._監督 = 会話実行監督(self.統合, 複数素材計画器(会話計画作用()))
        self._許可 = 外部読取許可
        self._ロック = Lock()
        self._記録 = ()
        self._上限 = 最大会話数
        self._保留 = self._前要求 = None

    def 会話記録(self):
        with self._ロック: return deepcopy(self._記録)

    def 初期化(self):
        if not self._ロック.acquire(blocking=False): raise ValueError('会話処理中')
        try:
            self.統合.初期化(); self._保留 = self._前要求 = None; self._記録 = ()
        finally: self._ロック.release()

    def _既存(self, ir, materials, start, stop, style, maximum):
        _, history = self.統合.採用履歴スナップショット()
        prior = history[-1]['出力'] if history else ()
        # 回答の表示文を数式へ戻さず、保持した元成果を利用する。
        if len(prior) == 1:
            meaning = prior[0][1].データ.get('回答意味', {})
            if meaning.get('種別') == '既存成果':
                prior = tuple((f'元成果:{i}', 能力結果を復元(r)) for i, r in enumerate(meaning['元成果']))
        projection = HDSから目的要求(ir, materials, 前回成果=prior)
        if not projection.成立: return 会話応答('保留', 'この依頼はまだ解釈できません。' + projection.理由, projection.理由)
        plan = self._計画器.計画する(projection.要求)
        if not plan.成立: return 会話応答('保留', plan.理由, plan.理由)
        data, steps = deepcopy(plan.Data), list(plan.計画.工程)
        for sid, module, inputs, settings in (
            ('会話:意味', '会話回答意味', tuple(素材参照('工程', x) for x in plan.計画.出力工程),
             {'種別': '既存成果', '形式': style, '最大文字数': maximum}),
            ('会話:文章', '会話文章化', (素材参照('工程', '会話:意味'),), {})):
            data['指示:' + sid] = 能力結果(True, '採用前に意味と由来を保って回答を構成')
            data['設定:' + sid] = 能力結果(True, '', データ=settings)
            steps.append(合成工程(sid, (module,), '指示:' + sid, inputs, '設定:' + sid))
        prepared = self.統合.準備(合成計画(tuple(steps), ('会話:文章',)), data, 依頼文=ir.原文)
        if prepared.起点 != start: raise ValueError('解釈中に会話状態が変化')
        result = self.統合.実行(prepared, 停止要求=stop)
        if result.成立: self._前要求 = None
        return 会話応答(result.状態, result.本文 if result.成立 else '処理結果は未採用です。' + result.理由,
            result.理由, {'行為': '依頼', '経路': plan.作用経路, 'HDS原文': ir.原文}, result)

    def 応答(self, 原文, 資料=None, *, 外部読取許可=False, 停止要求=None, 形式='段落', 最大文字数=20000):
        if not self._ロック.acquire(blocking=False): return 会話応答('保留', '同じ会話を処理中です。')
        try:
            self.統合._停止(停止要求)
            if len(self._記録) >= self._上限: raise ValueError('会話記録上限。初期化又は新しいセッションが必要です')
            if type(原文) is not str or not 原文.strip() or len(原文) > 8192: raise ValueError('入力文の範囲外')
            if type(外部読取許可) is not bool or 外部読取許可 and not self._許可: raise ValueError('外部読取の権限範囲外')
            if 形式 not in ('段落', '箇条書き') or type(最大文字数) is not int or not 1 <= 最大文字数 <= 100000:
                raise ValueError('応答形式又は予算不正')
            materials = {} if 資料 is None else deepcopy(資料)
            if type(materials) is not dict or len(materials) > 32: raise ValueError('名前付き資料が必要')
            def material_check(rows):
                for name, value in rows.items():
                    if type(name) is not str or not name or len(name) > 128: raise ValueError('資料名不正')
                    _結果辞書(value)
                if len(rows) > 32 or len(_符号化({k: _結果辞書(v) for k, v in rows.items()})) > 1000000:
                    raise ValueError('資料容量上限')
            material_check(materials)
            start = self.統合.起点()
            ir = 公開HDSコンパイラ().コンパイル(原文)
            meaning = 会話を解釈(ir)
            event = {'原文': 原文, '資料名': tuple(materials), '状態': '', '行為': meaning.行為}
            # 実行前に保存予算を確保する。終了状態の文字列分も保守的に確保。
            if len(_符号化((*self._記録, event))) + 128 > 1000000: raise ValueError('会話記録容量上限')
            def finish(result):
                event['状態'] = result.状態
                self._記録 = (*self._記録, deepcopy(event))
                return result
            if self._保留 and self._保留['起点'] != start:
                self._保留 = None
                return finish(会話応答('保留', '会話状態が変化したため、古い確認待ちの要求は再実行しません。'))
            if meaning.行為 == '取消':
                self._保留 = None
                return finish(会話応答('取消', '確認待ちの要求を取り消しました。過去の成果は変更していません。'))
            request = meaning.要求
            if meaning.行為 in ('補充', '訂正', '再開'):
                saved = self._保留 if self._保留 else self._前要求 if meaning.行為 == '訂正' else None
                if saved is None: return finish(会話応答('保留', '補充又は再開する要求がありません。'))
                if saved['起点'] != start: return finish(会話応答('保留', '改訂対象の会話状態が古くなっています。'))
                request = saved['要求']
                if meaning.行為 == '補充' and getattr(request, meaning.項目) is not None:
                    return finish(会話応答('保留', '指定済みの条件を変える場合は「訂正：」を付けてください。'))
                if meaning.行為 != '再開': request = request.補充(meaning.項目, meaning.値)
                materials = {**deepcopy(saved['資料']), **materials}
                material_check(materials)
                origin = saved['原要求']
                style, maximum = saved['形式'], saved['最大文字数']
            else:
                origin, style, maximum = 原文, 形式, 最大文字数
                if request is not None and self._保留:
                    return finish(会話応答('確認', '未完了の要求があります。取り消してから別の要求を入力してください。'))
            if request is None:
                if self._保留 and meaning.既存候補:
                    return finish(会話応答('確認', '未完了の要求があります。補充・再開・取消を指定してください。'))
                if meaning.既存候補:
                    return finish(self._既存(ir, materials, start, 停止要求, style, maximum))
                return finish(会話応答('保留', meaning.理由 or 'この会話行為はまだ対応していません。', meaning.理由))
            saved = {'要求': request, '資料': deepcopy(materials), '起点': start, '原要求': origin,
                     '形式': style, '最大文字数': maximum}
            info = {'行為': meaning.行為, '要求': asdict(request), '原要求': origin, 'HDS原文': ir.原文}
            if request.単位 is None:
                self._保留 = saved
                return finish(会話応答('確認', '比較・照会に使う単位を指定してください。例：単位はVです', 情報=info))
            goal, inputs, settings = 会話目的を準備(request, materials, 形式=style, 最大文字数=maximum)
            result = self._監督.実行(goal, inputs, settings, origin,
                外部読取許可=外部読取許可, 停止要求=停止要求)
            info['試行'] = result.試行
            if result.成立:
                self._保留 = None
                self._前要求 = {**saved, '起点': self.統合.起点()}
                return finish(会話応答('合格', result.本文, 情報=info, 実行=result.実行))
            self._保留 = saved if result.状態 != '中止' else None
            detail = result.理由
            if result.失敗 and result.失敗.種類 == '資料不足':
                body = f'対象「{result.失敗.対象}」の資料が必要です。資料を追加して「再開して」と入力してください。'
                if not 外部読取許可: body += '外部検索は許可されていないため実行していません。'
                state = '確認'
            else:
                state, body = result.状態, '結果を採用していません。' + detail
            return finish(会話応答(state, body, detail, info, result.実行))
        except (ValueError, TypeError, KeyError, AttributeError, RecursionError, InterruptedError) as exc:
            return 会話応答('中止' if isinstance(exc, InterruptedError) else '保留', str(exc), str(exc))
        finally:
            self._ロック.release()

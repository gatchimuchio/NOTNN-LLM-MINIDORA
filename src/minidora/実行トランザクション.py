"""回復中の成功済み工程を監査可能な再開点として固定する実行トランザクション。

この境界は一つの会話実行監督.run内だけを扱う。成功が観測され監査できた工程だけを
再開固定し、失敗した工程又は回復対象内の工程は再実行へ残す。プロセス停止を跨ぐ
永続exactly-onceや外部副作用のcommit確認までは主張しない。
"""
from __future__ import annotations

from copy import deepcopy
from dataclasses import dataclass, replace

from .会話意味 import 意味指紋
from .能力合成 import 合成計画, 素材参照, _結果辞書
from .製品版.型 import 能力結果

実行トランザクション版 = 'MINIDORA-実行トランザクション-v0.1'


@dataclass(frozen=True, slots=True)
class 固定工程成果:
    目的鍵: str
    作用: str
    契約印: str
    結果: 能力結果
    出力印: str
    外部作用: bool = False
    由来工程: str = ''


@dataclass(frozen=True, slots=True)
class 実行トランザクション台帳:
    トランザクション印: str
    固定成果: tuple[固定工程成果, ...] = ()

    @property
    def 台帳印(self) -> str:
        return 意味指紋({
            '版': 実行トランザクション版,
            'トランザクション印': self.トランザクション印,
            '固定成果': tuple((x.目的鍵, x.作用, x.契約印, x.出力印,
                              x.外部作用, x.由来工程) for x in self.固定成果),
        })


@dataclass(frozen=True, slots=True)
class 再開投影:
    計画: 合成計画
    Data: dict[str, 能力結果]
    固定工程: tuple[str, ...] = ()
    固定目的: tuple[str, ...] = ()
    外部固定工程: tuple[str, ...] = ()
    再開印: str = ''


def _被覆地図(plan) -> dict[str, object]:
    rows = getattr(plan, '要求被覆', ())
    if type(rows) is not tuple:
        raise ValueError('要求被覆の型不正')
    out = {}
    for row in rows:
        key = getattr(row, '目的鍵', None)
        if type(key) is not str or not key or key in out:
            raise ValueError('要求被覆の目的鍵が不正')
        out[key] = row
    return out


def _工程地図(plan) -> tuple[dict[str, tuple[str, str]], dict[str, str]]:
    trace = getattr(plan, '工程作用', ())
    if type(trace) is not tuple:
        raise ValueError('工程作用の型不正')
    by_step = {}
    by_goal = {}
    for item in trace:
        if (type(item) is not tuple or len(item) != 3
                or any(type(x) is not str or not x for x in item)):
            raise ValueError('工程作用の要素不正')
        sid, goal, action = item
        if sid in by_step or goal in by_goal:
            raise ValueError('工程作用の重複')
        by_step[sid] = (goal, action)
        by_goal[goal] = sid
    return by_step, by_goal


def _結果印(value: 能力結果) -> str:
    return 意味指紋(_結果辞書(value))


def 台帳を更新(台帳: 実行トランザクション台帳, plan, response) -> 実行トランザクション台帳:
    """一試行で監査可能に合格した工程だけを次試行の固定候補へ追加する。"""
    if type(台帳) is not 実行トランザクション台帳:
        raise ValueError('実行トランザクション台帳型不正')
    run = getattr(response, '実行', None)
    if run is None:
        return 台帳
    rows = getattr(run, '中間結果', ())
    if type(rows) is not tuple:
        raise ValueError('実行中間結果の型不正')
    if not rows:
        return 台帳
    audit = getattr(run, '監査整合', None)
    if audit is not None:
        ok = audit()
        if type(ok) is not bool or not ok:
            raise ValueError('再開候補の実行監査が不成立')
    history = getattr(run, '履歴', ())
    if type(history) is not tuple:
        raise ValueError('実行履歴の型不正')
    by_step, _ = _工程地図(plan)
    coverage = _被覆地図(plan)
    external = set(getattr(plan, '外部作用', ()))
    if type(getattr(plan, '外部作用', ())) is not tuple:
        raise ValueError('外部作用の型不正')
    existing = {x.目的鍵: x for x in 台帳.固定成果}
    for sid, value in rows:
        if type(sid) is not str or sid not in by_step or not isinstance(value, 能力結果):
            raise ValueError('再開候補の工程又は結果が不正')
        goal, action = by_step[sid]
        row = coverage.get(goal)
        if row is None or getattr(row, '解決', '') != '作用' or getattr(row, '作用', '') != action:
            raise ValueError('再開候補と要求被覆が不一致')
        contract = getattr(row, '契約印', '')
        if type(contract) is not str or not contract:
            raise ValueError('再開候補の作用契約印がない')
        successful = [r for r in history if getattr(r, '工程', None) == sid and getattr(r, '状態', None) == '合格']
        if not successful:
            raise ValueError('中間結果に対応する合格実行記録がない')
        out_hash = _結果印(value)
        recorded = getattr(successful[-1], '出力ハッシュ', '')
        if recorded and recorded != out_hash:
            raise ValueError('中間結果と実行記録の出力印が不一致')
        existing[goal] = 固定工程成果(goal, action, contract, deepcopy(value), out_hash,
                                     sid in external, sid)
    ordered = tuple(existing[k] for k in sorted(existing))
    return 実行トランザクション台帳(台帳.トランザクション印, ordered)



def 台帳を失効(台帳: 実行トランザクション台帳, 目的群: set[str] | frozenset[str]) -> 実行トランザクション台帳:
    """再実行すると決めた目的の旧成功を、次の再開候補から明示的に外す。"""
    if type(台帳) is not 実行トランザクション台帳:
        raise ValueError('実行トランザクション台帳型不正')
    if type(目的群) not in (set, frozenset) or any(type(x) is not str or not x for x in 目的群):
        raise ValueError('失効目的の型不正')
    if not 目的群:
        return 台帳
    return 実行トランザクション台帳(
        台帳.トランザクション印,
        tuple(x for x in 台帳.固定成果 if x.目的鍵 not in 目的群),
    )

def 再開投影を作る(台帳: 実行トランザクション台帳, plan, *, 再実行目的: set[str] | frozenset[str]) -> 再開投影:
    """契約が同一で回復対象外の成功工程だけを入力へ固定し、実行工程から外す。"""
    if type(台帳) is not 実行トランザクション台帳:
        raise ValueError('実行トランザクション台帳型不正')
    if type(再実行目的) not in (set, frozenset) or any(type(x) is not str or not x for x in 再実行目的):
        raise ValueError('再実行目的の型不正')
    coverage = _被覆地図(plan)
    _, by_goal = _工程地図(plan)
    logical = getattr(plan, '計画', None)
    data = getattr(plan, 'Data', None)
    if not isinstance(logical, 合成計画) or type(data) is not dict:
        raise ValueError('再開投影の計画又はDataが不正')
    outputs = set(logical.出力工程)
    external = set(getattr(plan, '外部作用', ()))
    fixed_by_step: dict[str, 固定工程成果] = {}
    for saved in 台帳.固定成果:
        if saved.目的鍵 in 再実行目的:
            continue
        row = coverage.get(saved.目的鍵)
        sid = by_goal.get(saved.目的鍵)
        if row is None or sid is None or sid in outputs:
            continue
        if (getattr(row, '解決', '') != '作用'
                or getattr(row, '作用', '') != saved.作用
                or getattr(row, '契約印', '') != saved.契約印):
            continue
        if (sid in external) != saved.外部作用:
            raise ValueError('再開候補の外部作用区分が変わった')
        if _結果印(saved.結果) != saved.出力印:
            raise ValueError('再開台帳の固定成果が改変された')
        fixed_by_step[sid] = saved
    if not fixed_by_step:
        stamp = 意味指紋({'台帳': 台帳.台帳印, '再実行目的': tuple(sorted(再実行目的)), '固定': ()})
        return 再開投影(deepcopy(logical), deepcopy(data), 再開印=stamp)

    new_data = deepcopy(data)
    key_by_step = {}
    for n, sid in enumerate(sorted(fixed_by_step), 1):
        saved = fixed_by_step[sid]
        key = f'再開固定:{n:04d}:{saved.出力印[:12]}'
        if key in new_data:
            raise ValueError('再開固定Data識別子が衝突')
        new_data[key] = deepcopy(saved.結果)
        key_by_step[sid] = key

    rewritten = []
    for step in logical.工程:
        if step.識別子 in fixed_by_step:
            continue
        inputs = tuple(
            素材参照('入力', key_by_step[ref.識別子])
            if ref.領域 == '工程' and ref.識別子 in key_by_step else ref
            for ref in step.入力
        )
        rewritten.append(replace(step, 入力=inputs))
    if not rewritten:
        raise ValueError('再開投影で全工程を除去しない')
    by_id = {s.識別子: s for s in rewritten}
    if any(out not in by_id for out in logical.出力工程):
        raise ValueError('再開投影で出力工程を除去しない')
    # 固定した中間成果の下流入力はDataへ置換済みなので、その成果だけに
    # 寄与していた旧依存工程は再実行しない。出力から逆到達する工程だけ残す。
    reachable = set()
    stack = list(logical.出力工程)
    while stack:
        sid = stack.pop()
        if sid in reachable:
            continue
        step = by_id.get(sid)
        if step is None:
            raise ValueError('再開投影に未解決の工程参照が残った')
        reachable.add(sid)
        for ref in step.入力:
            if ref.領域 == '工程':
                stack.append(ref.識別子)
    new_steps = [s for s in rewritten if s.識別子 in reachable]
    remaining = {s.識別子 for s in new_steps}
    for step in new_steps:
        for ref in step.入力:
            if ref.領域 == '工程' and ref.識別子 not in remaining:
                raise ValueError('再開投影に未解決の工程参照が残った')
    fixed_steps = tuple(sorted(fixed_by_step))
    fixed_goals = tuple(sorted(x.目的鍵 for x in fixed_by_step.values()))
    fixed_external = tuple(sorted(sid for sid in fixed_steps if sid in external))
    stamp = 意味指紋({
        '台帳': 台帳.台帳印,
        '再実行目的': tuple(sorted(再実行目的)),
        '固定': tuple((sid, fixed_by_step[sid].目的鍵, fixed_by_step[sid].作用,
                      fixed_by_step[sid].契約印, fixed_by_step[sid].出力印)
                     for sid in fixed_steps),
    })
    return 再開投影(合成計画(tuple(new_steps), logical.出力工程), new_data,
                    fixed_steps, fixed_goals, fixed_external, stamp)

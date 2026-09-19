"""HDSの単一通常循環。独立監督・介入モード・第二の採否主体を設けない。"""
from __future__ import annotations
from dataclasses import replace, asdict
from copy import deepcopy
from .値 import 署名
from .政策 import HDS計装, HDS阻害, HDS作用失敗, 停止理由
from .認識 import 認識区分
from .観測 import 必要観測を構成
from .計画 import HDS作用仕様, 作用列を構成
from .形成 import 形成手順を再利用
from .依存 import HDS依存辺
from .状態更新 import 状態更新, 有効認識, ノード有効
from .意味構成 import 不足意味構成作用, 関係仮説構成作用, 自動分岐作用
from .自動記憶 import 自動記憶圧縮作用
from .自動形成 import 自動経験形成作用, 自動形成文脈
from .未来 import 未来列を構成
from .診断 import 例外を診断
from .一時適応 import HDS一時適応キャッシュ
from .作用 import 観測作用, 仮説形成作用, 仮説再照合作用, 枝合流作用, 草案検証作用


def _関連仕様(状態, 作用群, 追加要求=frozenset()):
    仕様 = [getattr(a, "計画仕様", None) for a in 作用群]
    仕様 = [s for s in 仕様 if isinstance(s, HDS作用仕様)]
    必要状態 = set(状態.要求状態) | set(追加要求)
    必要残差 = set(状態.残差)
    関連, 増加 = {}, True
    while 増加:
        増加 = False
        for s in 仕様:
            if s.作用ID not in 関連 and (s.追加状態 & 必要状態 or s.解消残差 & 必要残差):
                関連[s.作用ID] = s
                必要状態.update(s.入力状態)
                必要残差.update(s.追加残差)
                増加 = True
    return tuple(関連[k] for k in sorted(関連))


def 通常循環(主体, 初期状態, 前回=None):
    from ..HDS実行主体 import HDS実行状態, HDS実行結果, HDS作用記録, HDS作用機会, HDS作用結果, HDS作用状態, HDS終端
    if not isinstance(初期状態, HDS実行状態):
        raise TypeError("HDS実行状態が必要")
    現在 = deepcopy(初期状態)
    現在.状態署名
    履歴 = list(前回.履歴 if 前回 is not None else ())
    阻害履歴 = list(前回.阻害履歴 if 前回 is not None else ())
    統計 = asdict(前回.計装 if 前回 is not None else HDS計装())
    観測待ち = ()
    政策 = 主体.政策
    軟予算 = min(主体.最大作用回数, max(政策.初期作用予算, len(履歴)))
    生成署名 = set()
    計画署名 = set()
    最終検証済 = set()
    if 主体.最終検証器:
        契約署名 = 署名((現在.状態署名, tuple((v.ID, v.版) for v in 主体.最終検証器)))
        if any(h.作用ID == "内的/目的検証" and h.作用入力署名 == 契約署名
               and h.作用状態 == HDS作用状態.成立 and h.阻害 is None for h in 履歴):
            最終検証済.add(現在.状態署名)
    失敗入力 = {}
    for h in 履歴:
        if h.阻害:
            失敗入力[h.作用ID] = h.阻害
    使用済み = {(h.作用ID, h.作用入力署名) for h in 履歴}
    形成試行済 = False
    圧縮作用 = 自動記憶圧縮作用(政策.圧縮開始文字数, 政策.圧縮最大文字数)
    一時適応 = HDS一時適応キャッシュ(min(256, 政策.最大内部生成))

    def 終了(終端, 種別, 旧理由):
        return HDS実行結果(終端, 現在, tuple(履歴), tuple(旧理由), 種別, HDS計装(**統計), 観測待ち, tuple(阻害履歴), 前回.入力履歴 if 前回 is not None else ())

    def 契約失敗(対象, 例外):
        阻害履歴.append(HDS阻害(停止理由.契約違反, 対象, f"{type(例外).__name__}: {例外}"))
        return 終了(HDS終端.失敗, 停止理由.契約違反, ("HDS_CONTRACT_VIOLATION",))

    def 記録する(機会, 結果, 計画=(), 未来=()):
        nonlocal 現在
        前 = 現在
        読取 = {"認識:" + k for k in (*機会.読取認識, *機会.未確定読取)} | {"成果:" + k for k in 機会.読取成果} | {"状態:" + k for k in 機会.入力状態}
        産出 = {"認識:" + x.ID for x in 結果.認識更新} | {"仮説:" + x.ID for x in 結果.仮説更新} | {"成果:" + k for k, _ in 結果.成果} | {"状態:" + k for k in 結果.追加状態}
        更新例外 = None
        try:
            証明 = dict(結果.検証依存)
            for k in 読取:
                現署名 = 前.ノード署名(k)
                if k in 証明 and 証明[k] != 現署名:
                    raise ValueError("作用結果の読取証明が現在入力と不一致")
                証明[k] = 現署名
            辺 = set(結果.依存追加)
            if 結果.状態 == HDS作用状態.成立:
                # 同一作用内でread-modify-writeしたノードは、旧版の読取値を
                # 同時産出物の親へ自動依存として残さない。残すと作用自身の
                # 更新直後に出力状態が旧入力依存として失効し、後続再評価より
                # 同じ作用の再実行が先行する。読取証明は前状態署名として保持し、
                # 後続作用は更新後ノード署名から依存を形成する。
                原子的更新ノード = 読取 & 産出
                自動依存元 = 読取 - 原子的更新ノード
                辺 |= {HDS依存辺(a, b) for a in 自動依存元 for b in 産出 if a != b}
            結果 = replace(結果, 依存追加=tuple(sorted(辺)), 検証依存=tuple(sorted(証明.items())))
            現在, 差 = 状態更新(前, 結果)
        except Exception as exc:
            更新例外 = exc
            結果 = HDS作用結果(HDS作用状態.失敗, 停止要求=True,
                               理由=(f"{type(exc).__name__}: {exc}",),
                               阻害=HDS阻害(停止理由.契約違反, 機会.作用ID, str(exc)))
            現在, 差 = 状態更新(前, 結果)
        消費 = tuple(sorted(set(機会.読取認識) | set(機会.未確定読取)))
        行 = HDS作用記録(len(履歴) + 1, 機会.作用ID, 機会.作用入力署名, 結果.状態,
                          前.状態署名, 現在.状態署名, 差,
                          tuple(sorted(前.残差 & 機会.解消対象)), tuple(sorted(前.未達状態 & 機会.出力状態)),
                          結果.理由, 消費, 機会.資源負荷, 結果.阻害, tuple(計画), tuple(未来), 結果.診断)
        直前変化 = set(履歴[-1].状態差.影響対象) if 履歴 else set()
        履歴.append(行)
        一時適応.結果を受け取る(機会, 結果, 差)
        使用済み.add((機会.作用ID, 機会.作用入力署名))
        統計["作用実行数"] += 1
        統計["消費資源"] += 機会.資源負荷
        統計["状態差発生数"] += int(差.変化有無)
        統計["後続消費数"] += len(直前変化 & 読取)
        統計["依存失効数"] += len(差.失効対象)
        if 機会.種別 == "観測":
            統計["観測実行数"] += 1
        if 機会.種別 == "大域再照合":
            統計["大域再照合数"] += 1
        if 結果.診断:
            統計["失敗診断数"] += 1
        for 種, 名 in (("意味構成", "意味構成数"), ("仮説形成", "仮説生成数"), ("枝生成", "枝生成数"), ("記憶圧縮", "圧縮数")):
            if 機会.種別 == 種:
                統計[名] += 1
        if 未来:
            統計["未来監査数"] += 1
        if 結果.阻害:
            阻害履歴.append(結果.阻害)
            失敗入力[機会.作用ID] = 結果.阻害
            if 結果.阻害.種別 == 停止理由.検証不成立:
                統計["検証失敗数"] += 1
        elif 結果.状態 == HDS作用状態.成立:
            失敗入力.pop(機会.作用ID, None)
        if 更新例外 is not None:
            raise 更新例外
        return 行

    while True:
        # 停止と供給も同じ通常循環の境界。上位の第二実行主体は置かない。
        try:
            if 主体.停止要求 is not None:
                停止 = 主体.停止要求()
                if type(停止) is not bool:
                    raise TypeError("停止要求はboolを返す必要がある")
                if 停止:
                    return 終了(HDS終端.保留, 停止理由.明示停止, ("HDS_USER_CANCELLED",))
            供給 = []
            for 供給器 in 主体.作用供給器:
                写し = deepcopy(現在)
                前署名 = 写し.状態署名
                候補 = 供給器.構成(写し)
                if 写し.状態署名 != 前署名:
                    raise ValueError("作用供給器が状態を変更した")
                if type(候補) is not tuple:
                    raise TypeError("作用供給器の返却はtupleが必要")
                if len(供給) + len(候補) > 政策.最大内部生成:
                    return 終了(HDS終端.保留, 停止理由.予算枯渇, ("HDS_SUPPLY_CAPACITY_EXHAUSTED",))
                for a in 候補:
                    if (not isinstance(getattr(a, "作用ID", None), str) or not a.作用ID.strip()
                            or a.作用ID.startswith("内的/")
                            or not callable(getattr(a, "機会", None))
                            or not callable(getattr(a, "実行", None))):
                        raise ValueError("供給作用の契約不正")
                供給.extend(候補)
            利用作用群 = (*主体.作用群, *供給)
            if len({a.作用ID for a in 利用作用群}) != len(利用作用群):
                raise ValueError("供給作用IDの重複")
        except Exception as exc:
            return 契約失敗("作用供給・停止境界", exc)
        if any(c.違反(現在.成立状態) for c in 主体.未来制約):
            阻害履歴.append(HDS阻害(停止理由.契約違反, "状態制約", "現在状態が明示不変条件に違反"))
            return 終了(HDS終端.失敗, 停止理由.契約違反, ("HDS_STATE_INVARIANT_VIOLATION",))
        if 現在.閉包済み:
            圧縮機会 = 圧縮作用.機会(現在)
            if 圧縮機会 is not None and (圧縮機会.作用ID, 圧縮機会.作用入力署名) not in 使用済み:
                if len(履歴) < 主体.最大作用回数 and 統計["消費資源"] + 圧縮機会.資源負荷 <= 政策.最大資源:
                    記録する(圧縮機会, 圧縮作用.実行(deepcopy(現在)))
                    continue
            if not 主体.最終検証器 or 現在.状態署名 in 最終検証済:
                if 政策.自動形成 and not 形成試行済 and 前回 is None:
                    形成試行済 = True
                    形成 = 自動経験形成作用(初期状態, tuple(履歴), 利用作用群, 主体.最終検証器)
                    機会 = 形成.機会(現在)
                    if 機会 is not None and len(履歴) < 主体.最大作用回数 and 統計["消費資源"] + 機会.資源負荷 <= 政策.最大資源:
                        記録する(機会, 形成.実行(deepcopy(現在)))
                        統計["自動形成数"] += 1
                        統計["再現作用数"] += 形成.再現回数
                        統計["形成再検証数"] += int(形成.再現成功)
                        continue
                return 終了(HDS終端.採用, 停止理由.目的達成, ("HDS_GOAL_CLOSED",))
            if len(履歴) >= 主体.最大作用回数 or 統計["消費資源"] + 1 > 政策.最大資源:
                return 終了(HDS終端.保留, 停止理由.予算枯渇, ("HDS_FINAL_VALIDATION_BUDGET_EXHAUSTED",))
            前署名 = 現在.状態署名
            機会 = HDS作用機会("内的/目的検証", 署名((前署名, tuple((v.ID, v.版) for v in 主体.最終検証器))), 種別="目的検証")
            if (機会.作用ID, 機会.作用入力署名) in 使用済み:
                return 終了(HDS終端.保留, 停止理由.検証不成立, ("HDS_FINAL_VALIDATION_REPEATED",))
            検証失敗 = []
            try:
                for v in 主体.最終検証器:
                    写し = deepcopy(現在)
                    合格 = v.検証(写し, None)
                    if type(合格) is not bool or 写し.状態署名 != 前署名:
                        raise ValueError("最終検証器の契約違反")
                    if not 合格:
                        検証失敗.append(v.ID)
            except Exception as exc:
                記録する(機会, HDS作用結果(HDS作用状態.失敗, 停止要求=True,
                    理由=(f"{type(exc).__name__}: {exc}",),
                    阻害=HDS阻害(停止理由.契約違反, 機会.作用ID, str(exc) or type(exc).__name__)))
                return 契約失敗("内的/目的検証", exc)
            結果 = HDS作用結果(HDS作用状態.成立,
                               追加残差=frozenset("検証:" + k for k in 検証失敗),
                               理由=("目的契約検証",),
                               阻害=HDS阻害(停止理由.検証不成立, "内的/目的検証", ",".join(検証失敗), True) if 検証失敗 else None)
            記録する(機会, 結果)
            if not 検証失敗:
                最終検証済.add(現在.状態署名)
            continue

        if len(履歴) >= 主体.最大作用回数 or 統計["消費資源"] >= 政策.最大資源:
            return 終了(HDS終端.保留, 停止理由.予算枯渇, ("HDS_ACTION_BUDGET_EXHAUSTED",))
        if len(履歴) >= 軟予算:
            if any(x.状態差.変化有無 for x in 履歴[-政策.予算増分:]):
                軟予算 = min(主体.最大作用回数, 軟予算 + 政策.予算増分)
                統計["予算拡張数"] += 1
            else:
                return 終了(HDS終端.保留, 停止理由.無進展, ("HDS_NO_EVIDENCE_FOR_EFFORT_INCREASE",))

        修復状態 = frozenset(k for b in 失敗入力.values() if b.修復可能 for k in b.必要状態)
        関連仕様 = _関連仕様(現在, 利用作用群, 修復状態)
        必要認識 = 現在.要求認識 | frozenset(k for s in 関連仕様 for k in s.読取認識)
        必要認識 |= frozenset(k for b in 失敗入力.values() if b.修復可能 for k in b.必要認識)
        待ち = list(必要認識)
        while 待ち:
            x = 現在.認識辞書().get(待ち.pop())
            for k in x.依存 if x is not None else ():
                if k not in 必要認識:
                    必要認識 = 必要認識 | {k}
                    待ち.append(k)
        try:
            観測用認識 = tuple(replace(x, 区分=認識区分.失効) if x.区分 == 認識区分.確定 and not 有効認識(現在, x.ID) else x for x in 現在.認識)
            観測待ち = 必要観測を構成(観測用認識, 必要認識, 現在.仮説, 現在.観測要求, 最大件数=政策.最大観測要求)
        except ValueError as exc:
            阻害履歴.append(HDS阻害(停止理由.予算枯渇, "観測構成", str(exc)))
            return 終了(HDS終端.保留, 停止理由.予算枯渇, ("HDS_OBSERVATION_CAPACITY_EXHAUSTED",))
        内的 = [観測作用(r, p, 政策.参照再利用回数) for r in 観測待ち for p in 主体.観測器 if p.手段 in r.手段]
        内的.append(不足意味構成作用())
        if 主体.関係規則:
            内的.append(関係仮説構成作用(主体.関係規則, 政策.最大内部生成))
        内的.append(自動分岐作用())
        内的.append(圧縮作用)
        内的.extend(仮説形成作用(t) for t in 主体.仮説雛型)
        内的.append(枝合流作用())
        内的.extend(草案検証作用(d.ID, 主体.検証器) for d in 現在.草案 if d.区分 in ("未検証", "失効"))
        差による再照合 = bool(履歴 and (履歴[-1].状態差.認識差 or 履歴[-1].状態差.変更依存))
        if len(履歴) % 政策.大域間隔 == 0 or 差による再照合 or any(x.区分 == 認識区分.競合 for x in 現在.認識):
            内的.append(仮説再照合作用())
        全作用 = tuple(利用作用群) + tuple(内的)
        ID別 = {}
        全機会 = {}
        選択可能 = []
        制約除外 = []
        資源除外 = False
        依存除外 = False
        try:
            for a in 全作用:
                if a.作用ID in ID別:
                    raise ValueError("動的生成作用IDの重複: " + a.作用ID)
                ID別[a.作用ID] = a
                写し = deepcopy(現在)
                写し署名 = 写し.状態署名
                o = a.機会(写し)
                if 写し.状態署名 != 写し署名:
                    raise ValueError("機会観測が主体状態を書換えた")
                if o is None:
                    continue
                if not isinstance(o, HDS作用機会) or o.作用ID != a.作用ID:
                    raise ValueError("作用機会の型/ID契約違反")
                o = 一時適応.機会を補正(o)
                spec = getattr(a, "計画仕様", None)
                権限 = tuple(sorted(set(o.必要権限) | (set(spec.必要権限) if isinstance(spec, HDS作用仕様) else set())))
                過去阻害 = 失敗入力.get(a.作用ID)
                修復入力 = tuple(過去阻害.必要状態) if 過去阻害 and 過去阻害.修復可能 else ()
                修復認識 = tuple(過去阻害.必要認識) if 過去阻害 and 過去阻害.修復可能 else ()
                読取認識 = tuple(sorted(set(o.読取認識) | set(修復認識)))
                入力状態 = o.入力状態 | frozenset(修復入力)
                入力 = (o.作用入力署名, o.契約版,
                        tuple((k, 現在.ノード署名("認識:" + k)) for k in (*読取認識, *o.未確定読取)),
                        tuple((k, 現在.ノード署名("成果:" + k)) for k in o.読取成果),
                        tuple((k, 現在.ノード署名("状態:" + k)) for k in sorted(入力状態)))
                o = replace(o, 作用入力署名=署名(入力), 必要権限=権限, 読取認識=読取認識, 入力状態=入力状態)
                全機会[o.作用ID] = o
                if o.作用ID.startswith("内的/"):
                    鍵 = (o.作用ID, o.作用入力署名)
                    if 鍵 not in 生成署名:
                        生成署名.add(鍵)
                        統計["生成件数"] += 1
                制約 = 政策.許可判定(o.作用ID, o.必要権限)
                if 制約:
                    制約除外.append((o, 制約))
                    continue
                if not o.状態変更可能 or (o.作用ID, o.作用入力署名) in 使用済み:
                    continue
                if not o.入力状態 <= 現在.成立状態 or any(not 有効認識(現在, k) for k in o.読取認識) or any(not ノード有効(現在, "成果:" + k) for k in o.読取成果):
                    依存除外 = True
                    continue
                if o.資源負荷 > 政策.最大資源 - 統計["消費資源"]:
                    資源除外 = True
                    continue
                if isinstance(spec, HDS作用仕様) and 主体.未来制約:
                    projected = (現在.成立状態 - spec.削除状態) | spec.追加状態
                    if any(c.違反(projected) for c in 主体.未来制約):
                        制約除外.append((o, 停止理由.検証不成立))
                        continue
                選択可能.append(o)
        except Exception as exc:
            return 契約失敗("作用機会観測", exc)
        統計["制約除外数"] += len(制約除外)
        if len(生成署名) > 政策.最大内部生成:
            return 終了(HDS終端.保留, 停止理由.予算枯渇, ("HDS_INTERNAL_CONSTRUCTION_BUDGET_EXHAUSTED",))

        計画 = None
        可用ID = {o.作用ID for o in 選択可能}
        残探索 = 政策.最大探索状態 - 統計["探索状態数"]
        if 関連仕様 and 残探索 > 0:
            計画用 = []
            for s in 関連仕様:
                if 政策.許可判定(s.作用ID, s.必要権限) or any(not 有効認識(現在, k) for k in s.読取認識):
                    continue
                o = 全機会.get(s.作用ID)
                if o is None:
                    continue
                if (o.作用ID, o.作用入力署名) in 使用済み:
                    continue
                if 政策.許可判定(o.作用ID, o.必要権限):
                    continue
                計画用.append(replace(s, 入力状態=o.入力状態, 読取認識=o.読取認識, 必要権限=o.必要権限))
            文脈 = 自動形成文脈(現在, 利用作用群)
            for 関係 in 現在.形成関係:
                計画 = 形成手順を再利用(関係, 現在.成立状態, 現在.残差, 現在.要求状態 | 修復状態,
                                     tuple(計画用), 文脈, 政策.最大資源 - 統計["消費資源"])
                if 計画 is not None and any(x.制約違反 for x in 未来列を構成(現在.成立状態, 現在.残差, 計画.作用列, tuple(計画用), 主体.未来制約)):
                    計画 = None
                if 計画 is not None:
                    統計["形成再利用数"] += 1
                    break
            if 計画 is None:
                計画 = 作用列を構成(現在.成立状態, 現在.残差, 現在.要求状態 | 修復状態,
                                  tuple(計画用), 最大深さ=政策.探索深さ, 最大状態数=残探索,
                                  最大資源=政策.最大資源 - 統計["消費資源"], 制約群=主体.未来制約)
            統計["探索状態数"] += 計画.探索状態数
            if 計画.成立:
                鍵 = 署名((現在.状態署名, 計画.作用列))
                if 鍵 not in 計画署名:
                    計画署名.add(鍵)
                    統計["動的計画数"] += 1
        try:
            if 計画 is not None and 計画.成立 and 計画.作用列[0] in 可用ID:
                選択 = next(o for o in 選択可能 if o.作用ID == 計画.作用列[0])
            else:
                選択用状態 = deepcopy(現在)
                選択用署名 = 選択用状態.状態署名
                選択 = 主体.作用選択器.選択(選択用状態, tuple(選択可能), tuple(履歴))
                if 選択用状態.状態署名 != 選択用署名:
                    raise ValueError("作用選択器が主体状態を変更した")
            if 選択 is not None and 選択 not in 選択可能:
                raise ValueError("作用選択器が許可済み候補外を選択した")
        except Exception as exc:
            return 契約失敗("作用選択", exc)
        if 選択 is None:
            if 資源除外:
                種別 = 停止理由.予算枯渇
            elif 制約除外:
                種別 = 制約除外[0][1]
            elif any(x.区分 == 認識区分.競合 for x in 現在.認識 if x.ID in 必要認識):
                種別 = 停止理由.証拠競合
            elif 観測待ち:
                種別 = 停止理由.観測不足
            elif any(d.区分 in ("未検証", "失効") and any(現在.ノード署名(k) != sig for k, sig in d.依存署名) for d in 現在.草案):
                種別 = 停止理由.依存未閉包
            elif 依存除外 or 現在.再評価待ち or 必要認識:
                種別 = 停止理由.依存未閉包
            elif 失敗入力:
                種別 = list(失敗入力.values())[-1].種別
            elif 計画 is not None and 計画.打切り:
                種別 = 停止理由.予算枯渇
            else:
                種別 = 停止理由.作用不足
            return 終了(HDS終端.保留, 種別, ("HDS_NO_PRODUCTIVE_ACTION",))

        if 失敗入力 and (選択.作用ID not in 失敗入力 or 選択.入力状態 or 選択.読取認識):
            統計["修復選択数"] += 1
        前 = deepcopy(現在)
        前署名 = 前.状態署名
        try:
            結果 = ID別[選択.作用ID].実行(前)
            if 前.状態署名 != 前署名:
                raise ValueError("作用器が受け取った主体状態を直接変更した")
            if not isinstance(結果, HDS作用結果):
                raise TypeError("作用結果契約違反")
        except HDS作用失敗 as exc:
            結果 = HDS作用結果(HDS作用状態.保留 if exc.阻害.修復可能 else HDS作用状態.失敗,
                               理由=(exc.阻害.詳細,), 阻害=exc.阻害,
                               停止要求=not exc.阻害.修復可能)
        except Exception as exc:
            診断, 阻害 = 例外を診断(exc, ID別[選択.作用ID], 選択, 現在)
            結果 = HDS作用結果(HDS作用状態.保留 if 阻害.修復可能 else HDS作用状態.失敗,
                               理由=(診断.観測記述,), 停止要求=not 阻害.修復可能,
                               阻害=阻害, 診断=診断)
        try:
            planned = 計画.作用列 if 計画 is not None and 計画.成立 and 選択.作用ID == 計画.作用列[0] else ()
            specs = tuple(getattr(a, "計画仕様") for a in 利用作用群 if isinstance(getattr(a, "計画仕様", None), HDS作用仕様))
            未来 = 未来列を構成(現在.成立状態, 現在.残差, planned, specs, 主体.未来制約) if planned else ()
            記録する(選択, 結果, planned, 未来)
        except Exception as exc:
            return 契約失敗(選択.作用ID, exc)
        if 結果.停止要求:
            種別 = 結果.阻害.種別 if 結果.阻害 else 停止理由.明示停止
            return 終了(HDS終端.失敗 if 結果.状態 == HDS作用状態.失敗 else HDS終端.保留, 種別,
                      tuple(dict.fromkeys(("HDS_ACTION_REQUESTED_STOP", *結果.理由))))

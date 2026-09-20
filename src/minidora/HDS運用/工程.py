"""合成計画の各工程を、同じHDS通常循環の作用候補として供給する。"""
from __future__ import annotations
from copy import deepcopy
from dataclasses import asdict
import math
from ..HDS実行主体 import HDS関数作用, HDS作用結果, HDS作用状態
from ..統合駆動_v2.政策 import HDS阻害, 停止理由
from ..能力合成 import _結果辞書, _参照結合
from ..製品版.能力契約 import 能力文脈
from ..製品版.型 import 能力結果
from ..採否 import 実行状態
from ..会話回答 import 回答を構成, 回答記録整合
from ..監査改善接続 import 改善回答を検査
from ..実行回復 import 回復方針を決定, 失敗を分類
from ..コア.内容計画 import 内容計画を構成, 内容計画を検査, 内容計画を表現
from .値 import 指紋, 正準, 結果を保存, 結果を復元, 計画を復元, 運用版
from .解釈 import 計画を構成
from .数量生成 import 数量回答を検査
from .内容構成 import 資料文章を検査
from .関係内容 import 関係回答を検査

計画接頭辞 = "運用計画:"


def 現行計画(状態):
    records = dict(状態.成果)
    names = [k for k in records if k.startswith(計画接頭辞) and "/" not in k]
    if not names:
        return None
    key = max(names, key=lambda k: int(k.split(":")[-1]))
    return key, records[key]


def _工程鍵(plan_key, sid):
    return plan_key + "/成果/" + sid


def _済(plan_key, sid):
    return plan_key + "/成立/" + sid


def _試行鍵(plan_key, sid, index):
    return plan_key + "/試行/" + sid + "/" + str(index)


def 最終素材を構成(results, packet):
    if len(results) == 1:
        item = results[0]
        if packet["回答種別"] != "能力成果" or 回答記録整合(item) or 改善回答を検査(item.データ):
            return item
    return 回答を構成(results)


def 入力依存を収集(packet, inputs, 結果参照=()):
    """出力の祖先工程が読む資料を追跡する。能力が参照を返し忘れても消さない。"""
    plan = 計画を復元(packet["計画"])
    steps = {step.識別子: step for step in plan.工程}
    seen, needed, queue = set(), set(), list(plan.出力工程)
    while queue:
        sid = queue.pop()
        if sid in seen:
            continue
        seen.add(sid)
        step = steps[sid]
        needed.add(step.指示参照)
        if step.設定参照:
            needed.add(step.設定参照)
        for ref in step.入力:
            if ref.領域 == "工程":
                queue.append(ref.識別子)
            else:
                needed.add(ref.識別子)
    refs = {ref.識別子 for key in needed
            for ref in 結果を復元(packet["資料"][key]).参照}
    refs.update(参照.識別子 for 参照 in 結果参照)
    dependencies = {name: 元資料["版"] for name, 元資料 in inputs["資料"].items()
                    if any(ref.識別子 in refs for ref in 結果を復元(元資料["結果"]).参照)}
    interpretation = packet.get("解釈", {})
    if interpretation.get("方式") == "継続":
        interpretation = interpretation["目的"]
    if (interpretation.get("方式") in ("数量再表現", "一般再表現", "関係再表現") or (interpretation.get("方式") == "会話"
            and interpretation.get("依頼", {}).get("行為") == "再表現")):
        dependencies.update(inputs.get("前回依存", {}))
    return dependencies


def _部分木(coverage, root):
    rows = {row["目的鍵"]: row for row in coverage}
    seen, queue = set(), [root]
    while queue:
        key = queue.pop()
        if key in seen:
            continue
        if key not in rows:
            raise ValueError("再計画の被覆が閉じていない")
        seen.add(key)
        row = rows[key]
        if row["解決"] == "作用":
            queue.extend(pair[1] for pair in row["入力役割"])
    return rows, seen


def _局所変更を検査(old, new, policy):
    old_rows, old_tree = _部分木(old["被覆"], policy.対象目的)
    new_rows, new_tree = _部分木(new["被覆"], policy.対象目的)
    if {k: v for k, v in old_rows.items() if k not in old_tree} != {k: v for k, v in new_rows.items() if k not in new_tree}:
        raise ValueError("回復対象外の目的・役割が変化した")
    if old["役割"]["目的"] != new["役割"]["目的"] or old["目録"] != new["目録"]:
        raise ValueError("回復中の目的又は作用契約の変更")


class 工程供給:
    def __init__(self, 目録, *, 最大回復=4, 最大結果バイト=2_000_000):
        self.目録 = 目録
        self.最大回復 = 最大回復
        self.最大結果バイト = 最大結果バイト

    def _文脈(self, 状態, plan_key, packet, step):
        values = dict(状態.成果)
        materials = {k: 結果を復元(v) for k, v in packet["資料"].items()}
        sources = []
        for ref in step.入力:
            value = materials[ref.識別子] if ref.領域 == "入力" else 結果を復元(values[_工程鍵(plan_key, ref.識別子)])
            if not value.成立:
                raise ValueError("不成立の上流結果")
            sources.append((ref, value))
        references = _参照結合(r for _, value in sources for r in value.参照)
        auxiliary = {"合成入力": tuple({"参照": asdict(ref), "結果": _結果辞書(value)} for ref, value in sources),
                     "合成設定": deepcopy(materials[step.設定参照].データ) if step.設定参照 else {}}
        return 能力文脈(materials[step.指示参照].本文, values["運用入力"]["セッションID"],
                        "\n\n".join(value.本文 for _, value in sources), references, (), auxiliary)

    def __call__(self, 状態):
        self.目録.照合()
        current = 現行計画(状態)
        if current is None:
            return ()
        plan_key, packet = current
        if packet["方式"] == "管理":
            return ()
        if packet["目録"] != self.目録.ハッシュ:
            raise ValueError("計画と能力目録の版不一致")
        plan = 計画を復元(packet["計画"])
        values = dict(状態.成果)
        actions = []
        for step in plan.工程:
            inputs = ("運用:計画構成済", *(_済(plan_key, ref.識別子) for ref in step.入力 if ref.領域 == "工程"))
            reads = (plan_key, *(_工程鍵(plan_key, ref.識別子) for ref in step.入力 if ref.領域 == "工程"))
            for index, name in enumerate(step.能力候補):
                record_key = _試行鍵(plan_key, step.識別子, index)
                作用識別子 = "運用能力/" + str(plan_key) + "/" + step.識別子 + "/" + name
                registration = self.目録.取得(name)
                boundary = self.目録.境界契約(name)
                def eligible(s, key=record_key, st=step, number=index):
                    current_values = dict(s.成果)
                    return (key not in current_values and _済(plan_key, st.識別子) not in s.成立状態
                            and (number == 0 or _試行鍵(plan_key, st.識別子, number - 1) in current_values))
                def execute(s, st=step, ability=name, number=index, key=record_key, boundary=boundary):
                    self.目録.照合()
                    ctx = self._文脈(s, plan_key, packet, st)
                    モジュール = self.目録.取得(ability).モジュール
                    before = 指紋(_結果辞書(能力結果(True, "", データ=正準({"文脈": {
                        "入力": ctx.入力文, "補助": ctx.補助, "参照": [r.辞書化() for r in ctx.直前参照]}}))))
                    try:
                        score = モジュール.判定(deepcopy(ctx))
                        if type(score) not in (int, float) or not math.isfinite(score) or not 0 <= score <= 1:
                            raise ValueError("能力の適用判定は有限な0..1の数値が必要")
                        cache_key = self.目録.再利用鍵(ability, ctx)
                        cache = self.目録.再利用庫
                        cache.計数(ability, "要求")
                        結果 = cache.取得(cache_key) if cache_key is not None and score > 0 else None
                        reused = 結果 is not None
                        if reused:
                            cache.計数(ability, "再利用")
                        elif score > 0:
                            cache.計数(ability, "原実行")
                            結果 = モジュール.実行(deepcopy(ctx))
                        else:
                            結果 = 能力結果(False, "", 保留理由="能力の適用条件を満たさない", 採否状態=実行状態.非適用)
                        self.目録.照合()
                        packed = 結果を保存(結果)
                        from ..能力合成 import _符号化
                        if len(_符号化(packed)) > self.最大結果バイト:
                            raise ValueError("能力結果の保存上限。切断せず停止")
                        if (結果.成立 and 結果.本文 and boundary is not None
                                and "C8" in boundary.関連コア責任ID):
                            # 局所部品が既に生成した明示本文だけを共通内容契約へ載せる。
                            # 構造化中間結果に表面文章を強制せず、語彙・文法・専門説明方式もコアへ移さない。
                            plan = 内容計画を構成(
                                結果.本文, 種別=ability, 根拠=tuple(結果.根拠),
                                由来=tuple("参照:" + x.識別子 for x in 結果.参照),
                            )
                            if not 内容計画を検査(plan) or 内容計画を表現(plan) != 結果.本文:
                                raise ValueError("能力結果の内容計画境界が不整合")
                        record = {"能力": ability, "版": モジュール.版, "工程": st.識別子,
                                  "入力印": before, "出力印": 指紋(packed), "採否": 結果.状態.value,
                                  "再利用": reused, "理由": 結果.保留理由}
                        if 結果.成立:
                            if cache_key is not None and not reused:
                                cache.保存(cache_key, 結果)
                            return HDS作用結果(HDS作用状態.成立,
                                追加状態=frozenset({_済(plan_key, st.識別子)}),
                                成果=((_工程鍵(plan_key, st.識別子), packed), (key, record)),
                                理由=("能力成果をHDSへ帰還", ability, "純粋結果再利用" if reused else "能力実行"))
                        return HDS作用結果(HDS作用状態.保留, 成果=((key, record),), 理由=(結果.保留理由,))
                    except Exception as exc:
                        # 契約違反を不適用や成功に縮退させない。
                        return HDS作用結果(HDS作用状態.失敗, 停止要求=True,
                            成果=((key, {"能力": ability, "工程": st.識別子, "理由": str(exc), "例外": type(exc).__name__}),),
                            理由=("能力実行契約違反", type(exc).__name__, str(exc)),
                            阻害=HDS阻害(停止理由.契約違反, ability, str(exc) or type(exc).__name__))
                def 意味入力署名関数(s, st=step, ability=name):
                    return self.目録.意味入力署名(ability, self._文脈(s, plan_key, packet, st))
                actions.append(HDS関数作用(作用識別子, execute, 入力状態=inputs,
                    出力状態=(_済(plan_key, step.識別子),), 読取成果=tuple(dict.fromkeys(reads)),
                    機会判定=eligible, 必要権限=("外部読取",) if registration.外部読取 else (),
                    優先度=1.0 - index / 1000, 契約版=registration.モジュール.版,
                    作用定義ID="運用能力/" + name, 意味入力署名=意味入力署名関数))
        recovery = self._回復作用(状態, plan_key, packet, plan)
        if recovery is not None:
            actions.append(recovery)
        outputs = tuple(_工程鍵(plan_key, sid) for sid in plan.出力工程)
        def answer(s):
            データ = dict(s.成果)
            results = tuple(結果を復元(データ[key]) for key in outputs)
            final = 最終素材を構成(results, packet)
            対応証拠 = {"原文": データ["運用入力"]["原文"], "計画鍵": plan_key, "計画印": 指紋(packet),
                        "目録": self.目録.ハッシュ, "出力": list(outputs),
                        "出力印": [指紋(データ[key]) for key in outputs], "回答印": 指紋(結果を保存(final)),
                        "資料依存": 入力依存を収集(packet, データ["運用入力"], final.参照)}
            return HDS作用結果(HDS作用状態.成立, 追加状態=frozenset({"運用:応答成立"}),
                               解消残差=frozenset({"運用:成果未構成"}),
                               成果=(("運用応答", 結果を保存(final)), ("運用採用対応", 対応証拠)),
                               理由=("要求に対応する全出力から応答構成",))
        actions.append(HDS関数作用("運用/成果構成/" + plan_key, answer,
            入力状態=tuple(_済(plan_key, sid) for sid in plan.出力工程), 出力状態=("運用:応答成立",),
            解消対象=("運用:成果未構成",), 読取成果=("運用入力", plan_key, *outputs), 契約版=運用版,
            作用定義ID="運用/成果構成"))
        return tuple(actions)

    def _回復作用(self, 状態, plan_key, packet, plan):
        if not packet["役割"] or int(plan_key.split(":")[-1]) >= self.最大回復:
            return None
        データ = dict(状態.成果)
        info = {sid: (goal, 行為) for sid, goal, 行為 in packet["役割"]["工程作用"]}
        rules = {r.識別子: r for r in self.目録.役割作用}
        for step in plan.工程:
            failure_key = _試行鍵(plan_key, step.識別子, len(step.能力候補) - 1)
            if _済(plan_key, step.識別子) in 状態.成立状態 or failure_key not in データ or step.識別子 not in info:
                continue
            failure = データ[failure_key]
            pieces = failure.get("理由", "").split(":", 2)
            category = pieces[1] if len(pieces) == 3 and pieces[0] == "会話失敗" else "能力不成立"
            goal, 行為 = info[step.識別子]
            rule = rules[行為]
            matched = next((r for r in rule.回復 if r.失敗種別 == category), None)
            if matched is None or matched.動作() == "同一作用再試行":
                continue
            reopen = (goal, 行為) if matched.対象 == "自己" else None
            if matched.対象 == "入力役割":
                bindings = dict(dict(packet["役割"]["入力役割"]).get(step.識別子, ()))
                parent = bindings.get(matched.入力役割)
                if parent and parent["領域"] == "工程" and parent["識別子"] in info:
                    pair = info[parent["識別子"]]
                    if pair[1] in matched.対象作用:
                        reopen = pair
            policy = 回復方針を決定(種別=category, 分類=失敗を分類(category), 発生目的=goal, 発生作用=行為,
                    規則=matched, 再開放=reopen, 契約=指紋(asdict(matched)))
            if not policy.自動実行:
                continue
            next_key = 計画接頭辞 + str(int(plan_key.split(":")[-1]) + 1)
            def replan(s, policy=policy, next_key=next_key):
                values = dict(s.成果)
                banned = tuple(tuple(x) for x in packet["禁止"]) + policy.禁止
                if len(set(banned)) != len(banned):
                    raise ValueError("同じ回復を反復しない")
                候補 = 計画を構成(packet["解釈"], values["運用入力"], self.目録, 禁止=banned)
                _局所変更を検査(packet, 候補, policy)
                return HDS作用結果(HDS作用状態.成立, 成果=((next_key, 候補),
                            (next_key + "/回復根拠", 正準(asdict(policy)))),
                            理由=("目的と資料を保持した局所再計画", policy.動作))
            return HDS関数作用("運用/回復/" + plan_key, replan, 入力状態=("運用:計画構成済",),
                    解消対象=("運用:成果未構成",), 読取成果=(plan_key, failure_key, "運用入力"),
                    優先度=5, 契約版=運用版, 作用定義ID="運用/回復")
        return None

    def 最終検証(self, 状態, _):
        """原依頼・計画・実出力を照合する。任意の世界事実の正しさの証明ではない。"""
        try:
            self.目録.照合()
            values = dict(状態.成果)
            answer = 結果を復元(values["運用応答"])
            proof = values["運用採用対応"]
            if proof["原文"] != values["運用入力"]["原文"] or proof["回答印"] != 指紋(values["運用応答"]):
                return False
            current_key, packet = 現行計画(状態)
            if proof["計画鍵"] != current_key or proof["計画印"] != 指紋(packet) or proof["目録"] != self.目録.ハッシュ:
                return False
            if packet["方式"] == "管理":
                return answer.成立 and proof["出力"] == []
            if proof["資料依存"] != 入力依存を収集(packet, values["運用入力"], answer.参照):
                return False
            plan = 計画を復元(packet["計画"])
            expected = [_工程鍵(current_key, sid) for sid in plan.出力工程]
            if proof["出力"] != expected or proof["出力印"] != [指紋(values[k]) for k in expected]:
                return False
            if any(not 結果を復元(values[k]).成立 for k in expected):
                return False
            expected_results = tuple(結果を復元(values[k]) for k in expected)
            expected_answer = 最終素材を構成(expected_results, packet)
            if 指紋(結果を保存(expected_answer)) != 指紋(values["運用応答"]):
                return False
            if packet["回答種別"] == "数量回答":
                if not 数量回答を検査(answer):
                    return False
                原要求 = packet["解釈"]
                if 原要求["方式"] == "継続":
                    原要求 = 原要求["目的"]
                構造 = answer.データ["構造"]
                if 原要求["方式"] == "数量言語":
                    if 構造["要求"] != 原要求["要求"] or answer.データ["表示"] != 原要求["要求"]["表示"]:
                        return False
                elif 原要求["方式"] == "数量再表現":
                    前 = 結果を復元(values["運用入力"]["前回結果"])
                    表示 = {**前.データ["表示"], **原要求["表示差分"]}
                    if 構造 != 前.データ["構造"] or answer.データ["表示"] != 表示:
                        return False
                else:
                    return False
                return all(name in values["運用入力"]["資料"] and
                           text == values["運用入力"]["資料"][name]["本文"]
                           for name, text in 構造["資料"].items())
            if packet["回答種別"] == "関係資料回答":
                if not 関係回答を検査(answer):
                    return False
                原要求 = packet["解釈"]
                if 原要求["方式"] == "継続":
                    原要求 = 原要求["目的"]
                構造 = answer.データ["構造"]
                if 原要求["方式"] == "関係資料":
                    if 構造["要求"] != 原要求["要求"] or answer.データ["表示形式"] != 原要求["要求"]["形式"]:
                        return False
                elif 原要求["方式"] == "関係再表現":
                    前回 = 結果を復元(values["運用入力"]["前回結果"])
                    if 構造 != 前回.データ["構造"] or answer.データ["表示形式"] != 原要求["形式"]:
                        return False
                else:
                    return False
                if 構造["要求"]["範囲"] == "全資料" and set(構造["資料群"]) != set(values["運用入力"]["資料"]):
                    return False
                return all(名 in values["運用入力"]["資料"] and 項["資料"] == values["運用入力"]["資料"][名]["結果"]
                           for 名, 項 in 構造["資料群"].items())
            if packet["回答種別"] == "資料文章回答":
                if not 資料文章を検査(answer):
                    return False
                原要求 = packet["解釈"]
                if 原要求["方式"] == "継続":
                    原要求 = 原要求["目的"]
                構造 = answer.データ["構造"]
                if 原要求["方式"] == "一般資料":
                    if 構造["要求"] != 原要求["要求"] or answer.データ["表示形式"] != 原要求["要求"]["形式"]:
                        return False
                elif 原要求["方式"] == "一般再表現":
                    前回 = 結果を復元(values["運用入力"]["前回結果"])
                    if 構造 != 前回.データ["構造"] or answer.データ["表示形式"] != 原要求["形式"]:
                        return False
                else:
                    return False
                if 構造["要求"]["範囲"] == "公開取得":
                    return 構造["取得記録"] is not None
                if 構造["要求"]["範囲"] == "全資料" and set(構造["資料群"]) != set(values["運用入力"]["資料"]):
                    return False
                return all(名 in values["運用入力"]["資料"] and 項["資料"] == values["運用入力"]["資料"][名]["結果"]
                           for 名, 項 in 構造["資料群"].items())
            if packet["回答種別"] == "検討回答":
                return answer.成立 and 改善回答を検査(answer.データ)
            return answer.成立 and (回答記録整合(answer) or 改善回答を検査(answer.データ))
        except (ValueError, TypeError, KeyError):
            return False

"""HDSを唯一の実行主体とする、資料・知識・会話・能力の通常運用入口。"""
from __future__ import annotations
from copy import deepcopy
from dataclasses import dataclass, replace
from pathlib import Path
from threading import Lock
import os
import tempfile
import time
from ..HDS実行主体 import HDS実行主体, HDS実行状態, HDS作用結果, HDS作用状態, HDS関数作用, HDS作用供給器, HDS終端
from ..統合駆動_v2.政策 import HDS運用政策
from ..統合駆動_v2.検証 import HDS検証器
from ..能力合成 import _符号化, 合成計画
from ..製品版.型 import 能力結果, 参照資料
from ..監査改善会話解釈 import JSONを厳格に読む, 名前を確認
from ..会話回答 import 回答記録整合
from ..監査改善接続 import 改善回答を検査
from .能力 import 運用能力目録
from .値 import 運用版, 正準, 指紋, 結果を保存, 結果を復元, 文字を検査, 封緘, 開封, 計画を保存
from .解釈 import 依頼を解釈, 計画を構成, 型付き要求を保存, 構造を保存
from .工程 import 工程供給, 現行計画
from .原記録 import 運用原記録
from .手順形成 import 手順形成供給, 目的鍵, 手順を束縛, 形成結果を検査, 手順資産を検査
from .知識資産 import 知識を形成, 資産を検査
from .数量生成 import 数量回答を検査
from .内容構成 import 資料文章を検査
from .保存移行 import 移行履歴を検査
from .一般依頼 import 一般要求を検査


@dataclass(frozen=True, slots=True)
class 運用応答:
    状態: str
    本文: str
    理由: tuple[str, ...] = ()
    結果: 能力結果 | None = None
    HDS結果: object = None
    追跡: dict | None = None

    @property
    def 成立(self):
        return self.状態 == HDS終端.採用.value

    def 辞書化(self):
        return {"状態": self.状態, "本文": self.本文, "理由": list(self.理由),
                "結果": 結果を保存(self.結果) if self.結果 else None, "追跡": deepcopy(self.追跡)}


class HDS運用セッション:
    """セッションは入出力・保存の所有境界。意味解釈・工程選択・採否はHDSへ置く。

    任意自然言語理解を名乗らず、現行部品の対応意味を同じ実行経路へ接続する。
    データ中の契約・命令を登録コードへ昇格させない。
    """
    def __init__(self, セッションID="default", *, 外部読取許可=False, 取得器=None,
                 追加能力=(), 追加役割作用=(), 再利用=True, 最大作用回数=128, 最大発話=128, 手順形成=True):
        文字を検査(セッションID, "セッションID", 128)
        if type(外部読取許可) is not bool or type(再利用) is not bool:
            raise TypeError("運用設定はbool")
        if type(最大作用回数) is not int or not 4 <= 最大作用回数 <= 512:
            raise ValueError("最大作用回数は4..512")
        if type(最大発話) is not int or not 1 <= 最大発話 <= 512:
            raise ValueError("最大発話は1..512")
        self.ID, self.外部読取許可 = セッションID, 外部読取許可
        self.最大作用回数, self.最大発話 = 最大作用回数, 最大発話
        self.目録 = 運用能力目録(セッションID, 外部読取許可=外部読取許可, 取得器=取得器,
                              追加能力=追加能力, 追加役割作用=追加役割作用, 再利用=再利用)
        if type(手順形成) is not bool:
            raise TypeError("手順形成はbool")
        self.手順形成 = 手順形成
        self._原記録 = 運用原記録(セッションID)
        self.目録.原記録庫 = self._原記録.庫
        self._知識資産 = {}
        self._形成手順 = {}
        self._資料 = {}
        self._旧資料 = []
        self._前回目的 = None
        self._保留目的 = None
        self._前回結果 = None
        self._前回依存 = {}
        self._焦点有効 = False
        self._前回知識範囲 = None
        self._移行履歴 = []
        self._発話 = []
        self._経験 = []
        self._ロック = Lock()

    def 能力一覧(self):
        return deepcopy(self.目録.一覧())

    def _有効(self):
        if self._前回目的 and self._前回目的.get("方式") == "一般資料" and self._前回目的["要求"]["範囲"] == "全資料":
            if set(self._前回依存) != set(self._資料):
                return False
        return (self._焦点有効 and self._前回結果 is not None
                and (self._前回知識範囲 is None or self._前回知識範囲 == self._知識範囲印())
                and all(k in self._資料 and self._資料[k]["版"] == v for k, v in self._前回依存.items()))

    def 状態(self):
        if not self._ロック.acquire(blocking=False):
            raise ValueError("会話の処理中")
        try:
            return {"版": 運用版, "セッションID": self.ID, "資料": deepcopy(self._資料),
                    "前回有効": self._有効(), "保留目的": deepcopy(self._保留目的),
                    "発話数": len(self._発話), "経験数": len(self._経験),
                    "知識資産数": len(self._知識資産), "形成手順数": len(self._形成手順),
                    "原記録資料": deepcopy(self._原記録.資料対応), "原記録改訂": self._原記録.庫.起点().改訂,
                    "能力": self.能力一覧(), "再利用": self.目録.再利用庫.統計()}
        finally:
            self._ロック.release()

    def 資料を登録(self, 名前, 本文, *, 種類="資料", データ=None, 更新=False):
        名前を確認(名前)
        文字を検査(本文, "資料本文", 100_000)
        if type(更新) is not bool or 種類 not in ("資料", "知識", "本文", "命題", "仮説", "介入"):
            raise ValueError("資料の登録条件不正")
        if データ is None:
            データ = {}
        if type(データ) is not dict:
            raise TypeError("資料データはdict")
        # 本文が長くても、制御入力と資料は別の欄で渡す。本文を命令へ埋めない。
        request = {"方式": "管理", "行為": "更新" if 更新 else "登録", "名前": 名前,
                   "本文": 本文, "種類": 種類, "データ": 正準(データ)}
        raw = f'資料「{名前}」を{"更新" if 更新 else "登録"}する'
        return self._応答(raw, 管理要求=request)

    def 文脈を取得(self, *, 必須資料=(), 検索語=(), 最大バイト数=32768):
        if type(必須資料) not in (list, tuple) or type(検索語) not in (list, tuple):
            raise TypeError("必須資料・検索語は文字列の配列で指定する")
        return self._応答("原記録の文脈を取得する", 文脈要求={"必須資料": list(必須資料),
                         "検索語": list(検索語), "最大バイト数": 最大バイト数})

    def 応答(self, 原文, *, 外部読取許可=False, 停止要求=None, 期限秒=None):
        return self._応答(原文, 外部読取許可=外部読取許可, 停止要求=停止要求, 期限秒=期限秒)

    def 目的を実行(self, 要求, *, 停止要求=None):
        packed = 型付き要求を保存(要求)
        return self._応答(要求.原文, 型付き目的=packed, 停止要求=停止要求)

    def 役割目的を実行(self, 目的, *, 原文, 外部読取許可=False, 停止要求=None):
        from ..会話意味 import 意味目的
        from dataclasses import asdict
        if type(目的) is not 意味目的:
            raise TypeError("意味目的が必要")
        目的.鍵()
        return self._応答(原文, 意味目的=正準(asdict(目的)), 外部読取許可=外部読取許可, 停止要求=停止要求)

    def 合成を実行(self, 原文, 計画, 資料, *, 外部読取許可=False, 停止要求=None):
        if type(資料) is not dict or len(資料) > 128:
            raise ValueError("合成資料の型・数")
        packed = {"計画": 計画を保存(計画), "資料": {k: 結果を保存(v) for k, v in 資料.items()}}
        return self._応答(原文, 明示合成=packed, 外部読取許可=外部読取許可, 停止要求=停止要求)

    def _管理作用(self, 状態):
        current = 現行計画(状態)
        if current is None or current[1]["方式"] != "管理":
            return ()
        key, packet = current
        def execute(s):
            values = dict(s.成果)
            task = packet["解釈"]
            行為 = task["行為"]
            delta = None
            if 行為 in ("登録", "更新"):
                name = 名前を確認(task["名前"])
                if 行為 == "登録" and name in values["運用入力"]["資料"]:
                    raise ValueError("既存資料は明示的に更新してください")
                if 行為 == "更新" and name not in values["運用入力"]["資料"]:
                    raise ValueError("未登録資料は更新できない")
                body = 文字を検査(task["本文"], "資料本文", 100_000)
                payload = task.get("データ", {})
                if body.lstrip().startswith(("{", "[")) and task["種類"] in ("資料", "知識"):
                    JSONを厳格に読む(body)
                version = 指紋({"種類": task["種類"], "本文": body, "データ": payload})
                ref = 参照資料("運用資料:" + name + ":" + version, name, "利用者提供" + task["種類"], 本文=body)
                value = 能力結果(True, body, 参照=(ref,), データ=payload)
                record = {"種類": task["種類"], "本文": body, "データ": payload,
                          "版": version, "結果": 結果を保存(value)}
                prospective = deepcopy(values["運用入力"]["資料"])
                prospective[name] = record
                if len(prospective) > 32 or len(_符号化(prospective)) > 2_000_000:
                    raise ValueError("保持資料の容量上限")
                delta = {"行為": 行為, "名前": name, "資料": record}
                if task["種類"] == "知識":
                    delta["知識資産"] = 知識を形成(name, record)
                response = 能力結果(True, f'資料「{name}」を{行為}しました。', データ={"版": version, "種類": task["種類"], "事実認定": False})
            elif 行為 == "初期化":
                delta = {"行為": "初期化"}
                response = 能力結果(True, "会話・資料・再利用結果を初期化しました。")
            elif 行為 == "会話":
                phrase = task.get("発話", "")
                body = ("HDSが資料・知識・目的・各能力の中間成果を保持して処理します。"
                        "対応入口は数式、JSON/CSV、数量比較・集計、本文・命題・仮説・介入の検討、"
                        "条件訂正と再表現です。未対応の自由文は残差として返します。") if phrase == "できることを教えて" else (
                        "外部読取は各依頼の明示許可がある場合だけ行います。" if phrase == "外部禁止" else "どうぞ。")
                response = 能力結果(True, body)
            else:
                raise ValueError("未対応の管理作用")
            proof = {"原文": values["運用入力"]["原文"], "計画鍵": key, "計画印": 指紋(packet),
                     "目録": self.目録.ハッシュ, "出力": [], "出力印": [], "回答印": 指紋(結果を保存(response))}
            return HDS作用結果(HDS作用状態.成立, 追加状態=frozenset({"運用:応答成立"}),
                    解消残差=frozenset({"運用:成果未構成"}),
                    成果=(("運用応答", 結果を保存(response)), ("運用採用対応", proof), ("運用更新", delta)),
                    理由=("利用者操作をHDS内で検査し更新候補を構成",))
        return (HDS関数作用("運用/管理", execute, 入力状態=("運用:計画構成済",),
                    出力状態=("運用:応答成立",), 解消対象=("運用:成果未構成",), 読取成果=("運用入力", key), 契約版=運用版),)

    def _知識範囲印(self):
        return 指紋({名前: 資産["資料版"] for 名前, 資産 in self._知識資産.items()})

    def _知識を読む目的(self, 状態):
        解釈 = dict(状態.成果).get("運用解釈", {})
        if 解釈.get("方式") == "継続":
            解釈 = 解釈["目的"]
        if 解釈.get("方式") == "知識横断":
            return True
        return (解釈.get("方式") == "会話" and 解釈.get("依頼", {}).get("行為") == "再表現"
                and self._前回知識範囲 is not None)

    def _全資料を読む目的(self, 状態):
        解釈 = dict(状態.成果).get("運用解釈", {})
        if 解釈.get("方式") == "継続":
            解釈 = 解釈["目的"]
        if 解釈.get("方式") == "一般再表現":
            解釈 = self._前回目的 or {}
        return 解釈.get("方式") == "一般資料" and 解釈["要求"]["範囲"] == "全資料"

    def _記憶同期作用(self, 状態):
        if "運用:応答成立" not in 状態.成立状態 or "運用:記憶同期済" in 状態.成立状態:
            return ()
        def 構成(s):
            値 = dict(s.成果)
            回答 = 結果を復元(値["運用応答"])
            候補 = self._原記録.同期候補(値["運用入力"], 値.get("運用更新"), 回答,
                                        値["運用採用対応"].get("資料依存", {}), 知識範囲=self._知識を読む目的(s), 全資料範囲=self._全資料を読む目的(s))
            return HDS作用結果(HDS作用状態.成立, 追加状態=frozenset({"運用:記憶同期済"}),
                    成果=(("運用原記録候補", 候補.保存()),), 理由=("原文・成果・版・依存の同期候補を構成",))
        return (HDS関数作用("運用/原記録同期", 構成, 入力状態=("運用:応答成立", "運用:形成処理済"),
                  出力状態=("運用:記憶同期済",), 読取成果=("運用入力", "運用応答", "運用採用対応"), 契約版=運用版),)

    def _記憶を検証(self, 状態, _):
        try:
            値 = dict(状態.成果)
            if not 形成結果を検査(状態, self.目録):
                return False
            更新 = 値.get("運用更新")
            if 更新 and "知識資産" in 更新:
                資産を検査(更新["知識資産"], 更新["資料"])
            候補 = self._原記録.同期候補(値["運用入力"], 更新, 結果を復元(値["運用応答"]),
                                        値["運用採用対応"].get("資料依存", {}), 知識範囲=self._知識を読む目的(状態), 全資料範囲=self._全資料を読む目的(状態))
            return 候補.保存() == 値["運用原記録候補"]
        except (ValueError, TypeError, KeyError):
            return False

    def _応答(self, 原文, *, 型付き目的=None, 明示合成=None, 管理要求=None, 意味目的=None, 文脈要求=None,
             外部読取許可=False, 停止要求=None, 期限秒=None):
        if not self._ロック.acquire(blocking=False):
            return 運用応答("SUSPEND", "同じ会話を処理中です。", ("同時更新を拒否",))
        try:
            文字を検査(原文)
            if type(外部読取許可) is not bool or 外部読取許可 and not self.外部読取許可:
                raise ValueError("外部読取は設定と各依頼の両方で許可が必要")
            if 停止要求 is not None and not callable(停止要求):
                raise TypeError("停止要求はcallable")
            if 期限秒 is not None and (type(期限秒) not in (int, float) or not 0 < 期限秒 <= 3600):
                raise ValueError("期限秒は0超3600以下の有限数")
            if len(self._発話) >= self.最大発話 and 原文 not in ("/初期化", "会話を初期化して"):
                raise ValueError("発話容量上限。初期化又は別セッションを利用してください")
            self.目録.照合()
            inputs = 正準({"原文": 原文, "セッションID": self.ID, "資料": self._資料,
                     "前回目的": self._前回目的, "保留目的": self._保留目的,
                     "前回結果": self._前回結果, "前回有効": self._有効(), "前回依存": self._前回依存,
                     "型付き目的": 型付き目的, "明示合成": 明示合成, "管理要求": 管理要求, "意味目的": 意味目的,
                     "外部許可": 外部読取許可, "知識資産": self._知識資産,
                     "文脈要求": 文脈要求, "原記録資料": self._原記録.資料対応,
                     "原記録起点": 構造を保存(self._原記録.庫.起点())})
            if len(_符号化(inputs)) > 8_000_000:
                raise ValueError("運用入力の保存上限")
            def interpret(s):
                データ = dict(s.成果)["運用入力"]
                try:
                    parsed = 依頼を解釈(データ) if データ["管理要求"] is None else {**データ["管理要求"], "原文": データ["原文"]}
                    return HDS作用結果(HDS作用状態.成立, 追加状態=frozenset({"運用:依頼解釈済"}),
                        解消残差=frozenset({"運用:依頼未解釈"}), 成果=(("運用解釈", parsed),), 理由=("依頼の意味を構文化",))
                except (ValueError, TypeError, KeyError) as exc:
                    return HDS作用結果(HDS作用状態.保留, 成果=(("運用診断", {"段階": "依頼解釈", "理由": str(exc)}),), 理由=(str(exc),))
            def plan(s):
                values = dict(s.成果)
                try:
                    packet = 計画を構成(values["運用解釈"], values["運用入力"], self.目録)
                    記録 = self._形成手順.get(目的鍵(values["運用解釈"]))
                    if 記録 is not None and packet["方式"] != "管理":
                        復元計画 = 手順を束縛(記録, values["運用解釈"], values["運用入力"], self.目録)
                        # 現行の目的解釈・計画と一致する手順だけ使う。保存物は信頼根にしない。
                        if 復元計画 is not None:
                            比較 = {鍵: 値 for 鍵, 値 in packet.items() if 鍵 != "解釈"}
                            復元比較 = {鍵: 値 for 鍵, 値 in 復元計画.items() if 鍵 != "解釈"}
                            if 比較 == 復元比較:
                                packet = 復元計画
                                packet["手順由来"] = 記録["SHA256"]
                    return HDS作用結果(HDS作用状態.成立, 追加状態=frozenset({"運用:計画構成済"}),
                        解消残差=frozenset({"運用:計画未構成"}), 成果=(("運用計画:0", packet),), 理由=("要求から作用の依存計画を構成",))
                except (ValueError, TypeError, KeyError) as exc:
                    return HDS作用結果(HDS作用状態.保留, 成果=(("運用診断", {"段階": "目的計画", "理由": str(exc)}),), 理由=(str(exc),))
            bridge = 工程供給(self.目録)
            形成供給 = 手順形成供給(self.目録, 有効=self.手順形成, 最大作用回数=self.最大作用回数)
            actions = (
                HDS関数作用("運用/依頼構文化", interpret, 出力状態=("運用:依頼解釈済",),
                           解消対象=("運用:依頼未解釈",), 読取成果=("運用入力",), 契約版=運用版),
                HDS関数作用("運用/目的計画", plan, 入力状態=("運用:依頼解釈済",), 出力状態=("運用:計画構成済",),
                           解消対象=("運用:計画未構成",), 読取成果=("運用入力", "運用解釈"), 契約版=運用版))
            started = time.monotonic()
            def stop():
                flag = 停止要求() if 停止要求 is not None else False
                if type(flag) is not bool:
                    raise TypeError("停止要求はboolを返す必要がある")
                return flag or (期限秒 is not None and time.monotonic() - started >= 期限秒)
            policy = HDS運用政策(探索深さ=64, 最大探索状態=8192, 最大内部生成=256,
                                 許可権限=("外部読取",) if 外部読取許可 else (), 自動形成=False)
            initial = HDS実行状態(目的=(原文,), 要求状態=frozenset({"運用:応答成立", "運用:形成処理済", "運用:記憶同期済"}),
                        残差=frozenset({"運用:依頼未解釈", "運用:計画未構成", "運用:成果未構成"}),
                        成果=(("運用入力", inputs),))
            結果 = HDS実行主体(actions, 最大作用回数=self.最大作用回数, 政策=policy,
                        作用供給器=(HDS作用供給器("能力工程", bridge, 運用版), HDS作用供給器("管理操作", self._管理作用, 運用版),
                                     HDS作用供給器("手順形成", 形成供給, 運用版), HDS作用供給器("原記録同期", self._記憶同期作用, 運用版)),
                        最終検証器=(HDS検証器("運用目的と実成果", bridge.最終検証, 運用版), HDS検証器("原記録と資料版", self._記憶を検証, 運用版)), 停止要求=stop).実行(initial)
            values = dict(結果.状態.成果)
            追跡 = {"版": 運用版, "目録": self.目録.ハッシュ, "入力印": 指紋(inputs),
                     "終端": 結果.終端.value, "理由": list(結果.理由), "阻害": 構造を保存(結果.阻害履歴),
                     "作用": [構造を保存(h) for h in 結果.履歴], "計装": 構造を保存(結果.計装),
                     "候補計画": [k for k in values if k.startswith("運用計画:") and "/" not in k],
                     "能力試行": [v for k, v in values.items() if "/試行/" in k],
                     "残差": sorted(結果.状態.残差), "再利用": self.目録.再利用庫.統計(),
                     "手順形成": {"状態": values.get("運用形成結果", {}).get("理由", "未到達"),
                                  "再現工程数": sum(k.startswith("運用形成:") for k in values),
                                  "手順再利用": bool(現行計画(結果.状態) and 現行計画(結果.状態)[1].get("手順由来"))}}
            accepted = 結果.終端 == HDS終端.採用
            answer = 結果を復元(values["運用応答"]) if accepted else None
            parsed = values.get("運用解釈")
            if accepted:
                # HDS採用後にだけセッションへ反映する。別の意味判定は行わない。
                原記録候補 = 運用原記録.復元(values["運用原記録候補"], self.ID)
                delta = values.get("運用更新")
                if delta and delta["行為"] == "初期化":
                    self._資料 = {}; self._旧資料 = []; self._前回目的 = self._保留目的 = self._前回結果 = None
                    self._前回依存 = {}; self._焦点有効 = False; self._発話 = []; self._経験 = []
                    self.目録.再利用庫.消去()
                elif delta:
                    name = delta["名前"]
                    if name in self._資料:
                        self._旧資料.append({"名前": name, **deepcopy(self._資料[name])})
                        self._旧資料 = self._旧資料[-32:]
                    self._資料[name] = deepcopy(delta["資料"])
                elif parsed and parsed["方式"] != "管理":
                    current_key, packet = 現行計画(結果.状態)
                    effective = parsed["目的"] if parsed["方式"] == "継続" else parsed
                    is_reword = (effective.get("方式") in ("数量再表現", "一般再表現") or (effective.get("方式") == "会話" and effective.get("依頼", {}).get("行為") == "再表現"))
                    if not is_reword:
                        self._前回目的 = deepcopy(effective)
                        self._前回知識範囲 = self._知識範囲印() if effective.get("方式") == "知識横断" else None
                    self._保留目的 = None
                    self._前回結果 = 結果を保存(answer)
                    # 回答に伝播した参照と、計画で実際に使う登録資料の両方から依存を残す。
                    self._前回依存 = deepcopy(values["運用採用対応"]["資料依存"])
                    self._焦点有効 = True
                    experience = {"目的": effective.get("方式"), "目録": self.目録.ハッシュ,
                        "計画印": 指紋(packet), "資料版": self._前回依存,
                        "作用列": [row["能力"] for row in 追跡["能力試行"] if row.get("採否") == "合格"],
                        "範囲": "この入力・契約で完遂した記録。一般法則又は自動学習とはしない"}
                    self._経験.append(正準(experience)); self._経験 = self._経験[-64:]
                self._原記録 = 原記録候補
                self.目録.原記録庫 = self._原記録.庫
                if delta and delta["行為"] == "初期化":
                    self._知識資産 = {}; self._形成手順 = {}; self._前回知識範囲 = None; self._移行履歴 = []
                elif delta:
                    if "知識資産" in delta:
                        self._知識資産[delta["名前"]] = deepcopy(delta["知識資産"])
                    else:
                        self._知識資産.pop(delta["名前"], None)
                形成 = values.get("運用形成結果", {}).get("手順")
                if 形成 is not None:
                    self._形成手順[形成["目的鍵"]] = deepcopy(形成)
                    if len(self._形成手順) > 64:
                        del self._形成手順[next(iter(self._形成手順))]
                body = answer.本文
                reasons = 結果.理由
            else:
                is_reword = (parsed is not None and (parsed.get("方式") in ("数量再表現", "一般再表現") or (parsed.get("方式") == "会話"
                             and parsed.get("依頼", {}).get("行為") == "再表現")))
                if parsed and parsed["方式"] not in ("管理",) and not is_reword:
                    effective = parsed["目的"] if parsed["方式"] == "継続" else parsed
                    self._保留目的 = deepcopy(effective)
                if not is_reword:
                    self._焦点有効 = False
                diagnostic = values.get("運用診断", {}).get("理由")
                failures = [v.get("理由", "") for v in 追跡["能力試行"] if v.get("理由")]
                reasons = tuple(x for x in (diagnostic, *failures, *結果.理由) if x)
                body = "回答は未確定です。" + (reasons[0] if reasons else "必要な作用又は観測が不足しています。")
            self._発話.append({"入力": 原文, "状態": 結果.終端.value, "本文": body,
                               "追跡印": 指紋(追跡)})
            return 運用応答(結果.終端.value, body, tuple(reasons), answer, 結果, 追跡)
        except (ValueError, TypeError, KeyError) as exc:
            return 運用応答("SUSPEND", "処理を確定できません。" + str(exc), (str(exc),))
        finally:
            self._ロック.release()

    def 保存(self):
        if not self._ロック.acquire(blocking=False):
            raise ValueError("処理中の状態は保存できない")
        try:
            状態 = {"版": 運用版, "セッションID": self.ID, "目録": self.目録.ハッシュ,
                     "外部読取許可": self.外部読取許可, "最大作用回数": self.最大作用回数, "最大発話": self.最大発話,
                     "資料": self._資料, "旧資料": self._旧資料, "前回目的": self._前回目的,
                     "保留目的": self._保留目的, "前回結果": self._前回結果,
                     "前回依存": self._前回依存, "焦点有効": self._焦点有効,
                     "発話": self._発話, "経験": self._経験,
                     "原記録": self._原記録.保存(), "知識資産": self._知識資産,
                     "形成手順": self._形成手順, "手順形成": self.手順形成, "前回知識範囲": self._前回知識範囲, "移行履歴": self._移行履歴}
            packed = _符号化(封緘(状態)).decode("utf-8")
            if len(packed.encode()) > 16_000_000:
                raise ValueError("保存上限")
            return packed
        finally:
            self._ロック.release()

    @classmethod
    def 復元(cls, text, *, 外部読取許可=False, 取得器=None, 追加能力=(), 追加役割作用=()):
        状態 = 開封(JSONを厳格に読む(text, 最大バイト数=16_000_000))
        required = {"版", "セッションID", "目録", "外部読取許可", "最大作用回数", "最大発話", "資料", "旧資料",
                    "前回目的", "保留目的", "前回結果", "前回依存", "焦点有効", "発話", "経験", "原記録", "知識資産", "形成手順", "手順形成", "前回知識範囲", "移行履歴"}
        if type(状態) is not dict or set(状態) != required or 状態["版"] != 運用版:
            raise ValueError("保存形式・版不一致")
        if 状態["外部読取許可"] is not 外部読取許可:
            raise ValueError("保存データから外部権限を復元しない。呼出側設定と一致が必要")
        obj = cls(状態["セッションID"], 外部読取許可=外部読取許可, 取得器=取得器,
                  追加能力=追加能力, 追加役割作用=追加役割作用,
                  最大作用回数=状態["最大作用回数"], 最大発話=状態["最大発話"], 手順形成=状態["手順形成"])
        if 状態["目録"] != obj.目録.ハッシュ:
            raise ValueError("保存時の能力・意味契約から変更されている")
        if type(状態["資料"]) is not dict or len(状態["資料"]) > 32 or len(_符号化(状態["資料"])) > 2_000_000:
            raise ValueError("保存資料の型・上限")
        for name, value in 状態["資料"].items():
            名前を確認(name)
            if type(value) is not dict or set(value) != {"種類", "本文", "データ", "版", "結果"}:
                raise ValueError("保存資料の欄不一致")
            if value["版"] != 指紋({k: value[k] for k in ("種類", "本文", "データ")}):
                raise ValueError("保存資料の版不一致")
            文字を検査(value["本文"], "資料本文", 100_000)
            if value["種類"] not in ("資料", "知識", "本文", "命題", "仮説", "介入") or type(value["データ"]) is not dict:
                raise ValueError("保存資料の種類・データ不正")
            ref = 参照資料("運用資料:" + name + ":" + value["版"], name,
                        "利用者提供" + value["種類"], 本文=value["本文"])
            expected = 能力結果(True, value["本文"], 参照=(ref,), データ=value["データ"])
            if 指紋(結果を保存(expected)) != 指紋(value["結果"]):
                raise ValueError("保存資料の本体・参照不一致")
        if 状態["前回結果"] is not None:
            old = 結果を復元(状態["前回結果"])
            if not (回答記録整合(old) or 改善回答を検査(old.データ) or 数量回答を検査(old) or 資料文章を検査(old)):
                raise ValueError("保存回答の整合不一致")
        if type(状態["焦点有効"]) is not bool or type(状態["前回依存"]) is not dict:
            raise ValueError("保存会話状態の型不正")
        for name in ("前回目的", "保留目的"):
            if 状態[name] is not None and (type(状態[name]) is not dict or type(状態[name].get("方式")) is not str):
                raise ValueError("保存目的の型不正")
            if 状態[name] is not None and 状態[name].get("方式") == "一般資料":
                一般要求を検査(状態[name].get("要求"))
        for name, version in 状態["前回依存"].items():
            名前を確認(name)
            if type(version) is not str or len(version) != 64:
                raise ValueError("保存依存の版不正")
        for name, limit in (("旧資料", 32), ("発話", obj.最大発話), ("経験", 64)):
            if type(状態[name]) is not list or len(状態[name]) > limit:
                raise ValueError("保存履歴の型・上限")
        for public, internal in (("資料", "_資料"), ("旧資料", "_旧資料"), ("前回目的", "_前回目的"),
                ("保留目的", "_保留目的"), ("前回結果", "_前回結果"), ("前回依存", "_前回依存"),
                ("焦点有効", "_焦点有効"), ("発話", "_発話"), ("経験", "_経験")):
            setattr(obj, internal, deepcopy(状態[public]))
        if obj._前回結果 is not None:
            前回 = 結果を復元(obj._前回結果)
            if 前回.データ.get("種別") == "数量言語回答":
                構造 = 前回.データ["構造"]
                目的 = obj._前回目的
                if (not 目的 or 目的.get("方式") != "数量言語"
                        or 目的.get("要求") != 構造["要求"]):
                    raise ValueError("数量保存回答と前回目的が不一致")
                if set(構造["資料"]) != set(obj._前回依存):
                    raise ValueError("数量保存回答の資料依存が不一致")
                # 失効した旧回答は履歴として残せる。現行利用する回答は元資料とも照合する。
                if obj._有効() and any(本文 != obj._資料[名]["本文"] for 名, 本文 in 構造["資料"].items()):
                    raise ValueError("数量保存回答と現行原資料が不一致")
        if obj._前回結果 is not None:
            前回 = 結果を復元(obj._前回結果)
            if 前回.データ.get("種別") == "資料文章回答":
                構造, 目的 = 前回.データ["構造"], obj._前回目的
                if not 目的 or 目的.get("方式") != "一般資料" or 目的.get("要求") != 構造["要求"]:
                    raise ValueError("資料文章保存回答と前回目的が不一致")
                if 構造["要求"]["範囲"] != "公開取得":
                    if set(構造["資料群"]) != set(obj._前回依存):
                        raise ValueError("資料文章保存回答の資料依存が不一致")
                    if obj._有効() and any(行["資料"] != obj._資料[名]["結果"] for 名, 行 in 構造["資料群"].items()):
                        raise ValueError("資料文章保存回答と現行原資料が不一致")
        移行履歴を検査(状態["移行履歴"])
        obj._移行履歴 = deepcopy(状態["移行履歴"])
        obj._原記録 = 運用原記録.復元(状態["原記録"], obj.ID)
        obj._原記録.資料を照合(obj._資料)
        obj.目録.原記録庫 = obj._原記録.庫
        資産群 = 状態["知識資産"]
        if type(資産群) is not dict or set(資産群) != {名前 for 名前, 値 in obj._資料.items() if 値["種類"] == "知識"}:
            raise ValueError("保存知識資産と現行資料の対応不一致")
        for 名前, 資産 in 資産群.items():
            if type(資産) is not dict or 資産.get("名前") != 名前:
                raise ValueError("知識資産の名前が不一致")
            資産を検査(資産, obj._資料[名前])
        手順群 = 状態["形成手順"]
        if type(手順群) is not dict or len(手順群) > 64:
            raise ValueError("保存手順の型・上限")
        for 鍵, 手順 in 手順群.items():
            手順資産を検査(手順, obj.目録)
            if (type(手順) is not dict or 手順.get("目的鍵") != 鍵 or 手順.get("目録") != obj.目録.ハッシュ
                    or 手順.get("検証") != "再実行一致"
                    or 手順.get("SHA256") != 指紋({k: v for k, v in 手順.items() if k != "SHA256"})):
                raise ValueError("保存手順の整合不一致")
        範囲 = 状態["前回知識範囲"]
        if 範囲 is not None and (type(範囲) is not str or len(範囲) != 64):
            raise ValueError("保存知識範囲の型不正")
        obj._前回知識範囲 = 範囲
        obj._知識資産, obj._形成手順 = deepcopy(資産群), deepcopy(手順群)
        return obj

    def 保存先へ書く(self, path):
        content = self.保存()
        target = Path(path)
        target.parent.mkdir(parents=True, exist_ok=True)
        fd, temporary = tempfile.mkstemp(prefix=".hds-", dir=target.parent)
        try:
            with os.fdopen(fd, "w", encoding="utf-8", newline="\n") as stream:
                stream.write(content); stream.flush(); os.fsync(stream.fileno())
            os.replace(temporary, target)
        finally:
            if os.path.exists(temporary):
                os.unlink(temporary)

"""実測したv1〜v5保存契約からの明示移行。旧原本・履歴・依存を保持する。"""
from __future__ import annotations
from copy import deepcopy
from hashlib import sha256
from types import SimpleNamespace
import json
from ..監査改善会話解釈 import JSONを厳格に読む, 名前を確認
from .値 import 運用版, 封緘, 開封, 指紋, 結果を復元, 結果を保存
from ..製品版.型 import 能力結果, 参照資料
from .原記録 import 運用原記録
from .知識資産 import 知識を形成

移行版 = "HDS旧保存明示移行-v1"
# 由来: tests/資料/HDS旧保存/由来.json。各固定commitの実保存と照合済み。
_旧契約 = {
    "HDS-MINIDORA-全体運用-v5": ("8b09407ac5166e5295549a3a15eb3b690ef873ae0a7e8f324887fe13ad99d367", "49949048d6c20d991caf81025f97b9204505907c"),
    "HDS-MINIDORA-全体運用-v4": ("73009636f3a9ecf084e9de56bd70511ac8ecef53a32122d926814ab7e29a6d6d", "09043dc222ecda52996e9dc0e53ad9c5a809c27e"),
    "HDS-MINIDORA-全体運用-v1": ("516e70fdebaa72ed71fd1674a2c7322a7ac22b4a2b76afc50a65bbd9c013c315", "2d08bd1cb9de343cd2725430fc80eda80d47fb73"),
    "HDS-MINIDORA-全体運用-v2": ("1305b1a665ef9b2de804f6d179751224e2fff024b14a88389adb25d016a0909f", "6820ee8670081c9f2aecb4d8b5a1b3ad80419fb2"),
    "HDS-MINIDORA-全体運用-v3": ("fe78c448f8482c1628aa9b97c0f94042a7af13fafc01e136e6f664d68c717c20", "4f303059c17044f038d4b5340d4c240373cf6f38"),
}
_共通欄 = {"版", "セッションID", "目録", "外部読取許可", "最大作用回数", "最大発話", "資料", "旧資料",
          "前回目的", "保留目的", "前回結果", "前回依存", "焦点有効", "発話", "経験"}
_v2欄 = {"原記録", "知識資産", "形成手順", "手順形成", "前回知識範囲"}


def _旧資料を検査(名前, 資料):
    名前を確認(名前)
    if type(資料) is not dict or set(資料) != {"種類", "本文", "データ", "版", "結果"}:
        raise ValueError("旧資料の欄不一致")
    if (資料["種類"] not in ("資料", "知識", "本文", "命題", "仮説", "介入")
            or type(資料["本文"]) is not str or len(資料["本文"]) > 100000 or type(資料["データ"]) is not dict):
        raise ValueError("旧資料の種類・型・上限不正")
    if 資料["版"] != 指紋({鍵: 資料[鍵] for 鍵 in ("種類", "本文", "データ")}):
        raise ValueError("旧資料の本文・版不一致")
    参照 = 参照資料("運用資料:" + 名前 + ":" + 資料["版"], 名前,
                  "利用者提供" + 資料["種類"], 本文=資料["本文"])
    期待 = 能力結果(True, 資料["本文"], 参照=(参照,), データ=資料["データ"])
    if 指紋(結果を保存(期待)) != 指紋(資料["結果"]):
        raise ValueError("旧資料の本体・結果不一致")


def _旧保存を読む(原本, *, 深さ=0):
    if 深さ > 3:
        raise ValueError("旧保存履歴の入れ子上限")
    if type(原本) is not str:
        raise ValueError("旧保存原本はUTF-8文字列が必要")
    状態 = 開封(JSONを厳格に読む(原本, 最大バイト数=16000000))
    if type(状態) is not dict or 状態.get("版") not in _旧契約:
        raise ValueError("対応する旧保存版はv1・v2・v3・v4・v5です")
    追加 = set() if 状態["版"].endswith("-v1") else _v2欄
    if 状態["版"].endswith(("-v4", "-v5")):
        追加 = 追加 | {"移行履歴"}
    if set(状態) != _共通欄 | 追加:
        raise ValueError("旧保存の欄不一致")
    if 状態["目録"] != _旧契約[状態["版"]][0]:
        raise ValueError("未確認の旧能力契約です。独自追加能力の自動移行は行いません")
    if type(状態["資料"]) is not dict or len(状態["資料"]) > 32:
        raise ValueError("旧保存資料の型・件数不正")
    if type(状態["旧資料"]) is not list or len(状態["旧資料"]) > 32:
        raise ValueError("旧保存履歴の型・件数不正")
    for 名前, 資料 in 状態["資料"].items():
        _旧資料を検査(名前, 資料)
    for 行 in 状態["旧資料"]:
        if type(行) is not dict or set(行) != {"名前", "種類", "本文", "データ", "版", "結果"}:
            raise ValueError("旧保存履歴の資料構造不正")
        _旧資料を検査(行["名前"], {鍵: 値 for 鍵, 値 in 行.items() if 鍵 != "名前"})
    if 状態["版"].endswith(("-v4", "-v5")):
        上限 = 4 if 状態["版"].endswith("-v4") else 5
        許容版 = {"HDS-MINIDORA-全体運用-v" + str(番号) for 番号 in range(1, 上限)}
        if (type(状態["移行履歴"]) is not list or any(type(行) is not dict or 行.get("旧版") not in
                許容版 for 行 in 状態["移行履歴"])):
            raise ValueError("v" + str(上限) + "当時に存在しない移行履歴")
        移行履歴を検査(状態["移行履歴"], 深さ=深さ + 1)
    return 状態


def 移行履歴を検査(履歴, *, 深さ=0):
    if 深さ > 3:
        raise ValueError("旧保存履歴の入れ子上限")
    if type(履歴) is not list or len(履歴) > 1:
        raise ValueError("移行履歴の型・件数不正")
    for 行 in 履歴:
        if type(行) is not dict or set(行) != {"版", "旧版", "旧目録", "由来commit", "原本", "原本SHA256", "方針"} or 行["版"] != 移行版:
            raise ValueError("移行履歴の欄・版不一致")
        旧 = _旧保存を読む(行["原本"], 深さ=深さ)
        if (行["旧版"] != 旧["版"] or 行["旧目録"] != 旧["目録"]
                or 行["由来commit"] != _旧契約[旧["版"]][1]
                or 行["原本SHA256"] != sha256(行["原本"].encode()).hexdigest()
                or 行["方針"] != "旧原本と履歴・依存を保持。旧成果を失効し、旧形成手順を再実行対象から外す"):
            raise ValueError("移行履歴の原本・方針が不整合")


def _v1原記録(状態):
    # v1には原記録庫が存在しない。残っている旧版列と現行資料から新設する。
    # 失われた過去や生成時刻は補完しない。元の記録は移行原本に残る。
    庫 = 運用原記録(状態["セッションID"])
    仮資料 = {}
    for 行 in [*状態["旧資料"], *({"名前": 名, **値} for 名, 値 in sorted(状態["資料"].items()))]:
        if type(行) is not dict or set(行) != {"名前", "種類", "本文", "データ", "版", "結果"}:
            raise ValueError("v1旧資料の構造不正")
        名前 = 行["名前"]
        資料 = {鍵: 値 for 鍵, 値 in 行.items() if 鍵 != "名前"}
        庫 = 庫.同期候補({"資料": 仮資料}, {"行為": "更新" if 名前 in 仮資料 else "登録", "名前": 名前, "資料": 資料}, None, {})
        仮資料[名前] = deepcopy(資料)
    庫.資料を照合(状態["資料"])
    return 庫


def 旧保存を移行(原本, *, 外部読取許可=False, 取得器=None):
    """元の文字列を変更せず、新セッションを返す。外部通信・能力実行はしない。"""
    from .セッション import HDS運用セッション
    from .手順形成 import 手順資産を検査
    旧 = _旧保存を読む(原本)
    if 旧["外部読取許可"] is not 外部読取許可:
        raise ValueError("保存データから外部権限を移行しない。呼出側設定との一致が必要")
    新 = deepcopy(旧)
    試用 = HDS運用セッション(旧["セッションID"], 外部読取許可=外部読取許可, 取得器=取得器,
                          最大作用回数=旧["最大作用回数"], 最大発話=旧["最大発話"], 手順形成=旧.get("手順形成", False))
    # 新復元器の資料・回答・履歴検査を先に通すため、v1の欠落欄を明示構成する。
    if 旧["版"].endswith("-v1"):
        庫 = _v1原記録(旧)
        新.update(原記録=庫.保存(), 知識資産={名: 知識を形成(名, 値) for 名, 値 in 旧["資料"].items() if 値["種類"] == "知識"},
                 形成手順={}, 手順形成=False, 前回知識範囲=None)
    else:
        庫 = 運用原記録.復元(旧["原記録"], 旧["セッションID"])
        庫.資料を照合(旧["資料"])
        if type(旧["形成手順"]) is not dict or len(旧["形成手順"]) > 64:
            raise ValueError("旧形成手順の型・上限不正")
        # 検証対象は記録契約のみ。旧コードや手順を実行しない。
        from .関係接続 import 関係能力名
        除外 = set() if 旧["版"].endswith("-v5") else set(関係能力名)
        if not 旧["版"].endswith(("-v4", "-v5")):
            除外 |= {"資料意味選択", "取得資料意味選択", "資料内容構成", "資料文章照合", "資料文章再表現"}
        if 旧["版"].endswith("-v2"):
            除外 |= {"数量文構文化", "数量式評価", "数量コード仕様", "数量コード実行", "数量結果照合", "数量回答構成", "数量回答再表現"}
        検証用 = SimpleNamespace(ハッシュ=旧["目録"], _純粋=試用.目録._純粋 - 除外, 取得=試用.目録.取得)
        for 鍵, 手順 in 旧["形成手順"].items():
            手順資産を検査(手順, 検証用)
            if 手順["目的鍵"] != 鍵:
                raise ValueError("旧手順の索引不一致")
    失効 = []
    for 事象 in 庫.保存()["庫"]["履歴"]:
        for 行 in 事象["追加"]:
            if 行["種別"] == "成果" and 庫.庫.原記録(行["識別子"])["現行"]:
                失効.append(行["識別子"])
    for 開始 in range(0, len(失効), 128):
        庫.庫.更新(庫.庫.起点(), 失効ID=tuple(失効[開始:開始+128]), 理由="保存移行で能力契約が変更。旧成果は履歴のみ")
    新.update(版=運用版, 目録=試用.目録.ハッシュ, 原記録=庫.保存(), 焦点有効=False, 形成手順={})
    新["移行履歴"] = [{"版": 移行版, "旧版": 旧["版"], "旧目録": 旧["目録"], "由来commit": _旧契約[旧["版"]][1],
                       "原本": 原本, "原本SHA256": sha256(原本.encode()).hexdigest(),
                       "方針": "旧原本と履歴・依存を保持。旧成果を失効し、旧形成手順を再実行対象から外す"}]
    移行履歴を検査(新["移行履歴"])
    文字列 = json.dumps(封緘(新), ensure_ascii=False, allow_nan=False)
    # 全資料・結果・依存・知識資産等は現行復元器でも再検査する。
    return HDS運用セッション.復元(文字列, 外部読取許可=外部読取許可, 取得器=取得器)

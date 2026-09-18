"""原資料の関係・実導出・未確認前提を保持する。資料間の同名を自動同一化しない。"""
from __future__ import annotations
from dataclasses import asdict
from ..命題句 import 構成句を分ける
from ..命題構造 import 命題記載, 命題を復元, 原子群
from ..知識取得 import 知識取得要求
from ..命題推論 import 命題推論器, 推論上限
from ..導出説明 import 導出説明を構成
from ..製品版.型 import 能力結果
from .値 import 正準, 指紋, 結果を保存, 結果を復元
from .関係言語 import 関係文を読む
from .一般接続 import 取得資料を復元

関係要求版 = "HDS関係説明要求-v2"
_旧要求版 = "HDS関係説明要求-v1"
関係読解版 = "HDS関係読解-v2"
_旧読解版 = "HDS関係読解-v1"
_形式 = ("箇条書き", "文章", "引用")


def 関係要求の読解器(要求):
    if 要求["版"] == _旧要求版:
        return 関係文を読む
    from .関係構文化 import 関係文を読む as 新読解
    return 新読解


def 関係要求を検査(要求):
    if (type(要求) is not dict or set(要求) != {"版", "対象", "範囲", "問い", "形式", "不足調査", "最大文字数"}
            or 要求["版"] not in (関係要求版, _旧要求版)):
        raise ValueError("関係要求の型・欄・版不一致")
    群 = 要求["対象"]
    if (type(群) is not list or len(群) > 8 or any(type(名) is not str or not 名.strip() or len(名) > 128 for 名 in 群)
            or len(set(群)) != len(群)):
        raise ValueError("関係要求の資料名・件数不正")
    if 要求["範囲"] not in ("指定資料", "全資料") or (要求["範囲"] == "指定資料") != bool(群):
        raise ValueError("関係要求の資料範囲不一致")
    if 要求["形式"] not in _形式 or type(要求["不足調査"]) is not bool:
        raise ValueError("関係要求の形式・調査許可不正")
    if type(要求["最大文字数"]) is not int or not 100 <= 要求["最大文字数"] <= 24000:
        raise ValueError("関係回答の文字予算は100〜24000")
    式, _, _ = 関係要求の読解器(要求)(要求["問い"])
    if 要求["不足調査"] and len(要求["問い"]) > 512:
        raise ValueError("公開調査の問いは512文字以内")
    if 式.種別 not in ("原子", "否定", "含意", "連言", "選言", "全称", "存在", "帰属"):
        raise ValueError("問いの意味構造が未対応")
    return 正準(要求)


def 関係調査要求(要求):
    問い, _, _ = 関係要求の読解器(要求)(要求["問い"])
    原子列 = tuple(原子群(問い))
    語 = tuple(dict.fromkeys(項.名前 for 式 in 原子列 for 項 in 式.項 if 項.種別 == "定数"))
    if not 語:
        語 = tuple(dict.fromkeys(式.述語 for 式 in 原子列))
    結果 = 知識取得要求(検索語=要求["問い"], 必要語=語[:8], 最大検索回数=2, 最大候補数=4,
                        最大取得数=4, 最大資料数=3, 最大抜粋文字数=12000)
    結果.検証()
    return 結果


def _一資料(名前, 資料, 問い):
    if not isinstance(資料, 能力結果) or not 資料.成立 or not 0 < len(資料.本文) <= 16000:
        raise ValueError("関係読解の資料型・成立・文字上限")
    # 作用域不明の例外は、同一資料の先行断定を含めて推論への採用を止める。
    # 知らない留保を消して結論するより、原文ごと確認対象へ戻す。
    限定 = any(語 in 資料.本文 for 語 in ("ただし", "除く", "除き", "限り", "例外", "のみ"))
    区間 = list(構成句を分ける(資料.本文))
    if len(区間) > 64:
        raise ValueError("関係資料の記載数上限")
    記載, 読解, 残差 = [], [], []
    先行 = None
    for 番号, (開始, 終了) in enumerate(区間):
        原文 = 資料.本文[開始:終了]
        if 原文.strip().startswith("#"):
            先行 = None
            残差.append({"範囲": [開始, 終了], "原文": 原文, "理由": "見出し（参照範囲を再開）"})
            continue
        try:
            式, 先行, 変換 = 関係文を読む(原文, 先行主体=先行)
            識別子 = "記載" + str(番号)
            記載.append(命題記載(識別子, 式, 名前, 原文, (開始, 終了)))
            読解.append({"識別子": 識別子, "範囲": [開始, 終了], "原文": 原文,
                         "式": 式.辞書(), "変換": 変換})
        except ValueError as 例外:
            先行 = None
            残差.append({"範囲": [開始, 終了], "原文": 原文, "理由": str(例外)})
    採用 = () if 限定 else tuple(記載)
    推論器 = 命題推論器(採用, 上限=推論上限(操作数=12000, 事実数=256, 項数=48, 根拠数=1024)) if 採用 else None
    判定 = 推論器.判定(問い) if 推論器 is not None else {
        "判定": "未確定", "問い": 問い.辞書(), "支持": None, "反証": None, "導出": {}, "操作数": 0,
        "解釈境界": "採用可能な記載がないため推論を行っていない。問いの否定ではない。"}
    説明 = 導出説明を構成(判定, [asdict(項) for 項 in 採用])
    不足 = []
    # 後件から前件を事実推論しない。既存ルールを使う場合の確認候補だけを得る。
    if 判定["判定"] != "支持":
        for 項 in 採用:
            if 項.式.種別 != "含意" or 項.式.子[1].鍵() != 問い.鍵():
                continue
            前件 = 項.式.子[0]
            前判定 = 推論器.判定(前件)
            if 前判定["判定"] != "支持":
                不足.append({"規則記載": 項.識別子, "前件": 前件.辞書(), "判定": 前判定["判定"],
                             "位置づけ": "この導出経路を使う場合の確認候補。事実・必要条件とは未認定"})
    return {"資料": 結果を保存(資料), "読解": 読解, "残差": 残差,
            "限定隔離": 限定, "判定": 判定, "説明": 説明, "不足候補": 不足,
            "解釈状態": "限定作用域の確認待ち" if 限定 else "部分解釈" if 残差 else "対応文法内の解釈成立"}


def 不足調査が必要(構造):
    return any(行["限定隔離"] or 行["残差"] or 行["判定"]["判定"] != "支持"
               or any(not 項["採用"] for 項 in 行.get("例外監査", ())) for 行 in 構造["資料群"].values())


def 関係資料を読む(資料群, 要求, *, 取得=None):
    要求 = 関係要求を検査(要求)
    if (type(資料群) is not dict or not 1 <= len(資料群) <= 8
            or any(type(名) is not str or not 名 or len(名) > 128 for 名 in 資料群)):
        raise ValueError("関係資料の名前・件数不正")
    if 要求["範囲"] == "指定資料" and set(資料群) != set(要求["対象"]):
        raise ValueError("関係要求と資料の対応不一致")
    if any(not isinstance(値, 能力結果) or not 値.成立 or type(値.本文) is not str for 値 in 資料群.values()):
        raise ValueError("関係資料の結果型・成立不正")
    if sum(len(値.本文) for 値 in 資料群.values()) > 32000:
        raise ValueError("関係資料の合計文字数上限")
    問い, _, 変換 = 関係要求の読解器(要求)(要求["問い"])
    新版 = 要求["版"] == 関係要求版
    from .関係条件読解 import 関係条件資料を読む
    一資料 = 関係条件資料を読む if 新版 else _一資料
    結果 = {"版": 関係読解版 if 新版 else _旧読解版, "要求": 要求, "問い式": 問い.辞書(), "問い変換": 変換,
          "資料群": {名: 一資料(名, 値, 問い) for 名, 値 in sorted(資料群.items())},
          "公開資料群": {}, "取得": None, "取得状態": "未要求"}
    if 取得 is not None:
        if not 要求["不足調査"]:
            raise ValueError("公開調査を要求していない")
        if not isinstance(取得, 能力結果):
            raise ValueError("取得の結果型不正")
        # 外部読取自体の不成立も観測として保存。失敗を知識成立へ変えない。
        if 取得.成立:
            if 正準(取得.データ.get("要求")) != 正準(asdict(関係調査要求(要求))):
                raise ValueError("取得記録と質問の対応不一致")
            公開 = 取得資料を復元(取得)
            if len(公開) > 3 or sum(len(値.本文) for 値 in 公開.values()) > 32000:
                raise ValueError("公開関係資料の容量上限")
            結果["公開資料群"] = {名: 一資料(名, 値, 問い) for 名, 値 in sorted(公開.items())}
        結果["取得"] = 結果を保存(取得)
        結果["取得状態"] = "取得済（意味的十分性は別判定）" if 取得.成立 else "取得不成立"
    elif 要求["不足調査"]:
        結果["取得状態"] = "必要" if 不足調査が必要(結果) else "不要"
    結果["境界"] = "資料ごとの読めた記載における支持・反証。資料間の同名対象、時点・条件の同一性や世界の真偽を認定しない。条件適用は現実の因果検証ではない。"
    return 正準(結果)


def 関係資料を検査(構造):
    try:
        if type(構造) is not dict or 構造.get("版") not in (関係読解版, _旧読解版):
            return False
        再 = 関係資料を読む({名: 結果を復元(行["資料"]) for 名, 行 in 構造["資料群"].items()},
                        構造["要求"], 取得=None if 構造["取得"] is None else 結果を復元(構造["取得"]))
        return 指紋(再) == 指紋(構造)
    except (ValueError, TypeError, KeyError, AttributeError, RecursionError, OverflowError):
        return False

"""資料の見出し・明示別名・原文区間を用いる選択。語の一致を真偽判定にしない。"""
from __future__ import annotations
from copy import deepcopy
from dataclasses import asdict
import re
import unicodedata
from ..製品版.型 import 能力結果
from .一般依頼 import 一般要求を検査
from .値 import 正準, 指紋, 結果を保存, 結果を復元

意味資料版 = "HDS資料意味選択-v1"
_条件 = re.compile(r'ただし|但し|除く|除外|例外|限り|場合|条件|時点|現在|以前|以後|以降|まで|未確認|不明|保証|可能性|推定|仮定|共通|適用|注意|誤り|虚構|引用|否定|しない|ではない|禁止|異なる|無効')
_別名 = re.compile(r'(?:「(?P<左引用>[^「」\n]{1,80})」|(?P<左>[^。\n「」]{1,80}?))は(?:「(?P<右引用>[^「」\n]{1,80})」|(?P<右>[^。\n「」]{1,80}?))とも(?:呼ぶ|呼ばれる|いう|言う)[。\n]')


def _正規化(文):
    return unicodedata.normalize("NFKC", 文).casefold()


def 資料を区分(本文):
    """空行を含む節の原文を保持。見出しは局所ATX構文として扱う。"""
    if type(本文) is not str or not 本文.strip() or len(本文) > 100000:
        raise ValueError("資料本文は1〜100000文字です")
    本文.encode("utf-8")
    if any(unicodedata.category(字) in ("Cf", "Cs", "Zl", "Zp") or
           unicodedata.category(字) == "Cc" and 字 not in '\t\n\r' for 字 in 本文):
        raise ValueError("未対応制御文字を削除せず保留")
    節群, 階層, 開始, 位置 = [], [], 0, 0
    現階層, 引用, 囲い = [], [], None
    括弧 = {"「": "」", "『": "』", "（": "）"}
    for 行 in 本文.splitlines(keepends=True):
        枠 = re.fullmatch(r"[ ]{0,3}(`{3,}|~{3,})[^\r\n]*\r?\n?", 行)
        if 枠 and not 引用:
            if 囲い is None:
                囲い = 枠[1]
            elif 枠[1][0] == 囲い[0] and len(枠[1]) >= len(囲い):
                囲い = None
            位置 += len(行)
            continue
        if 囲い is not None:
            位置 += len(行)
            continue
        引用中 = bool(引用)
        for 字 in 行:
            if 字 in 括弧:
                引用.append(括弧[字])
            elif 字 in 括弧.values():
                if not 引用 or 引用.pop() != 字:
                    raise ValueError("資料の引用境界が不整合です")
        見出し = None if 引用中 else re.fullmatch(r'(#{1,6})[ \t]+([^\r\n]+)\r?\n?', 行)
        if 見出し:
            if 位置 > 開始 and 本文[開始:位置].strip():
                節群.append({"開始": 開始, "終了": 位置, "階層": deepcopy(現階層)})
            深さ = len(見出し[1])
            階層 = [項 for 項 in 階層 if 項["深さ"] < 深さ]
            階層.append({"深さ": 深さ, "開始": 位置, "終了": 位置 + len(行), "見出し": 見出し[2]})
            開始, 現階層 = 位置, deepcopy(階層)
        位置 += len(行)
    if 引用 or 囲い is not None:
        raise ValueError("閉じていない引用・コード領域を切断せず保留")
    if 位置 > 開始 and 本文[開始:位置].strip():
        節群.append({"開始": 開始, "終了": 位置, "階層": 現階層})
    if not 1 <= len(節群) <= 128:
        raise ValueError("資料の節数は1〜128です")
    return 節群


def _語展開(主題, 本文):
    """別名は同じ資料内の明示宣言だけから得る。別資料の同一性には転用しない。"""
    対 = []
    for 一致 in _別名.finditer(本文 + ("\n" if not 本文.endswith(("。", "\n")) else "")):
        前境界 = max(本文.rfind("。", 0, 一致.start()), 本文.rfind("\n", 0, 一致.start())) + 1
        if 本文[前境界:一致.start()].strip():
            continue
        左, 右 = (一致["左引用"] or 一致["左"]).strip(), (一致["右引用"] or 一致["右"]).strip()
        if any(_条件.search(項) for 項 in (左, 右)):
            continue
        対.append((左, 右, 一致.start(), min(一致.end(), len(本文))))
    if len(対) > 64:
        raise ValueError("資料の別名宣言数上限")
    語, 根拠, 未処理 = {主題}, [], [主題]
    while 未処理:
        項 = 未処理.pop()
        for 左, 右, 開始, 終了 in 対:
            # 部分文字列置換は「寿命」と「設計寿命」の意味を潰すためしない。
            次 = 右 if _正規化(項) == _正規化(左) else 左 if _正規化(項) == _正規化(右) else None
            if 次 and 次 not in 語:
                語.add(次); 未処理.append(次)
                根拠.append({"開始": 開始, "終了": 終了, "左": 左, "右": 右})
                if len(語) > 16:
                    raise ValueError("別名展開の上限。切断して確定しない")
    return sorted(語), 根拠


def 資料意味を選ぶ(資料, 要求, *, 取得記録=None):
    要求 = 一般要求を検査(要求)
    if type(資料) is not dict or not 1 <= len(資料) <= 16:
        raise ValueError("一般文章の資料数は1〜16です")
    if sum(len(項.本文) for 項 in 資料.values()) > 200000:
        raise ValueError("一般文章の資料総量上限")
    if 要求["範囲"] == "指定資料" and list(資料) != 要求["対象"]:
        raise ValueError("一般文章の要求対象と素材の順序・集合が不一致")
    if 要求["範囲"] != "指定資料":
        資料 = {名: 資料[名] for 名 in sorted(資料)}
    if (取得記録 is not None) != (要求["範囲"] == "公開取得"):
        raise ValueError("取得記録と要求範囲が不一致")
    if 取得記録 is not None:
        from .一般接続 import 取得資料を復元
        参照群 = tuple(参照 for 項 in 資料.values() for 参照 in 項.参照)
        再資料 = 取得資料を復元(能力結果(True, "", 参照=参照群, データ=取得記録))
        if (set(再資料) != set(資料) or 取得記録["要求"]["検索語"] != 要求["主題"][0]
                or list(取得記録["要求"]["必要語"]) != 要求["主題"]
                or any(結果を保存(再資料[名]) != 結果を保存(資料[名]) for 名 in 資料)):
            raise ValueError("取得要求・資料の対応が不一致")
    記録, 被覆, 採用数 = {}, [], 0
    for 名前, 項 in 資料.items():
        if (type(名前) is not str or not 名前.strip() or len(名前) > 256
                or not isinstance(項, 能力結果) or not 項.成立):
            raise ValueError("資料名・成立状態の不正")
        本文 = 項.本文
        節群 = 資料を区分(本文)
        主題別, 一致節, 別名根拠 = [], set(), []
        for 主題 in 要求["主題"]:
            語群, 根拠 = _語展開(主題, 本文)
            一致 = [番号 for 番号, 節 in enumerate(節群) if any(
                _正規化(語) in _正規化(本文[節["開始"]:節["終了"]]) for 語 in 語群)]
            一致節.update(一致); 別名根拠.extend(根拠)
            主題別.append({"主題": 主題, "展開語": 語群, "一致節": 一致, "別名根拠": 根拠})
            被覆.append({"資料": 名前, "主題": 主題, "記載一致": bool(一致)})
        if not 要求["主題"]:
            一致節.update(range(len(節群)))
        同伴節 = set()
        if 一致節:
            for 番号, 節 in enumerate(節群):
                部分 = 本文[節["開始"]:節["終了"]]
                # 文書冒頭と明示条件・例外・時点の節を同伴。主題への適用を断定しない。
                if not 節["階層"] or _条件.search(部分) or any(節["開始"] <= 証拠["開始"] < 節["終了"] for 証拠 in 別名根拠):
                    同伴節.add(番号)
                # 選択節の親見出しが持つ前文も落とさない。
                if any(節["階層"] and len(節["階層"]) < len(節群[子]["階層"])
                       and 節["階層"] == 節群[子]["階層"][:len(節["階層"])] for 子 in 一致節):
                    同伴節.add(番号)
        選択 = sorted(一致節 | 同伴節)
        採用数 += len(選択)
        if 採用数 > 40:
            raise ValueError("条件を同伴した選択が40節を超えます。資料範囲を絞ってください")
        記録[名前] = {"資料": 結果を保存(項), "節": 節群, "主題対応": 主題別,
                     "一致節": sorted(一致節), "同伴節": sorted(同伴節 - 一致節), "選択": 選択,
                     "未選択": [番号 for 番号 in range(len(節群)) if 番号 not in 選択]}
    if not 採用数:
        raise ValueError("資料不足:指定した主題の記載を特定できません。別名又は資料を明示してください")
    構造 = {"版": 意味資料版, "要求": 要求, "資料群": 記録, "被覆": 被覆,
             "取得記録": 取得記録,
             "境界": "原文の記載一致・明示別名・見出し関係。世界事実の検証、同名対象の同一性、語義の一意性は確定しない"}
    return 正準(構造)


def 意味資料を検査(構造):
    try:
        if type(構造) is not dict or 構造.get("版") != 意味資料版:
            return False
        群 = {名: 結果を復元(値["資料"]) for 名, 値 in 構造["資料群"].items()}
        # JSON正準化は辞書順を並べ替えるため要求順で復元する。
        if 構造["要求"]["範囲"] == "指定資料":
            群 = {名: 群[名] for 名 in 構造["要求"]["対象"]}
        return 指紋(構造) == 指紋(資料意味を選ぶ(群, 構造["要求"], 取得記録=構造["取得記録"]))
    except (ValueError, TypeError, KeyError, AttributeError, RecursionError):
        return False

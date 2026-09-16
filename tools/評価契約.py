from __future__ import annotations

import hashlib
import json
from typing import Any


契約形式 = 'minidora.外部評価.契約.v2'
GPQA実参照E2E識別子 = "gpqa-diamond-e2e-live-v2"
GPQA正本全問題数 = 198
GPQA正本資料集合CSV_SHA256 = "41d1213cd7a4998605a26c2798500652572007161b3a92817ba46b35befcd305"
GPQA正本選択肢シャッフル種 = 0
GPQA正本OpenAlex有効 = False
GPQA正本Wikipedia言語群 = ("en",)


def _正本SHA256(payload: Any) -> str:
    raw = json.dumps(
        payload,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
    return hashlib.sha256(raw).hexdigest()


def GPQA正本手順を検証(protocol: dict[str, Any]) -> tuple[str, ...]:
    """GPQA正本E2Eの外部評価条件を検査する。

    固定するのは問題集合・seed・参照経路の構成であり、検索結果そのものではない。
    参照結果をrun間で固定・再生することは正本GPQAでは禁止する。
    """
    errors: list[str] = []
    if protocol.get("資料集合CSV_SHA256") != GPQA正本資料集合CSV_SHA256:
        errors.append("GPQA dataset hashが正本値と一致しない")
    if protocol.get("全問題数") != GPQA正本全問題数:
        errors.append("GPQA総問題数が198ではない")
    if protocol.get("選択番号群") != list(range(GPQA正本全問題数)):
        errors.append("GPQA正本は198/198全数実行でなければならない")
    if protocol.get("選択肢シャッフル種") != GPQA正本選択肢シャッフル種:
        errors.append('選択肢 shuffle seedが0ではない')
    if bool(protocol.get("OpenAlex有効")) != GPQA正本OpenAlex有効:
        errors.append("OpenAlex条件が正本条件と一致しない")
    if tuple(protocol.get("Wikipedia言語群", ())) != GPQA正本Wikipedia言語群:
        errors.append("Wikipedia言語条件が正本条件と一致しない")
    if not bool(protocol.get("統制AB")):
        errors.append("正本GPQAは同一run内controlled A/Bを必須とする")
    return tuple(errors)


def GPQA実参照E2E契約(protocol: dict[str, Any]) -> dict[str, Any]:
    errors = GPQA正本手順を検証(protocol)
    if errors:
        raise ValueError("; ".join(errors))

    condition = {
        "資料集合CSV_SHA256": protocol.get("資料集合CSV_SHA256"),
        "全問題数": protocol.get("全問題数"),
        "選択番号群": protocol.get("選択番号群"),
        "選択肢シャッフル種": protocol.get("選択肢シャッフル種"),
        "OpenAlex有効": bool(protocol.get("OpenAlex有効")),
        "Wikipedia言語群": protocol.get("Wikipedia言語群", []),
        "統制AB": bool(protocol.get("統制AB")),
        "参照方式": "LIVE_ONLY",
    }
    return {
        "契約形式": 契約形式,
        "外部評価識別子": GPQA実参照E2E識別子,
        "課題": "GPQA Diamond",
        "評価種別": "GENERIC_E2E_CANONICAL",
        "入力境界": "question + choices + references newly retrieved during this run",
        "参照方式": "LIVE_ONLY",
        "固定参照資料許可": False,
        "条件指紋SHA256": _正本SHA256(condition),
        "入力スナップショットSHA256": None,
        "正本全数実行": True,
        "正本得点欄": "metrics.correct",
        "同一実行内統制AB直接比較": True,
        "実行間コード差直接比較": False,
        "スナップショット得点時系列保存許可": True,
        "主張可能範囲": [
            "同一の正本GPQA運用規則で、その実行時点の外部参照環境を含めた汎用E2E性能スナップショット",
            "同一run内controlled A/Bは、そのrunで取得した同一資料を共有するため直接差分として扱える",
            "同一正本運用規則で得た各runの得点は時系列セーブポイントとして保持できる",
        ],
        "禁止主張": [
            '保存済み参照結果・C2・再生 bundle等の固定参照資料をGPQA正本性能評価へ利用すること',
            "部分実行値をGPQA正本性能として採用すること",
            "異なる日時のLIVE run間の得点差をコード変更だけの因果差とみなすこと",
        ],
    }


def 直接比較判定(left: dict[str, Any], right: dict[str, Any]) -> tuple[bool, str]:
    l = left.get("評価契約") or left
    r = right.get("評価契約") or right
    if l.get("契約形式") != 契約形式 or r.get("契約形式") != 契約形式:
        return False, '外部評価 契約 v2が両結果に存在しない'
    if l.get("外部評価識別子") != r.get("外部評価識別子"):
        return False, '外部評価_idが異なる'
    if l.get("評価種別") != "GENERIC_E2E_CANONICAL" or r.get("評価種別") != "GENERIC_E2E_CANONICAL":
        return False, "GPQA正本以外の評価種別は直接比較対象外"
    if l.get("固定参照資料許可") is not False or r.get("固定参照資料許可") is not False:
        return False, '固定参照資料を許可したGPQA結果は正本比較対象外'
    return False, "LIVE参照取得を含むため別run間をコード変更だけの直接差分にはできない。得点は時系列E2Eセーブポイントとして扱う"


def 契約を付与(結果: dict[str, Any], 契約: dict[str, Any]) -> dict[str, Any]:
    out = dict(結果)
    out["評価契約"] = 契約
    return out

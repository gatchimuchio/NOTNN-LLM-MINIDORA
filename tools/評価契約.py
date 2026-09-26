from __future__ import annotations

import hashlib
import json
from typing import Any


契約形式 = "minidora.外部評価.契約.v3"
GPQA実参照E2E識別子 = "gpqa-diamond-e2e-live-v3"
GPQA正本全問題数 = 198
GPQA正本資料集合CSV_SHA256 = "41d1213cd7a4998605a26c2798500652572007161b3a92817ba46b35befcd305"
GPQA正本選択肢シャッフル種 = 0
GPQA正本OpenAlex有効 = False
GPQA正本EuropePMC有効 = True
GPQA正本Crossref有効 = True
GPQA正本Wikipedia言語群 = ("en",)
GPQA正本中核入口 = "HDS駆動コア.選択実行"


def _正本SHA256(payload: Any) -> str:
    raw = json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(raw).hexdigest()


def GPQA正本手順を検証(評価条件: dict[str, Any]) -> tuple[str, ...]:
    errors: list[str] = []
    if 評価条件.get("資料集合CSV_SHA256") != GPQA正本資料集合CSV_SHA256:
        errors.append("GPQA dataset hashが正本値と一致しない")
    if 評価条件.get("全問題数") != GPQA正本全問題数:
        errors.append("GPQA総問題数が198ではない")
    if 評価条件.get("選択番号群") != list(range(GPQA正本全問題数)):
        errors.append("GPQA正本は198/198全数実行でなければならない")
    if 評価条件.get("選択肢シャッフル種") != GPQA正本選択肢シャッフル種:
        errors.append("選択肢シャッフル種が0ではない")
    if bool(評価条件.get("OpenAlex有効")) != GPQA正本OpenAlex有効:
        errors.append("OpenAlex条件が正本条件と一致しない")
    if bool(評価条件.get("EuropePMC有効")) != GPQA正本EuropePMC有効:
        errors.append("Europe PMC条件が正本条件と一致しない")
    if bool(評価条件.get("Crossref有効")) != GPQA正本Crossref有効:
        errors.append("Crossref条件が正本条件と一致しない")
    if tuple(評価条件.get("Wikipedia言語群", ())) != GPQA正本Wikipedia言語群:
        errors.append("Wikipedia言語条件が正本条件と一致しない")
    if 評価条件.get("参照方式") != "LIVE_ONLY":
        errors.append("参照方式がLIVE_ONLYではない")
    if 評価条件.get("固定参照資料許可") is not False:
        errors.append("固定参照資料は禁止")
    if 評価条件.get("中核入口") != GPQA正本中核入口:
        errors.append("現行中核入口がHDS駆動コア.選択実行ではない")
    if 評価条件.get("問題束一問一形成") is not True:
        errors.append("問題束一問一形成が保証されていない")
    return tuple(errors)


def GPQA実参照E2E契約(評価条件: dict[str, Any]) -> dict[str, Any]:
    errors = GPQA正本手順を検証(評価条件)
    if errors:
        raise ValueError("; ".join(errors))
    condition = {
        "資料集合CSV_SHA256": 評価条件.get("資料集合CSV_SHA256"),
        "全問題数": 評価条件.get("全問題数"),
        "選択番号群": 評価条件.get("選択番号群"),
        "選択肢シャッフル種": 評価条件.get("選択肢シャッフル種"),
        "OpenAlex有効": bool(評価条件.get("OpenAlex有効")),
        "EuropePMC有効": bool(評価条件.get("EuropePMC有効")),
        "Crossref有効": bool(評価条件.get("Crossref有効")),
        "Wikipedia言語群": 評価条件.get("Wikipedia言語群", []),
        "参照方式": 評価条件.get("参照方式"),
        "固定参照資料許可": 評価条件.get("固定参照資料許可"),
        "中核入口": 評価条件.get("中核入口"),
        "問題束一問一形成": 評価条件.get("問題束一問一形成"),
    }
    return {
        "契約形式": 契約形式,
        "外部評価識別子": GPQA実参照E2E識別子,
        "課題": "GPQA Diamond",
        "評価種別": "CURRENT_INTEGRATED_KERNEL_CANONICAL",
        "入力境界": "question + choices + references newly retrieved during this run",
        "参照方式": "LIVE_ONLY",
        "固定参照資料許可": False,
        "中核入口": GPQA正本中核入口,
        "問題束一問一形成": True,
        "条件指紋SHA256": _正本SHA256(condition),
        "正本全数実行": True,
        "正本得点欄": "指標.正答",
        "同一実行内状態遷移記録許可": True,
        "実行間コード差直接比較": False,
        "スナップショット得点時系列保存許可": True,
        "主張可能範囲": [
            "同一の正本GPQA運用規則で、その実行時点の外部参照環境を含めた現行中核E2E性能スナップショット",
            "同一実行内で記録した初期継承状態から最終状態への遷移",
            "全198問で問題束を一問一形成したこと",
        ],
        "禁止主張": [
            "保存済み参照結果・再生束等の固定参照資料をGPQA正本性能評価へ利用すること",
            "部分実行値をGPQA正本性能として採用すること",
            "独立LIVE参照を用いる別実行またはpaired実行の得点差をコード変更だけの因果差とみなすこと",
        ],
    }


def 直接比較判定(left: dict[str, Any], right: dict[str, Any]) -> tuple[bool, str]:
    l = left.get("評価契約") or left
    r = right.get("評価契約") or right
    if l.get("契約形式") != 契約形式 or r.get("契約形式") != 契約形式:
        return False, "外部評価契約v3が両結果に存在しない"
    if l.get("外部評価識別子") != r.get("外部評価識別子"):
        return False, "外部評価識別子が異なる"
    if l.get("評価種別") != "CURRENT_INTEGRATED_KERNEL_CANONICAL" or r.get("評価種別") != "CURRENT_INTEGRATED_KERNEL_CANONICAL":
        return False, "現行中核正本以外の評価種別は比較対象外"
    if l.get("固定参照資料許可") is not False or r.get("固定参照資料許可") is not False:
        return False, "固定参照資料を許可した結果は正本比較対象外"
    return False, "LIVE参照取得を含むため別実行間をコード変更だけの直接差分にはできない。得点は時系列E2Eセーブポイントとして扱う"


def 契約を付与(結果: dict[str, Any], 契約: dict[str, Any]) -> dict[str, Any]:
    out = dict(結果)
    out["評価契約"] = 契約
    return out

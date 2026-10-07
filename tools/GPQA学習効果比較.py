from __future__ import annotations

import argparse
from math import comb
import json
from pathlib import Path

有意水準 = 0.05
全問題数 = 198
並列下限 = 43


def _読む(経路):
    return json.loads(Path(経路).read_text(encoding="utf-8"))


def _版(結果):
    return str(結果.get("リポジトリ版") or 結果.get("評価条件", {}).get("リポジトリ版") or "")


比較共通条件 = (
    "資料集合CSV_SHA256", "全問題数", "選択肢シャッフル種",
    "参照方式", "固定参照資料許可", "採点結果の学習利用",
    "中核入口", "問題束一問一形成", "OpenAlex有効", "EuropePMC有効",
    "Crossref有効", "Wikipedia言語群", "選択番号群",
)


def _共通条件を検査(並列, 直列):
    p = 並列.get("評価条件")
    s = 直列.get("評価条件")
    if not isinstance(p, dict) or not isinstance(s, dict):
        raise ValueError("並列・直列の評価条件が必要")
    for key in 比較共通条件:
        if p.get(key) != s.get(key) or type(p.get(key)) is not type(s.get(key)):
            raise ValueError("共通評価条件不一致:" + key)


def _個票(結果):
    rows = tuple(結果.get("個票", ()))
    if len(rows) != 全問題数:
        raise ValueError("198問の個票が必要")
    by_id = {}
    for row in rows:
        i = row.get("番号")
        if type(i) is not int or not 0 <= i < 全問題数 or i in by_id:
            raise ValueError("個票番号が不正")
        by_id[i] = row
    if set(by_id) != set(range(全問題数)):
        raise ValueError("0..197の全問題が必要")
    return by_id


def 二項片側有意確率(直列勝ち: int, 並列勝ち: int) -> float:
    if min(直列勝ち, 並列勝ち) < 0:
        raise ValueError("勝敗数は非負")
    n = 直列勝ち + 並列勝ち
    if n == 0 or 直列勝ち <= 並列勝ち:
        return 1.0
    return sum(comb(n, k) for k in range(直列勝ち, n + 1)) / (2 ** n)


def 比較(並列, 直列):
    p版, s版 = _版(並列), _版(直列)
    if not p版 or p版 != s版:
        raise ValueError("並列と直列は同一リポジトリ版が必要")
    _共通条件を検査(並列, 直列)
    p_rows, s_rows = _個票(並列), _個票(直列)

    p_score = sum(bool(p_rows[i].get("正答")) for i in range(全問題数))
    s_score = sum(bool(s_rows[i].get("正答")) for i in range(全問題数))
    p_complete = bool(並列.get("性能継承成立")) and p_score >= 並列下限
    s_complete = (
        直列.get("測定状態") == "完了"
        and bool(直列.get("実測", {}).get("全数完走"))
        and float(直列.get("実測", {}).get("経過秒", 10**9)) <= 90 * 60
    )
    直列勝ち = sum((not bool(p_rows[i].get("正答"))) and bool(s_rows[i].get("正答")) for i in range(全問題数))
    並列勝ち = sum(bool(p_rows[i].get("正答")) and (not bool(s_rows[i].get("正答"))) for i in range(全問題数))
    確率 = 二項片側有意確率(直列勝ち, 並列勝ち)

    学習状態更新 = any(
        str(s_rows[i].get("処理前継続状態署名", "")) != str(s_rows[i].get("処理後継続状態署名", ""))
        for i in range(全問題数)
    )
    後続適応 = any(
        int(s_rows[i].get("観測経路適応数", 0) or 0) > 0
        or int(s_rows[i].get("計装", {}).get("形成再利用数", 0) or 0) > 0
        for i in range(1, 全問題数)
    )
    成立 = bool(
        p_complete and s_complete and s_score > p_score
        and 確率 < 有意水準 and 学習状態更新 and 後続適応
    )
    return {
        "契約形式": "minidora.gpqa.learning-effect.v1",
        "リポジトリ版": p版,
        "全問題数": 全問題数,
        "並列正答": p_score,
        "直列正答": s_score,
        "差分": s_score - p_score,
        "直列のみ正答": 直列勝ち,
        "並列のみ正答": 並列勝ち,
        "不一致問数": 直列勝ち + 並列勝ち,
        "片側正確有意確率": 確率,
        "有意水準": 有意水準,
        "並列性能継承成立": p_complete,
        "直列全数時間内": s_complete,
        "学習状態更新": 学習状態更新,
        "後続適応観測": 後続適応,
        "学習実証成立": 成立,
    }


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--parallel", required=True)
    p.add_argument("--serial", required=True)
    p.add_argument("--out", required=True)
    a = p.parse_args()
    結果 = 比較(_読む(a.parallel), _読む(a.serial))
    Path(a.out).write_text(json.dumps(結果, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(結果, ensure_ascii=False, indent=2))
    return 0 if 結果["学習実証成立"] else 3


if __name__ == "__main__":
    raise SystemExit(main())

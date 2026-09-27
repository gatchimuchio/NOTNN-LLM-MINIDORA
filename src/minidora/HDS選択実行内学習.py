from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable, Mapping


HDS選択実行内学習版 = "HDS-SELECTION-RUNTIME-LEARNING-v2"


@dataclass(frozen=True, slots=True)
class HDS選択学習経験:
    ID: str
    参照署名: str
    結果状態: str
    回答ラベル: str | None
    残差: tuple[str, ...]
    理由: tuple[str, ...]
    候補差: tuple[tuple[str, float], ...] = ()


@dataclass(frozen=True, slots=True)
class HDS選択学習導出:
    経験ID: str
    観測要求: tuple[object, ...]
    未観測関係数: int
    矛盾関係数: int
    署名: str
    根拠経験ID群: tuple[str, ...] = ()
    導出理由: tuple[str, ...] = ()


def _候補差(結果: object) -> tuple[tuple[str, float], ...]:
    模型 = getattr(結果, "MINIDORA模型結果", None)
    if 模型 is None:
        return ()
    mapping = getattr(模型, "候補辞書", None)
    if callable(mapping):
        try:
            return tuple(sorted((str(k), float(v)) for k, v in dict(mapping()).items()))
        except (TypeError, ValueError):
            return ()
    return ()


def HDS選択学習経験を形成(
    結果: object,
    *,
    参照署名: str,
    残差: Iterable[str],
) -> HDS選択学習経験:
    from .コア.値 import 署名

    reasons = tuple(dict.fromkeys(str(x) for x in getattr(結果, "理由", ()) if str(x)))
    residuals = tuple(sorted({str(x) for x in 残差 if str(x)}))
    scores = _候補差(結果)
    payload = (
        str(参照署名),
        str(getattr(結果, "状態", "")),
        getattr(結果, "回答ラベル", None),
        residuals,
        reasons,
        scores,
    )
    return HDS選択学習経験(
        "経験:" + 署名(payload)[:24],
        str(参照署名),
        str(getattr(結果, "状態", "")),
        None if getattr(結果, "回答ラベル", None) is None else str(getattr(結果, "回答ラベル")),
        residuals,
        reasons,
        scores,
    )


def HDS選択学習経験を保持(
    既存: Iterable[HDS選択学習経験],
    経験: HDS選択学習経験,
) -> tuple[HDS選択学習経験, ...]:
    rows = list(既存)
    if not any(x.ID == 経験.ID for x in rows):
        rows.append(経験)
    return tuple(rows)


def HDS選択参照記憶を統合(既存: Iterable[object], 追加: Iterable[object]) -> tuple[object, ...]:
    """同一実行で観測した参照を失わず、同一識別子だけ最新版へ統合する。"""
    rows: list[object] = []
    index: dict[str, int] = {}
    for record in (*tuple(既存), *tuple(追加)):
        key = str(getattr(record, "識別子", ""))
        if not key:
            rows.append(record)
            continue
        if key in index:
            old = rows[index[key]]
            try:
                from dataclasses import replace
                conditions = tuple(dict.fromkeys((*tuple(getattr(old, "条件", ())), *tuple(getattr(record, "条件", ())))))
                rows[index[key]] = replace(
                    record,
                    条件=conditions,
                    信頼=max(float(getattr(old, "信頼", 0.0)), float(getattr(record, "信頼", 0.0))),
                )
            except (TypeError, ValueError):
                rows[index[key]] = record
            continue
        index[key] = len(rows)
        rows.append(record)
    return tuple(rows)


def _条件値(関係: object, key: str) -> str:
    prefix = key + "="
    for raw in tuple(getattr(関係, "条件", ())):
        text = str(raw)
        if text.startswith(prefix):
            return text[len(prefix):].strip()
    return ""


def _条件範囲(関係: object) -> tuple[tuple[str, str], ...]:
    meta = {"検索述語", "不足位置", "英日意味射影", "受動態", "選択意図", "選択問題閉包", "由来"}
    out: list[tuple[str, str]] = []
    for raw in tuple(getattr(関係, "条件", ())):
        key, sep, value = str(raw).partition("=")
        key, value = key.strip(), value.strip()
        if sep and key and value and key not in meta:
            item = (key, value)
            if item not in out:
                out.append(item)
    return tuple(out)


def _端点表層(ir: object, ids: Iterable[str]) -> tuple[str, ...]:
    coords = ir.座標辞書()
    out: list[str] = []
    seen: set[str] = set()
    for cid in ids:
        coord = coords.get(cid)
        if coord is None:
            continue
        value = " ".join(str(getattr(coord, "内容", "")).split()).strip()
        if not value:
            continue
        key = value.casefold()
        if key not in seen:
            seen.add(key)
            out.append(value)
    return tuple(out)


def _観測表層群(ir: object, 関係: object) -> tuple[str, ...]:
    left = _端点表層(ir, getattr(関係, "始点", ()))
    right = _端点表層(ir, getattr(関係, "終点", ()))
    predicate = _条件値(関係, "検索述語") or str(getattr(関係, "種別", ""))
    範囲値群 = tuple(v for _k, v in _条件範囲(関係))
    候補群 = (
        (*left, predicate, *right, *範囲値群),
        (predicate, *left, *right, *範囲値群),
        (*left, *right, *範囲値群),
    )
    out: list[str] = []
    seen: set[str] = set()
    for 候補 in 候補群:
        parts: list[str] = []
        for raw in 候補:
            value = " ".join(str(raw).split()).strip()
            if value and value.casefold() not in {x.casefold() for x in parts}:
                parts.append(value)
        surface = " ".join(parts)
        if surface and surface.casefold() not in seen:
            seen.add(surface.casefold())
            out.append(surface)
    return tuple(out)


def _内部言語体系(ir: object) -> str:
    lang = str(getattr(ir, "入力言語", "ja") or "ja").casefold()
    return "自然言語:ja" if lang.startswith("ja") else "自然言語:en"


def _証拠関係(結果: object) -> tuple[object, ...]:
    模型 = getattr(結果, "MINIDORA模型結果", None)
    文脈 = getattr(模型, "文脈", None)
    if 文脈 is None:
        return ()
    out: list[object] = []
    for ref in tuple(getattr(文脈, "参照状態", ())):
        if not bool(getattr(ref, "証拠利用可", False)):
            continue
        out.extend(tuple(getattr(ref, "関係構造", ())))
    # 問い側に既に確定している関係も、後続観測の重複を防ぐため証拠面へ含める。
    current = getattr(文脈, "現在", None)
    if current is not None:
        out.extend(tuple(getattr(current, "関係構造", ())))
    return tuple(out)


def HDS選択学習観測を導出(
    question_ir: object,
    候補意味IR: Mapping[str, object] | None,
    結果: object,
    経験: HDS選択学習経験,
) -> HDS選択学習導出:
    """現在の評価経験から未観測・矛盾関係を導出し、同一実行の次観測へ反映可能な要求へする。"""
    from dataclasses import replace
    from .HDS模型射影 import HDS内部言語状態
    from .HDS観測計画 import HDS参照観測要求
    from .HDS選択仮説 import HDS候補代入仮説群
    from .能力作用則 import 証拠状態照合
    from .コア.値 import 署名

    if not 候補意味IR:
        return HDS選択学習導出(経験.ID, (), 0, 0, 署名((経験.ID, ())))

    hypotheses = HDS候補代入仮説群(question_ir, 候補意味IR)
    証拠群 = _証拠関係(結果)
    経験文脈 = "\n".join((*経験.残差, *経験.理由))
    if any(x in 経験文脈 for x in ("候補競合", "AMBIGUOUS", "CONFLICT", "矛盾")):
        学習焦点 = "競合分別"
    elif any(x in 経験文脈 for x in ("観測不足", "NO_GUESS", "NO_KNOWLEDGE", "証拠_INSUFFICIENT", "EVIDENCE_INSUFFICIENT")):
        学習焦点 = "観測不足"
    elif 経験.結果状態 == "APPROVE":
        学習焦点 = "承認監査"
    else:
        学習焦点 = "未閉包"
    requests: list[object] = []
    seen: set[tuple[str, str]] = set()
    missing_count = 0
    conflict_count = 0

    for label, ir in sorted(hypotheses.items()):
        for 関係 in tuple(getattr(ir, "関係", ())):
            if str(getattr(関係, "由来", "")) != "HDS候補代入仮説":
                continue
            projected = HDS内部言語状態(
                replace(ir, 関係=(関係,)),
                識別子=f"学習候補:{label}:{getattr(関係, '関係ID', '')}",
                言語体系=_内部言語体系(question_ir),
            )
            targets = tuple(getattr(projected, "関係構造", ()))
            if not targets:
                continue
            照合状態 = 証拠状態照合(targets, 証拠群)
            if int(getattr(照合状態, "未観測", 0)) <= 0 and int(getattr(照合状態, "矛盾", 0)) <= 0:
                continue
            missing_count += int(getattr(照合状態, "未観測", 0))
            conflict_count += int(getattr(照合状態, "矛盾", 0))
            reason = "矛盾関係" if int(getattr(照合状態, "矛盾", 0)) > 0 else "未観測関係"
            観測表層群 = _観測表層群(ir, 関係)
            for 方法番号, surface in enumerate(観測表層群, start=1):
                key = (str(label), surface.casefold())
                if key in seen:
                    continue
                seen.add(key)
                基礎優先度 = 0 if reason == "矛盾関係" and 学習焦点 == "競合分別" else 5 if 学習焦点 == "観測不足" else 10
                requests.append(HDS参照観測要求(
                    ID=f"学習:{経験.ID}:{label}:{getattr(関係, '関係ID', '')}:方法:{方法番号}",
                    関係ID=str(getattr(関係, "関係ID", "")) or None,
                    関係種別=str(getattr(関係, "種別", "")) or None,
                    未知位置=None,
                    既知端点=(*_端点表層(ir, getattr(関係, "始点", ())), *_端点表層(ir, getattr(関係, "終点", ()))),
                    条件範囲=_条件範囲(関係),
                    候補ラベル=str(label),
                    候補表層=" ".join(str(getattr(候補意味IR[label], "正規化文", "") or getattr(候補意味IR[label], "原文", "")).split()).strip() or None,
                    外部言語=str(getattr(question_ir, "入力言語", "ja") or "ja"),
                    外部検索表層=surface,
                    必須被覆=True,
                    外部文脈アンカー=(),
                    段階="primary",
                    優先度=基礎優先度 + (方法番号 - 1) * 20,
                    provenance=("実行内学習", 経験.ID, 学習焦点, reason, f"観測方法:{方法番号}"),
                ))

    導出理由 = (
        f"経験状態:{経験.結果状態}",
        f"学習焦点:{学習焦点}",
        f"経験残差数:{len(経験.残差)}",
        f"経験理由数:{len(経験.理由)}",
        f"経験候補差数:{len(経験.候補差)}",
    )
    signature = 署名((経験.ID, 導出理由, tuple((x.ID, x.外部検索表層, x.優先度) for x in requests)))
    return HDS選択学習導出(
        経験.ID,
        tuple(requests),
        missing_count,
        conflict_count,
        signature,
        (経験.ID,),
        導出理由,
    )


def _候補対象関係群(question_ir: object, 候補意味IR: Mapping[str, object], label: str) -> tuple[object, ...]:
    from dataclasses import replace
    from .HDS模型射影 import HDS内部言語状態
    from .HDS選択仮説 import HDS候補代入仮説群

    ir = HDS候補代入仮説群(question_ir, 候補意味IR).get(str(label))
    if ir is None:
        return ()
    out: list[object] = []
    for 関係 in tuple(getattr(ir, "関係", ())):
        if str(getattr(関係, "由来", "")) != "HDS候補代入仮説":
            continue
        projected = HDS内部言語状態(
            replace(ir, 関係=(関係,)),
            識別子=f"学習証拠:{label}:{getattr(関係, '関係ID', '')}",
            言語体系=_内部言語体系(question_ir),
        )
        out.extend(tuple(getattr(projected, "関係構造", ())))
    return tuple(out)


def HDS選択学習証拠優越(
    question_ir: object,
    候補意味IR: Mapping[str, object] | None,
    結果: object,
    *,
    基準ラベル: str,
    新ラベル: str,
    最小独立支持数: int = 2,
) -> bool:
    """学習後の候補が基準を置換できるだけの独立した関係証拠があるかを検査する。"""
    from .能力作用則 import 証拠状態照合

    if not 候補意味IR or str(基準ラベル) == str(新ラベル):
        return False
    if type(最小独立支持数) is not int or 最小独立支持数 < 1:
        raise ValueError("最小独立支持数は1以上")
    模型 = getattr(結果, "MINIDORA模型結果", None)
    文脈 = getattr(模型, "文脈", None)
    if 文脈 is None:
        return False
    新対象 = _候補対象関係群(question_ir, 候補意味IR, str(新ラベル))
    旧対象 = _候補対象関係群(question_ir, 候補意味IR, str(基準ラベル))
    if not 新対象 or not 旧対象:
        return False

    新支持 = 0
    新反証 = 0
    旧反証 = 0
    for ref in tuple(getattr(文脈, "参照状態", ())):
        if not bool(getattr(ref, "証拠利用可", False)):
            continue
        関係群 = tuple(getattr(ref, "関係構造", ()))
        新照合状態 = 証拠状態照合(新対象, 関係群)
        旧照合状態 = 証拠状態照合(旧対象, 関係群)
        if int(getattr(新照合状態, "支持", 0)) > 0 and not int(getattr(新照合状態, "反証", 0)) and not int(getattr(新照合状態, "矛盾", 0)):
            新支持 += 1
        if int(getattr(新照合状態, "反証", 0)) > 0 or int(getattr(新照合状態, "矛盾", 0)) > 0:
            新反証 += 1
        if int(getattr(旧照合状態, "反証", 0)) > 0 or int(getattr(旧照合状態, "矛盾", 0)) > 0:
            旧反証 += 1
    return 新支持 >= 最小独立支持数 and 新反証 == 0 and 旧反証 >= 1


__all__ = [
    "HDS選択実行内学習版",
    "HDS選択学習経験",
    "HDS選択学習導出",
    "HDS選択学習経験を形成",
    "HDS選択学習経験を保持",
    "HDS選択参照記憶を統合",
    "HDS選択学習観測を導出",
    "HDS選択学習証拠優越",
]

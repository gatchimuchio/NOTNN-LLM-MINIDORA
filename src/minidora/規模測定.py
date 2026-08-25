from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any

from .模型 import MINIDORA模型核, 成立候補, 言語状態, 標準模型核
from .semantic_tokens import 意味語
from .言語基底 import 標準言語基底P
from .言語基底_英語 import 英語語形数


規模測定版 = "v1"


@dataclass(frozen=True, slots=True)
class 規模測定結果:
    版: str
    対象言語体系: tuple[str, ...]
    対象範囲: str
    比較集合: tuple[str, ...]
    状態域規模: dict[str, Any]
    関係域規模: dict[str, Any]
    共有適用規模: dict[str, Any]
    物理規模値: dict[str, Any]
    大規模性状態: str
    理由: tuple[str, ...]

    def 辞書(self) -> dict[str, Any]:
        return asdict(self)


def _内部署名(kernel: MINIDORA模型核, text: str, system: str) -> tuple[str, ...]:
    state = kernel.言語対応.内部化(言語状態(text, system))
    return tuple(sorted(state.意味語集合))


def _状態域測定(kernel: MINIDORA模型核) -> dict[str, Any]:
    rows: list[tuple[str, str]] = []
    for i in range(128):
        rows.append(("自然言語:en", f"entity_{i} causes result_{i % 31}"))
        rows.append(("自然言語:ja", f"対象{i} 状態{i % 23} 関係{i % 17}"))
        rows.append(("program:python", f"value_{i} = item_{i % 31} + {i % 13}"))

    signatures = {
        (system, _内部署名(kernel, text, system))
        for system, text in rows
    }

    long_text = "語" * 10000
    long_ok = bool(_内部署名(kernel, long_text, "自然言語:ja"))

    history = tuple(言語状態(f"履歴{i}", "自然言語:ja") for i in range(256))
    context = kernel.文脈化(言語状態("現在", "自然言語:ja"), history)

    return {
        "試験状態数": len(rows),
        "識別内部状態数": len(signatures),
        "試験言語体系数": 3,
        "一万文字状態受理": long_ok,
        "履歴深さ256受理": len(context.履歴) == 256,
        "明示固定文脈長上限": None,
        "観測": "文字列長・履歴長に模型核固有の一点上限は置かれておらず、複数言語体系の状態を同じ言語対応で内部化できる",
    }


def _関係域測定(kernel: MINIDORA模型核) -> dict[str, Any]:
    families = 標準言語基底P.英語関係族()
    recognized: list[str] = []
    for kind, lemmas in sorted(families.items()):
        lemma = sorted(lemmas)[0]
        if f"rel:{kind}" in 意味語(f"A {lemma} B"):
            recognized.append(kind)

    direction_same = _内部署名(kernel, "A causes B", "自然言語:en") == _内部署名(kernel, "B causes A", "自然言語:en")
    polarity_same = _内部署名(kernel, "A causes B", "自然言語:en") == _内部署名(kernel, "A does not cause B", "自然言語:en")

    candidates = (
        成立候補("A", 言語状態("alpha", "自然言語:en")),
        成立候補("B", 言語状態("beta", "自然言語:en")),
    )
    r1 = kernel.評価言語状態(
        言語状態("current", "自然言語:en"),
        candidates,
        履歴=(言語状態("alpha", "自然言語:en"), 言語状態("beta", "自然言語:en")),
    ).候補辞書()
    r2 = kernel.評価言語状態(
        言語状態("current", "自然言語:en"),
        candidates,
        履歴=(言語状態("beta", "自然言語:en"), 言語状態("alpha", "自然言語:en")),
    ).候補辞書()

    c1 = kernel.評価言語状態(
        言語状態("current", "自然言語:en"),
        candidates,
        条件=("alpha", "beta"),
    ).候補辞書()
    c2 = kernel.評価言語状態(
        言語状態("current", "自然言語:en"),
        candidates,
        条件=("beta", "alpha"),
    ).候補辞書()

    return {
        "模型関係実体数": len(kernel.関係群),
        "意味対応済み関係族数": len(recognized),
        "意味対応済み関係族": tuple(recognized),
        "方向差を識別": not direction_same,
        "肯否差を識別": not polarity_same,
        "履歴順序差が結果へ到達": r1 != r2,
        "条件順序差が結果へ到達": c1 != c2,
        "観測": "関係語族は複数識別するが、現行標準模型核の評価関係は意味集合連続が中心で、方向・肯否・履歴順序・条件結合の差が十分に結果へ到達しない",
    }


def _共有適用測定(kernel: MINIDORA模型核) -> dict[str, Any]:
    passed = 0
    total = 256
    relation_ids = tuple(id(item) for item in kernel.関係群)
    for i in range(total):
        context = 言語状態(f"topic_{i} causes result_{i % 19}", "自然言語:en")
        candidates = (
            成立候補("shared", 言語状態(f"topic_{i} causes outcome", "自然言語:en")),
            成立候補("other", 言語状態(f"unrelated_{i} stands alone", "自然言語:en")),
        )
        result = kernel.評価言語状態(context, candidates)
        if result.最有力候補ID == "shared":
            passed += 1
        if tuple(id(item) for item in kernel.関係群) != relation_ids:
            raise AssertionError("共有適用試験中に模型関係実体が交換された")

    return {
        "共有適用試験数": total,
        "同一関係群での成功数": passed,
        "成功率": passed / total,
        "関係実体再利用": passed == total,
        "観測": "同一の模型関係群を多数の異なる状態・文脈へ再利用できる",
    }


def 規模測定(kernel: MINIDORA模型核 | None = None) -> 規模測定結果:
    model = kernel or 標準模型核()
    state = _状態域測定(model)
    relation = _関係域測定(model)
    shared = _共有適用測定(model)
    base_stats = 標準言語基底P.統計()

    relation_gaps = tuple(
        name
        for name, value in (
            ("方向差", relation["方向差を識別"]),
            ("肯否差", relation["肯否差を識別"]),
            ("履歴順序差", relation["履歴順序差が結果へ到達"]),
            ("条件順序差", relation["条件順序差が結果へ到達"]),
        )
        if not value
    )

    if relation_gaps:
        status = "未成立"
        reasons = (
            "状態域は開放的で、共有適用も多数状態へ再利用できる",
            "関係域で重要な構造差が未分別のため、三つの規模面をまとめて大規模とは記せない",
            "未分別:" + ",".join(relation_gaps),
            "一点閾値ではなく関係域の構造不足を理由に保留する",
        )
    else:
        status = "局所成立候補"
        reasons = (
            "状態域・関係域・共有適用規模の三面で現在の比較集合に対する拡張性を確認",
            "大規模は比較集合依存の相対記述であり、普遍的一点閾値は置かない",
        )

    return 規模測定結果(
        版=規模測定版,
        対象言語体系=("自然言語:ja", "自然言語:en", "program:python"),
        対象範囲="MINIDORA v0.4 標準模型核。外部参照R、HDS Compiler、主体主幹、K3補助、計算実行器は模型核の規模へ加算しない",
        比較集合=(
            "固定ラベル・少数テンプレート・固定FAQ等の狭い言語処理系",
            "上流規定の2026年現代LLM参照群（構造比較。物理尺度の直接同一視はしない）",
        ),
        状態域規模=state,
        関係域規模=relation,
        共有適用規模=shared,
        物理規模値={
            "模型関係実体数": len(model.関係群),
            "英語関係語形数": 英語語形数(),
            **base_stats,
        },
        大規模性状態=status,
        理由=reasons,
    )


__all__ = ["規模測定版", "規模測定結果", "規模測定"]

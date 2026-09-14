from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
from typing import Any

from .能力状態差循環 import MINIDORA能力状態差模型核


汎用能力核版 = "MINIDORA-汎用能力核-v0.1"


class 能力核作用(StrEnum):
    模型閉包 = "模型閉包"
    入力内定義形成 = "入力内定義形成"
    定義適用 = "定義適用"
    仮説候補生成 = "仮説候補生成"
    仮説検討 = "仮説検討"
    因果介入比較 = "因果介入比較"
    資料読解 = "資料読解"
    導出説明 = "導出説明"


@dataclass(frozen=True, slots=True)
class 能力核作用結果:
    作用: 能力核作用
    状態: str
    成果: Any
    残差: tuple[str, ...] = ()
    境界: tuple[str, ...] = ()
    版: str = 汎用能力核版


class MINIDORA汎用能力核(MINIDORA能力状態差模型核):
    """既存の一般認知作用を、同じMINIDORA Core主体の共通ABIへ束ねる。

    最終採否、目的変更、永続記憶、外部取得、権限、Transaction/Resumeは持たない。
    各作用の元報告を改変せず ``成果`` に保持し、共通の状態・残差・境界だけを付与する。
    """

    汎用版 = 汎用能力核版

    def 模型を閉じる(self, result):
        from .模型閉包 import 模型終端を判定
        return 模型終端を判定(result)

    def 入力内定義を形成(self, text: str):
        from .意味定義 import 単項計算定義を読む
        return 単項計算定義を読む(text)

    def 入力内定義を適用(self, definition, value):
        from .意味定義 import 定義を実行
        from .計算実行器 import 計算実行器
        return 定義を実行(definition, value, 計算実行器())

    def 仮説候補を形成(self, request: dict, *, 最大候補数: int = 16):
        from .候補生成 import 仮説候補を生成
        return 仮説候補を生成(request, 最大候補数=最大候補数)

    def 仮説を検討する(self, request: dict, *, 自動候補: bool = False, 最大候補数: int = 16):
        from .候補生成 import 自動仮説要求
        from .有限仮説探索 import 仮説を検討
        target = request
        generation = None
        if 自動候補:
            target, generation = 自動仮説要求(request, 最大候補数=最大候補数)
        return 仮説を検討(target), generation

    def 因果介入を比較する(self, request: dict):
        from .有限因果モデル import 介入を比較
        return 介入を比較(request)

    def 資料を読む(self, request: dict):
        from .資料読解 import 資料を読解
        return 資料を読解(request)

    def 導出を説明する(self, judgment: dict, records: list[dict]):
        from .導出説明 import 導出説明を構成
        return 導出説明を構成(judgment, records)

    @staticmethod
    def _文字残差(rows) -> tuple[str, ...]:
        out = []
        for row in rows:
            if hasattr(row, "種別"):
                kind = str(getattr(row, "種別"))
                target = str(getattr(row, "対象", ""))
                details = tuple(str(x) for x in getattr(row, "詳細", ()))
                out.append(":".join(x for x in (kind, target, "|".join(details)) if x))
            elif isinstance(row, dict):
                ident = str(row.get("識別子", row.get("資料", "")))
                reason = str(row.get("理由", ""))
                out.append(":".join(x for x in (ident, reason) if x))
            else:
                out.append(str(row))
        return tuple(out)

    def 作用する(self, action: 能力核作用 | str, payload: Any, **options) -> 能力核作用結果:
        """Core一般作用の共通入口。処理完了と意味上の成立を同一boolへ潰さない。"""
        action = 能力核作用(action)

        if action == 能力核作用.模型閉包:
            result = self.模型を閉じる(payload)
            return 能力核作用結果(
                action, result.状態.value, result,
                self._文字残差(result.残差),
                ("最終採否はJの責任",),
            )

        if action == 能力核作用.入力内定義形成:
            result = self.入力内定義を形成(payload)
            return 能力核作用結果(
                action, "形成済み", result, (),
                ("入力内定義のみ", "未解釈残差は不成立"),
            )

        if action == 能力核作用.定義適用:
            if type(payload) is not dict or set(payload) != {"定義", "入力"}:
                raise ValueError("定義適用は 定義/入力 の2欄")
            definition = payload["定義"]
            if isinstance(definition, str):
                definition = self.入力内定義を形成(definition)
            result = self.入力内定義を適用(definition, payload["入力"])
            return 能力核作用結果(
                action, "計算完了", result, (),
                ("決定論的計算", "外部作用なし"),
            )

        if action == 能力核作用.仮説候補生成:
            result = self.仮説候補を形成(payload, 最大候補数=options.get("最大候補数", 16))
            state = "候補生成済み" if result.候補 else "候補未形成"
            return 能力核作用結果(
                action, state, result,
                self._文字残差(result.残差),
                ("世界知識・尤度・正解情報を補完しない",),
            )

        if action == 能力核作用.仮説検討:
            report, generation = self.仮説を検討する(
                payload,
                自動候補=bool(options.get("自動候補", False)),
                最大候補数=options.get("最大候補数", 16),
            )
            residuals = []
            if generation is not None:
                residuals.extend(self._文字残差(generation.残差))
            if report.get("状態") != "説明候補あり":
                residuals.append(str(report.get("状態", "未確定")))
            return 能力核作用結果(
                action, str(report.get("状態", "未確定")), report,
                tuple(residuals),
                (str(report.get("限界", "")),),
            )

        if action == 能力核作用.因果介入比較:
            report = self.因果介入を比較する(payload)
            return 能力核作用結果(
                action, str(report.get("状態", "未確定")), report, (),
                (str(report.get("限界", "")), "現実の因果採用はJの責任"),
            )

        if action == 能力核作用.資料読解:
            report = self.資料を読む(payload)
            residuals = list(self._文字残差(report.get("未解釈", ())))
            if report.get("問い残差"):
                residuals.append("問い:" + str(report["問い残差"]))
            for source in report.get("資料", ()):
                for missing in source.get("欠落", ()):
                    residuals.append(f"欠落:{source.get('名前', '')}:{missing}")
            return 能力核作用結果(
                action, str(report.get("状態", "未確定")), report,
                tuple(residuals),
                (str(report.get("限界", "")), "資料全体の真偽へ昇格しない"),
            )

        if action == 能力核作用.導出説明:
            if type(payload) is not dict or set(payload) != {"判定", "記載"}:
                raise ValueError("導出説明は 判定/記載 の2欄")
            report = self.導出を説明する(payload["判定"], payload["記載"])
            return 能力核作用結果(
                action, "説明構成済み", report, (),
                (str(report.get("境界", "")),),
            )

        raise ValueError("未対応の能力核作用")


def 標準汎用能力核() -> MINIDORA汎用能力核:
    from .模型 import (
        参照関係寄与作用,
        意味連続関係,
        有向関係整合,
        条件結合関係,
        肯否整合関係,
        候補共同参照作用,
        履歴近接関係,
        順序連続関係,
    )

    return MINIDORA汎用能力核(
        (
            意味連続関係(),
            順序連続関係(),
            有向関係整合(),
            肯否整合関係(),
            履歴近接関係(),
            条件結合関係(),
        ),
        能力作用群=(参照関係寄与作用(), 候補共同参照作用()),
    )


__all__ = [
    "汎用能力核版",
    "能力核作用",
    "能力核作用結果",
    "MINIDORA汎用能力核",
    "標準汎用能力核",
]

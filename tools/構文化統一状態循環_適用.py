from __future__ import annotations

from pathlib import Path


def _replace_once(path: str, old: str, new: str) -> None:
    target = Path(path)
    text = target.read_text(encoding="utf-8")
    count = text.count(old)
    if count != 1:
        raise RuntimeError(f"{path}: replacement anchor count={count}, expected=1\nANCHOR:\n{old[:800]}")
    target.write_text(text.replace(old, new, 1), encoding="utf-8")


def main() -> None:
    # K3 helperは正式模型核の標準経路では不要。型参照だけ遅延する。
    _replace_once(
        "src/minidora/hds能力経路_v2.py",
        "from typing import Iterable\n",
        "from typing import Iterable, TYPE_CHECKING\n",
    )
    _replace_once(
        "src/minidora/hds能力経路_v2.py",
        "from .k3_functional import K3相当能力核\n",
        "if TYPE_CHECKING:\n    from .k3_functional import K3相当能力核\n",
    )
    _replace_once(
        "src/minidora/hds能力経路_v2.py",
        "    基礎能力核: K3相当能力核,\n",
        "    基礎能力核: K3相当能力核 | None,\n",
    )

    _replace_once(
        "src/minidora/hds候補提案runtime.py",
        "from typing import Mapping, Sequence\n",
        "from typing import Mapping, Sequence, TYPE_CHECKING\n",
    )
    _replace_once(
        "src/minidora/hds候補提案runtime.py",
        "from .k3_functional import K3相当能力核\n",
        "if TYPE_CHECKING:\n    from .k3_functional import K3相当能力核\n",
    )
    _replace_once(
        "src/minidora/hds候補提案runtime.py",
        "    基礎能力核: K3相当能力核,\n",
        "    基礎能力核: K3相当能力核 | None,\n",
    )

    # HDS安全弁の追加参照・計算後も、初回と同じ統一評価入口へ戻す。
    supervisor = "src/minidora/hds監督選択runtime.py"
    _replace_once(supervisor, "import json\n", "import json\nfrom typing import Callable\n")
    _replace_once(
        supervisor,
        "        計算実行器_: 計算実行器 | None,\n        初期選択: HDS選択実行結果 | None,\n    ) -> None:\n",
        "        計算実行器_: 計算実行器 | None,\n        初期選択: HDS選択実行結果 | None,\n        評価実行: Callable[[tuple[参照記録, ...]], HDS選択実行結果] | None = None,\n    ) -> None:\n",
    )
    _replace_once(
        supervisor,
        "        self._compute_plan_checked = False\n        self._compute_plan = None\n        self.initial = 初期選択 if 初期選択 is not None else self._normal()\n",
        "        self._compute_plan_checked = False\n        self._compute_plan = None\n        self.評価実行 = 評価実行\n        self.initial = 初期選択 if 初期選択 is not None else self._normal()\n",
    )
    _replace_once(
        supervisor,
        "    ) -> HDS選択実行結果:\n        return HDS選択推論実行(\n            self.question_ir,\n            self.references,\n",
        "    ) -> HDS選択実行結果:\n        # 追加参照・計算後も同じ統一評価入口へ戻し、初回だけ新経路になる二重構造を防ぐ。\n        if self.評価実行 is not None:\n            return self.評価実行(self.references)\n        return HDS選択推論実行(\n            self.question_ir,\n            self.references,\n",
    )
    _replace_once(
        supervisor,
        "    HDS介入予算: int = 6,\n    初期選択: HDS選択実行結果 | None = None,\n) -> HDS監督選択結果:\n",
        "    HDS介入予算: int = 6,\n    初期選択: HDS選択実行結果 | None = None,\n    評価実行: Callable[[tuple[参照記録, ...]], HDS選択実行結果] | None = None,\n) -> HDS監督選択結果:\n",
    )
    _replace_once(
        supervisor,
        "        計算実行器_=計算実行器_,\n        初期選択=初期選択,\n    )\n",
        "        計算実行器_=計算実行器_,\n        初期選択=初期選択,\n        評価実行=評価実行,\n    )\n",
    )

    runtime = "src/minidora/runtime.py"
    _replace_once(
        runtime,
        "        計算実行器_: 計算実行器 | None = None,\n        HDS監督制御_: HDS介入制御 | None | object = _標準HDS監督,\n    ) -> None:\n",
        "        計算実行器_: 計算実行器 | None = None,\n        HDS監督制御_: HDS介入制御 | None | object = _標準HDS監督,\n        HDS形成台帳_=None,\n    ) -> None:\n",
    )
    _replace_once(
        runtime,
        "        self.模型核 = self.能力模型核\n        self.HDS監督制御 = 標準HDS介入制御() if HDS監督制御_ is _標準HDS監督 else HDS監督制御_\n",
        "        self.模型核 = self.能力模型核\n        self.HDS監督制御 = 標準HDS介入制御() if HDS監督制御_ is _標準HDS監督 else HDS監督制御_\n        if HDS形成台帳_ is None:\n            from .hds形成循環 import HDS形成台帳\n            HDS形成台帳_ = HDS形成台帳()\n        self.HDS形成台帳 = HDS形成台帳_\n",
    )

    old_choice = '''                initial = HDS選択推論実行(\n                    hds_ir, references, コンパイル=self.コンパイル, 基礎能力核=None,\n                    模型核=self.能力模型核, 正式模型評価=True,\n                )\n                if self.HDS監督制御 is None or (initial.状態 == "APPROVE" and initial.回答ラベル is not None):\n                    return self._HDS選択結果(要求_, hds_ir, references, initial)\n                supervised = HDS監督選択実行(\n                    hds_ir, references, コンパイル=self.コンパイル, 基礎能力核=None,\n                    模型核=self.能力模型核, 参照供給器=self.参照供給器,\n                    計算実行器_=self.計算実行器, HDS制御=self.HDS監督制御, 初期選択=initial,\n                )\n                return self._HDS選択結果(要求_, hds_ir, supervised.参照, supervised.選択)\n'''
    new_choice = '''                from .hds統一実行 import HDS統一選択評価\n                from .hds統一状態循環 import HDS統一状態Session\n\n                unified_session = HDS統一状態Session(\n                    str(hds_ir.正規化文 or hds_ir.原文),\n                    references,\n                    主体状態=self.主体状態,\n                    認知世界ID=str(hds_ir.認知世界ID or ""),\n                )\n\n                def _統一評価(current_references: tuple[参照記録, ...]) -> HDS選択実行結果:\n                    return HDS統一選択評価(\n                        hds_ir,\n                        current_references,\n                        コンパイル=self.コンパイル,\n                        模型核=self.能力模型核,\n                        統一session=unified_session,\n                        主体状態=self.主体状態,\n                    )\n\n                initial = _統一評価(references)\n                if self.HDS監督制御 is None or (initial.状態 == "APPROVE" and initial.回答ラベル is not None):\n                    return self._HDS選択結果(要求_, hds_ir, references, initial)\n                supervised = HDS監督選択実行(\n                    hds_ir, references, コンパイル=self.コンパイル, 基礎能力核=None,\n                    模型核=self.能力模型核, 参照供給器=self.参照供給器,\n                    計算実行器_=self.計算実行器, HDS制御=self.HDS監督制御, 初期選択=initial,\n                    評価実行=_統一評価,\n                )\n                return self._HDS選択結果(要求_, hds_ir, supervised.参照, supervised.選択)\n'''
    _replace_once(runtime, old_choice, new_choice)

    history_anchor = '''        history = (\n            {"op":"HDS_CHOICE_NATIVE","status":選択.状態,"answer_label":選択.回答ラベル,"candidate_compiled":選択.候補コンパイル数},\n            {"op":"R_TO_HDS_TO_K","reference_count":len(参照),"data_compiled":選択.Dataコンパイル数,"data_compile_failed":選択.Dataコンパイル失敗数,"k_facts_added":選択.K追加事実数,"evidence_facts":選択.K証拠事実数,"blocked_evidence_facts":選択.K証拠阻害事実数},\n        )\n        return self._帰還(結果(\n'''
    history_replacement = '''        history = (\n            {"op":"HDS_CHOICE_NATIVE","status":選択.状態,"answer_label":選択.回答ラベル,"candidate_compiled":選択.候補コンパイル数},\n            {"op":"R_TO_HDS_TO_K","reference_count":len(参照),"data_compiled":選択.Dataコンパイル数,"data_compile_failed":選択.Dataコンパイル失敗数,"k_facts_added":選択.K追加事実数,"evidence_facts":選択.K証拠事実数,"blocked_evidence_facts":選択.K証拠阻害事実数},\n        )\n\n        # 形成循環は現在の推論・採否には使わず、実行後の観測だけを台帳へ残す。\n        if self.HDS形成台帳 is not None:\n            from hashlib import sha256\n            from .hds形成循環 import HDS形成観測\n\n            def _形成署名(value: object) -> str:\n                return sha256(repr(value).encode("utf-8")).hexdigest()[:20]\n\n            last_action = next(\n                (str(reason).split(":", 1)[1] for reason in 選択.理由 if str(reason).startswith("UNIFIED_LAST_ACTION:")),\n                "FINAL_EVALUATION",\n            )\n            before_residuals = tuple(str(x) for x in self.HDS文脈.未解残差)\n            after_residuals = () if 選択.状態 == "APPROVE" else tuple(str(x) for x in 選択.理由)\n            self.HDS形成台帳.記録(HDS形成観測(\n                str(ir.認知世界ID or _形成署名(ir.正規化文 or ir.原文)),\n                _形成署名(ir.正規化文 or ir.原文),\n                last_action,\n                before_residuals,\n                after_residuals,\n                _形成署名((self._HDS版, before_residuals)),\n                _形成署名((選択.状態, 選択.回答ラベル, 選択.理由)),\n                bool(選択.状態 == "APPROVE" and 選択.回答ラベル is not None),\n                tuple(str(record.識別子) for record in 参照),\n            ))\n\n        return self._帰還(結果(\n'''
    _replace_once(runtime, history_anchor, history_replacement)


if __name__ == "__main__":
    main()

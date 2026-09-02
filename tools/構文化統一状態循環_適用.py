from __future__ import annotations

from pathlib import Path
import subprocess
import tempfile


PATCHES = (
r'''--- a/src/minidora/hds能力経路_v2.py
+++ b/src/minidora/hds能力経路_v2.py
@@
-from typing import Iterable
+from typing import Iterable, TYPE_CHECKING
@@
-from .k3_functional import K3相当能力核
+if TYPE_CHECKING:
+    from .k3_functional import K3相当能力核
@@
-    基礎能力核: K3相当能力核,
+    基礎能力核: K3相当能力核 | None,
--- a/src/minidora/hds候補提案runtime.py
+++ b/src/minidora/hds候補提案runtime.py
@@
-from typing import Mapping, Sequence
+from typing import Mapping, Sequence, TYPE_CHECKING
@@
-from .k3_functional import K3相当能力核
+if TYPE_CHECKING:
+    from .k3_functional import K3相当能力核
@@
-    基礎能力核: K3相当能力核,
+    基礎能力核: K3相当能力核 | None,
''',
r'''--- a/src/minidora/hds監督選択runtime.py
+++ b/src/minidora/hds監督選択runtime.py
@@
 from dataclasses import dataclass, replace
 from hashlib import sha256
 import json
+from typing import Callable
@@
 class _Session:
@@
         計算実行器_: 計算実行器 | None,
         初期選択: HDS選択実行結果 | None,
+        評価実行: Callable[[tuple[参照記録, ...]], HDS選択実行結果] | None = None,
     ) -> None:
@@
         self._compute_plan_checked = False
         self._compute_plan = None
+        self.評価実行 = 評価実行
         self.initial = 初期選択 if 初期選択 is not None else self._normal()
         self.current = self.initial
@@
     def _normal(
         self,
         *,
         working: bool = True,
         local: bool = True,
         formal_model: bool = True,
     ) -> HDS選択実行結果:
+        # 追加参照・計算後も同じ統一評価入口へ戻し、初回だけ新経路になる二重構造を防ぐ。
+        if self.評価実行 is not None:
+            return self.評価実行(self.references)
         return HDS選択推論実行(
@@
 def HDS監督選択実行(
@@
     HDS介入予算: int = 6,
     初期選択: HDS選択実行結果 | None = None,
+    評価実行: Callable[[tuple[参照記録, ...]], HDS選択実行結果] | None = None,
 ) -> HDS監督選択結果:
@@
         計算実行器_=計算実行器_,
         初期選択=初期選択,
+        評価実行=評価実行,
     )
''',
r'''--- a/src/minidora/runtime.py
+++ b/src/minidora/runtime.py
@@
         言語模型核_: MINIDORA厳密言語模型 | None = None,
         計算実行器_: 計算実行器 | None = None,
         HDS監督制御_: HDS介入制御 | None | object = _標準HDS監督,
+        HDS形成台帳_=None,
     ) -> None:
@@
         self.能力模型核 = 模型核_ or 標準能力模型核()
         self.模型核 = self.能力模型核
         self.HDS監督制御 = 標準HDS介入制御() if HDS監督制御_ is _標準HDS監督 else HDS監督制御_
+        if HDS形成台帳_ is None:
+            from .hds形成循環 import HDS形成台帳
+            HDS形成台帳_ = HDS形成台帳()
+        self.HDS形成台帳 = HDS形成台帳_
@@
             if HDS選択問題(hds_ir):
                 references: tuple[参照記録, ...] = ()
                 if self.参照供給器 is not None:
@@
                         一問合せ上限=budget.一問合せ上限, 最大問合せ並列=budget.最大問合せ並列,
                     )
-                initial = HDS選択推論実行(
-                    hds_ir, references, コンパイル=self.コンパイル, 基礎能力核=None,
-                    模型核=self.能力模型核, 正式模型評価=True,
-                )
+                from .hds統一実行 import HDS統一選択評価
+                from .hds統一状態循環 import HDS統一状態Session
+
+                unified_session = HDS統一状態Session(
+                    str(hds_ir.正規化文 or hds_ir.原文),
+                    references,
+                    主体状態=self.主体状態,
+                    認知世界ID=str(hds_ir.認知世界ID or ""),
+                )
+
+                def _統一評価(current_references: tuple[参照記録, ...]) -> HDS選択実行結果:
+                    return HDS統一選択評価(
+                        hds_ir,
+                        current_references,
+                        コンパイル=self.コンパイル,
+                        模型核=self.能力模型核,
+                        統一session=unified_session,
+                        主体状態=self.主体状態,
+                    )
+
+                initial = _統一評価(references)
                 if self.HDS監督制御 is None or (initial.状態 == "APPROVE" and initial.回答ラベル is not None):
                     return self._HDS選択結果(要求_, hds_ir, references, initial)
                 supervised = HDS監督選択実行(
@@
                     模型核=self.能力模型核, 参照供給器=self.参照供給器,
-                    計算実行器_=self.計算実行器, HDS制御=self.HDS監督制御, 初期選択=initial,
+                    計算実行器_=self.計算実行器, HDS制御=self.HDS監督制御, 初期選択=initial,
+                    評価実行=_統一評価,
                 )
                 return self._HDS選択結果(要求_, hds_ir, supervised.参照, supervised.選択)
''',
r'''--- a/src/minidora/runtime.py
+++ b/src/minidora/runtime.py
@@
         history = (
             {"op":"HDS_CHOICE_NATIVE","status":選択.状態,"answer_label":選択.回答ラベル,"candidate_compiled":選択.候補コンパイル数},
             {"op":"R_TO_HDS_TO_K","reference_count":len(参照),"data_compiled":選択.Dataコンパイル数,"data_compile_failed":選択.Dataコンパイル失敗数,"k_facts_added":選択.K追加事実数,"evidence_facts":選択.K証拠事実数,"blocked_evidence_facts":選択.K証拠阻害事実数},
         )
+
+        # 形成循環は推論中の採否には使わない。実行後の観測だけを台帳へ残す。
+        if self.HDS形成台帳 is not None:
+            from hashlib import sha256
+            from .hds形成循環 import HDS形成観測
+
+            def _形成署名(value: object) -> str:
+                return sha256(repr(value).encode("utf-8")).hexdigest()[:20]
+
+            last_action = next(
+                (str(reason).split(":", 1)[1] for reason in 選択.理由 if str(reason).startswith("UNIFIED_LAST_ACTION:")),
+                "FINAL_EVALUATION",
+            )
+            before_residuals = tuple(str(x) for x in self.HDS文脈.未解残差)
+            after_residuals = () if 選択.状態 == "APPROVE" else tuple(str(x) for x in 選択.理由)
+            self.HDS形成台帳.記録(HDS形成観測(
+                str(ir.認知世界ID or _形成署名(ir.正規化文 or ir.原文)),
+                _形成署名(ir.正規化文 or ir.原文),
+                last_action,
+                before_residuals,
+                after_residuals,
+                _形成署名((self._HDS版, before_residuals)),
+                _形成署名((選択.状態, 選択.回答ラベル, 選択.理由)),
+                bool(選択.状態 == "APPROVE" and 選択.回答ラベル is not None),
+                tuple(str(record.識別子) for record in 参照),
+            ))
+
         return self._帰還(結果(
''',
)


def main() -> None:
    for index, patch in enumerate(PATCHES, start=1):
        with tempfile.NamedTemporaryFile("w", encoding="utf-8", suffix=f"-{index}.patch", delete=False) as handle:
            handle.write(patch)
            path = handle.name
        subprocess.run(["git", "apply", "--check", path], check=True)
        subprocess.run(["git", "apply", path], check=True)


if __name__ == "__main__":
    main()

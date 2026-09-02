from __future__ import annotations

from pathlib import Path


path = Path("src/minidora/runtime.py")
text = path.read_text(encoding="utf-8")
start_marker = "                supervised = HDS監督選択実行("
end_marker = "                return self._HDS選択結果(要求_, hds_ir, supervised.参照, supervised.選択)\n"
start = text.find(start_marker)
if start < 0:
    raise SystemExit("runtime start anchor not found")
end_start = text.find(end_marker, start)
if end_start < 0:
    raise SystemExit("runtime end anchor not found")
end = end_start + len(end_marker)

lines = [
    "                # 55/198を成立させた既存MINIDORA経路を先に最後まで実行する。",
    "                # 既存経路が閉包した場合は一切再解釈せず、その結果をそのまま返す。",
    "                supervised = HDS監督選択実行(",
    "                    hds_ir,",
    "                    tuple(references),",
    "                    コンパイル=self.コンパイル,",
    "                    基礎能力核=self.K3能力核,",
    "                    模型核=self.能力模型核,",
    "                    参照供給器=self.参照供給器,",
    "                    HDS制御=self.HDS監督制御,",
    "                    初期選択=initial,",
    "                )",
    "                if supervised.選択.状態 == \"APPROVE\" and supervised.選択.回答ラベル is not None:",
    "                    return self._HDS選択結果(要求_, hds_ir, supervised.参照, supervised.選択)",
    "",
    "                # K3/GLM/Llama3統一状態循環は既存経路が未閉包の時だけfallbackとして発火する。",
    "                # 既存の正答・採否・科学専門能力経路を置換しない。",
    "                from .hds統一実行 import HDS統一選択評価",
    "                from .hds統一状態循環 import HDS統一状態Session",
    "",
    "                fallback_references = tuple(supervised.参照)",
    "                unified_session = HDS統一状態Session(",
    "                    str(hds_ir.正規化文 or hds_ir.原文),",
    "                    fallback_references,",
    "                    主体状態=self.主体状態,",
    "                    認知世界ID=str(hds_ir.認知世界ID or \"\"),",
    "                )",
    "                unified = HDS統一選択評価(",
    "                    hds_ir,",
    "                    fallback_references,",
    "                    コンパイル=self.コンパイル,",
    "                    模型核=self.能力模型核,",
    "                    統一session=unified_session,",
    "                    主体状態=self.主体状態,",
    "                )",
    "                if unified.状態 == \"APPROVE\" and unified.回答ラベル is not None:",
    "                    return self._HDS選択結果(要求_, hds_ir, fallback_references, unified)",
    "",
    "                # fallbackが閉包できなければ既存MINIDORAの未閉包結果を保持する。",
    "                return self._HDS選択結果(要求_, hds_ir, supervised.参照, supervised.選択)",
    "",
]
replacement = "\n".join(lines)
path.write_text(text[:start] + replacement + text[end:], encoding="utf-8")
print("monotonic fallback integrated")

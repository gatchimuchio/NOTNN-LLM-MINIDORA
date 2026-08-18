"""実行結果・台帳・命令履歴を日本語fieldへ射影する。"""
from __future__ import annotations
from dataclasses import asdict, is_dataclass
from enum import Enum
from typing import Any

_FIELD = {
    "status":"状態", "state":"状態", "answer":"回答", "task_family":"問題系統", "confidence":"確信度",
    "reason_codes":"理由符号群", "evidence_ids":"証拠番号群", "trace":"履歴", "elapsed_ms":"所要ミリ秒",
    "record_id":"記録番号", "kind":"種別", "title":"題名", "body":"本文", "tags":"標識群",
    "source":"出典", "authority":"権限", "metadata":"付記", "opcode":"命令語", "opcodes":"命令語群",
    "args":"引数", "source_ids":"出典番号群", "program_id":"手順番号", "instructions":"命令列",
    "input_data":"入力資料", "target_schema":"出力型", "compile_trace":"変換履歴",
    "model_projection":"模型射影", "sequence_axis":"時間軸", "layers":"層群", "layer":"層",
    "global_families":"全体役割群", "expected_counts":"期待数", "scalar_semantic_conversion":"重み値意味命令化",
    "expected_role_families":"期待役割群", "selected_experts_per_token":"各token選択数",
    "kda_layers":"KDA層数", "gated_mla_layers":"門制御MLA層数", "schedule":"実行順",
    "kda_semantics":"KDA意味", "global_semantics":"全体意味", "depth_axis":"深度軸",
    "attnres_block_size":"注意残差塊幅", "blocks":"塊数", "partial_final_block":"末尾不完全塊",
    "sources_including_embedding":"埋込含む参照源数", "width_axis":"幅軸", "routed_experts":"経路選択専門器数",
    "selected_per_token":"各token選択数", "shared_experts":"共有専門器数", "latent_width":"潜在幅",
    "model_width":"模型幅", "experts":"専門器群", "expert_id":"専門器番号", "family":"系統",
    "shared":"共有", "effort_axis":"計算量軸", "levels":"段階", "activation":"活性化", "name":"名称",
    "context":"文脈", "vision":"視覚", "public_model":"公開模型", "current_non_neural_projection":"現非ニューラル射影",
    "tensor_name":"テンソル名", "shape":"形状", "dtype":"資料型", "shard":"分割名", "data_offsets":"資料位置",
    "conversion_state":"変換状態", "role":"役割", "axis":"軸", "notes":"注記", "summary":"概要",
    "checks":"検査", "commands":"実行記録", "violations":"違反", "claim_boundary":"主張境界",
    "channel":"路", "action":"作用", "retention":"保持率", "write_strength":"書込強度",
    "provider":"参照供給器", "reference_ids":"参照番号群", "effort":"計算量", "budget":"予算",
    "max_reference":"最大参照数", "max_steps":"最大手順数", "max_stage_reads":"最大段階読出数",
    "verification_passes":"検証回数", "stage":"段階", "required":"必須参照", "bound":"結合済参照",
    "replay_answer":"再実行回答", "schema_ok":"出力型適合", "passed":"合格", "payload_digest":"資料摘要",
    "verifier":"検証器", "routed_experts":"経路選択専門器群", "shared_experts":"共有専門器群",
    "stage_ids":"段階番号群", "error":"誤り", "text":"本文", "result":"結果", "expression":"式",
    "values":"値群", "items":"項目群", "category":"分類", "selected":"選択結果", "target":"対象",
    "value":"値", "entities":"対象群", "constraints":"制約群", "valid":"成立順序群", "derivation":"導出",
    "base":"基準", "operation":"作用", "options":"選択肢群", "claims":"主張群",
    "contradictions":"矛盾群", "hazards":"危険群", "source_id":"出典番号",
}

def 日本語辞書(value: Any) -> Any:
    if is_dataclass(value):
        value = asdict(value)
    if isinstance(value, Enum):
        return value.value
    if isinstance(value, dict):
        return {_FIELD.get(str(k), str(k)): 日本語辞書(v) for k,v in value.items()}
    if isinstance(value, (list, tuple)):
        return [日本語辞書(v) for v in value]
    return value

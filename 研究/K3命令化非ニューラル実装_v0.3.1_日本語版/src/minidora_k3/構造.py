from __future__ import annotations

import hashlib
from dataclasses import asdict, dataclass
from typing import Iterable


@dataclass(frozen=True, slots=True)
class LayerInstruction:
    layer: int
    attention_opcode: str
    feedforward_opcode: str
    attnres_block: int
    dense_ffn: bool


@dataclass(frozen=True, slots=True)
class ExpertDescriptor:
    expert_id: int
    family: str
    tags: tuple[str, ...]
    shared: bool = False


TASK_FAMILIES = (
    "論理式",
    "算術",
    "数量",
    "状態遷移",
    "順序",
    "日付",
    "参照",
    "検証",
    "言語",
    "計画",
    "符号",
    "視覚",
    "一般",
    "矛盾",
)


def build_layer_program() -> tuple[LayerInstruction, ...]:
    rows: list[LayerInstruction] = []
    for layer in range(1, 94):
        attention = "門制御MLA全体照合" if layer % 4 == 0 or layer == 93 else "KDA状態更新"
        rows.append(
            LayerInstruction(
                layer=layer,
                attention_opcode=attention,
                feedforward_opcode="密SiTU_GLU" if layer == 1 else "安定潜在MoE",
                attnres_block=(layer - 1) // 12,
                dense_ffn=layer == 1,
            )
        )
    assert sum(row.attention_opcode == "KDA状態更新" for row in rows) == 69
    assert sum(row.attention_opcode == "門制御MLA全体照合" for row in rows) == 24
    return tuple(rows)


def build_expert_manifest() -> tuple[ExpertDescriptor, ...]:
    rows: list[ExpertDescriptor] = []
    for expert_id in range(896):
        family = TASK_FAMILIES[expert_id % len(TASK_FAMILIES)]
        rows.append(
            ExpertDescriptor(
                expert_id=expert_id,
                family=family,
                tags=(family, f"bucket:{expert_id // len(TASK_FAMILIES)}"),
            )
        )
    rows.append(ExpertDescriptor(896, "共有言語", ("言語", "normalize", "render"), True))
    rows.append(ExpertDescriptor(897, "共有採否", ("verify", "evidence", "矛盾", "authority"), True))
    return tuple(rows)


def deterministic_top16(task_family: str, features: Iterable[str]) -> tuple[int, ...]:
    feature_text = "|".join(sorted(set(features)))
    matching = [row.expert_id for row in build_expert_manifest()[:896] if row.family == task_family]
    if not matching:
        matching = list(range(896))
    scored: list[tuple[bytes, int]] = []
    for expert_id in matching:
        payload = f"{task_family}|{feature_text}|{expert_id}".encode("utf-8")
        scored.append((hashlib.sha256(payload).digest(), expert_id))
    return tuple(expert_id for _, expert_id in sorted(scored)[:16])


def architecture_manifest() -> dict[str, object]:
    layers = build_layer_program()
    experts = build_expert_manifest()
    return {
        "model_projection": "Kimi-K3-public-structure-to-explicit-instructions",
        "sequence_axis": {
            "layers": 93,
            "kda_layers": 69,
            "gated_mla_layers": 24,
            "schedule": [asdict(row) for row in layers],
            "kda_semantics": ["保持", "消去", "書込", "読出"],
            "global_semantics": ["参照選択", "全体照合", "出力門"],
        },
        "depth_axis": {
            "attnres_block_size": 12,
            "blocks": 8,
            "partial_final_block": True,
            "sources_including_embedding": 9,
            "opcodes": ["段階登録", "深度評価", "深度上位読出", "塊累積"],
        },
        "width_axis": {
            "routed_experts": 896,
            "selected_per_token": 16,
            "shared_experts": 2,
            "latent_width": 3584,
            "model_width": 7168,
            "experts": [asdict(row) for row in experts],
        },
        "effort_axis": {
            "levels": ["low", "high", "max"],
            "opcodes": ["予算設定", "計算量経路選択", "閉路停止"],
        },
        "activation": {"name": "SiTU-GLU", "beta_gate": 4.0, "beta_up": 25.0},
        "context": {"max_tokens_public_model": 1_048_576, "non_neural_runtime": "provider-defined"},
        "視覚": {
            "public_model": "MoonViT-V2",
            "vision_layers": 27,
            "vision_width": 1024,
            "heads": 12,
            "patch_size": 14,
            "current_non_neural_projection": "interface-only",
        },
    }


層命令 = LayerInstruction
専門器記述 = ExpertDescriptor
層手順を構築 = build_layer_program
専門器台帳を構築 = build_expert_manifest
決定的上位16 = deterministic_top16
構造台帳 = architecture_manifest

import json
from pathlib import Path

from minidora_k3.重み変換 import (
    TensorMetadata,
    bind_checkpoint_payloads,
    compile_checkpoint,
    expected_public_tensor_role_families,
    map_tensor_name,
    read_safetensors_header,
    synthetic_safetensors,
)

ROOT = Path(__file__).resolve().parents[1]


def test_公式設定の構造数():
    config = json.loads((ROOT / "一次資料/K3公式設定原文.json").read_text(encoding="utf-8"))
    counts = expected_public_tensor_role_families(config)["expected_counts"]
    assert counts == {
        "layers": 93,
        "kda_layers": 69,
        "gated_mla_layers": 24,
        "routed_experts": 896,
        "selected_experts_per_token": 16,
        "shared_experts": 2,
    }


def test_tensor名から日本語役割命令():
    cases = {
        "language_model.model.embed_tokens.weight": "語彙番地",
        "language_model.model.layers.3.self_attn.q_conv1d.weight": "KDA短畳込問合せ",
        "language_model.model.layers.3.self_attn.A_log": "KDA保持制御",
        "language_model.model.layers.4.self_attn.kv_a_proj_with_mqa.weight": "MLA潜在鍵値圧縮",
        "language_model.model.layers.4.attn_res_proj.weight": "注意残差深度評価",
        "language_model.model.layers.10.mlp.gate.weight": "MoE専門経路選択",
        "language_model.model.layers.10.mlp.experts.15.gate_up_proj.weight": "経路専門器起動",
        "language_model.model.layers.10.mlp.experts.15.down_proj.weight": "経路専門器返却",
        "vision_tower.patch_embed.proj.weight": "視覚片番地",
        "mm_projector.proj.weight": "視覚言語射影",
        "language_model.lm_head.weight": "結果面得点表",
    }
    for name, expected in cases.items():
        assert map_tensor_name(TensorMetadata(name, (2, 2), "F32", "synthetic.safetensors")).opcode == expected


def test_safetensors頭部とbyte結合(tmp_path: Path):
    shard = tmp_path / "model-00001-of-000096.safetensors"
    synthetic_safetensors(shard, {
        "language_model.model.embed_tokens.weight": {"shape": [2, 2], "dtype": "F32", "bytes": 16},
        "language_model.model.layers.1.self_attn.A_log": {"shape": [2], "dtype": "F32", "bytes": 8},
    })
    assert len(read_safetensors_header(shard)) == 2
    instructions, summary = compile_checkpoint(shard_paths=[shard])
    assert summary.tensors_total == 2
    assert summary.tensors_unresolved == 0
    assert summary.role_conversion_complete
    assert not summary.scalar_semantic_conversion_complete
    rows = bind_checkpoint_payloads((shard,), hash_payloads=True)
    assert len(rows) == 2
    assert all(row.payload_sha256 and len(row.payload_sha256) == 64 for row in rows)
    assert not any(row.semantic_conversion_complete for row in rows)

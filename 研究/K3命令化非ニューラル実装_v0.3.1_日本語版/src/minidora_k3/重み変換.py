"""K3公開checkpointを日本語の役割命令台帳へ変換する非ニューラルcompiler。

ここで変換するのは、tensor名・shape・dtype・shard・byte位置から観測できる
処理責任である。個々のscalarが保持する概念・知識・規則の意味変換とは分離する。
"""
from __future__ import annotations

import hashlib
import json
import re
import struct
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Iterable, Mapping, Sequence


class WeightCompilerError(RuntimeError):
    pass


@dataclass(frozen=True, slots=True)
class TensorMetadata:
    name: str
    shape: tuple[int, ...]
    dtype: str
    shard: str | None = None
    data_offsets: tuple[int, int] | None = None


@dataclass(frozen=True, slots=True)
class TensorInstruction:
    tensor_name: str
    opcode: str
    role: str
    axis: str
    layer: int | None
    expert: int | None
    shape: tuple[int, ...]
    dtype: str
    shard: str | None
    conversion_state: str
    exact_math_preservation: bool
    non_neural_semantic_projection: bool
    provenance: tuple[str, ...]
    notes: tuple[str, ...] = ()


@dataclass(frozen=True, slots=True)
class CompileSummary:
    tensors_total: int
    tensors_mapped: int
    tensors_unresolved: int
    role_conversion_complete: bool
    scalar_semantic_conversion_complete: bool
    opcodes: Mapping[str, int]
    unresolved_names: tuple[str, ...]
    source_mode: str


@dataclass(frozen=True, slots=True)
class TensorPayloadBinding:
    tensor_name: str
    opcode: str
    shard: str
    shape: tuple[int, ...]
    dtype: str
    data_start: int
    data_end: int
    payload_bytes: int
    payload_sha256: str | None
    conversion_state: str = "正確重みバイト役割命令結合"
    semantic_conversion_complete: bool = False
    exact_original_math_requires_native_operator_equivalent: bool = True


@dataclass(frozen=True, slots=True)
class RoleRule:
    pattern: re.Pattern[str]
    opcode: str
    role: str
    axis: str
    semantic_projection: bool
    notes: tuple[str, ...] = ()


_LAYER_RE = re.compile(r"(?:^|\.)(?:layers?|h)\.(\d+)(?:\.|$)")
_EXPERT_RE = re.compile(r"(?:^|\.)(?:experts?|routed_experts?)\.(\d+)(?:\.|$)")


def _rule(pattern: str, opcode: str, role: str, axis: str, semantic: bool, *notes: str) -> RoleRule:
    return RoleRule(re.compile(pattern, re.IGNORECASE), opcode, role, axis, semantic, tuple(notes))


# specific → general。公式tensor名は公開重みへ再接続する番地として原文保持する。
ROLE_RULES: tuple[RoleRule, ...] = (
    _rule(r"(?:embed_tokens|word_embeddings|tok_embeddings)\.weight$", "語彙番地", "token_to_symbol_address", "言語", False),
    _rule(r"(?:lm_head|output_projection|output)\.weight$", "結果面得点表", "symbol_to_output_score", "結果", False),
    _rule(r"vision_tower.*(?:patch_embed|patch_embedding).*weight$", "視覚片番地", "image_patch_to_visual_symbol", "視覚", False),
    _rule(r"vision_tower.*(?:position|pos_embed)", "視覚位置番地", "visual_position_encoding", "視覚", False),
    _rule(r"vision_tower.*(?:qkv|q_proj|k_proj|v_proj).*weight$", "視覚内容選択", "visual_attention_projection", "視覚", False),
    _rule(r"vision_tower.*(?:mlp|fc1|fc2|gate|up|down).*weight$", "視覚特徴変換", "visual_feature_transformation", "視覚", False),
    _rule(r"(?:mm_projector|multi_modal_projector|projector).*weight$", "視覚言語射影", "visual_symbol_to_language_state", "視覚", False),
    _rule(r"attn_res.*(?:proj|projection).*weight$", "注意残差深度評価", "content_dependent_depth_scoring", "深度", True),
    _rule(r"attn_res.*(?:norm|rms).*weight$", "注意残差深度正規化", "depth_candidate_normalization", "深度", True),
    _rule(r"self_attn.*(?:q_conv|q_conv1d|conv_q).*weight$", "KDA短畳込問合せ", "short_range_query_state", "時間", True),
    _rule(r"self_attn.*(?:k_conv|k_conv1d|conv_k).*weight$", "KDA短畳込鍵", "short_range_key_state", "時間", True),
    _rule(r"self_attn.*(?:v_conv|v_conv1d|conv_v).*weight$", "KDA短畳込値", "short_range_value_state", "時間", True),
    _rule(r"self_attn.*(?:a_log|decay|forget).*", "KDA保持制御", "retain_erase_gate", "時間", True),
    _rule(r"self_attn.*(?:beta|write_gate|update_gate).*", "KDA差分書込制御", "delta_write_gate", "時間", True),
    _rule(r"self_attn.*q_proj.*weight$", "KDA又はMLA問合せ射影", "content_query_projection", "時間又は文脈", False),
    _rule(r"self_attn.*k_proj.*weight$", "KDA鍵射影", "content_key_projection", "時間", False),
    _rule(r"self_attn.*v_proj.*weight$", "KDA値射影", "content_value_projection", "時間", False),
    _rule(r"self_attn.*(?:kv_a_proj|kv_a_layernorm|kv_b_proj).*", "MLA潜在鍵値圧縮", "latent_key_value_compression", "文脈", True),
    _rule(r"self_attn.*(?:q_a_proj|q_a_layernorm|q_b_proj).*", "MLA潜在問合せ圧縮", "latent_query_compression", "文脈", True),
    _rule(r"self_attn.*(?:rope|rotary).*", "MLA位置結合", "relative_position_binding", "文脈", True),
    _rule(r"self_attn.*(?:output_gate|o_gate|gate_proj).*", "門制御MLA出力制御", "global_context_output_gate", "文脈", True),
    _rule(r"self_attn.*(?:o_proj|out_proj).*weight$", "注意結果射影", "attention_result_projection", "文脈", False),
    _rule(r"(?:mlp|block_sparse_moe).*(?:router|gate)\.weight$", "MoE専門経路選択", "input_dependent_expert_selection", "幅", True),
    _rule(r"(?:latent|routed).*(?:down|compress|in)_proj.*weight$", "潜在MoE圧縮", "model_state_to_expert_latent", "幅", True),
    _rule(r"(?:latent|routed).*(?:up|expand|out)_proj.*weight$", "潜在MoE展開", "expert_latent_to_model_state", "幅", True),
    _rule(r"shared_experts?.*(?:gate|up|down|gate_up).*weight$", "共有専門器変換", "always_active_shared_capability", "幅", False),
    _rule(r"experts?\.\d+.*(?:gate|up|gate_up).*weight$", "経路専門器起動", "selected_expert_feature_expand", "幅", False),
    _rule(r"experts?\.\d+.*down.*weight$", "経路専門器返却", "selected_expert_feature_reduce", "幅", False),
    _rule(r"(?:mlp|feed_forward).*(?:gate|up|gate_up).*weight$", "密SiTU_GLU起動", "dense_feature_expand_and_gate", "幅", False),
    _rule(r"(?:mlp|feed_forward).*down.*weight$", "密SiTU_GLU返却", "dense_feature_reduce", "幅", False),
    _rule(r"(?:input_layernorm|post_attention_layernorm|rms_norm|norm)\.weight$", "状態正規化", "state_scale_normalization", "状態", True),
)


def map_tensor_name(metadata: TensorMetadata) -> TensorInstruction:
    layer_match = _LAYER_RE.search(metadata.name)
    expert_match = _EXPERT_RE.search(metadata.name)
    layer = int(layer_match.group(1)) if layer_match else None
    expert = int(expert_match.group(1)) if expert_match else None
    for rule in ROLE_RULES:
        if rule.pattern.search(metadata.name):
            return TensorInstruction(
                metadata.name, rule.opcode, rule.role, rule.axis, layer, expert,
                metadata.shape, metadata.dtype, metadata.shard,
                "役割変換済・重み値意味未変換", False, rule.semantic_projection,
                ("公開重み情報", "公開参照実装", "HDS役割射影"), rule.notes,
            )
    return TensorInstruction(
        metadata.name, "未解決テンソル役割", "unresolved", "residual", layer, expert,
        metadata.shape, metadata.dtype, metadata.shard, "残差未解決", False, False,
        ("公開重み情報", "HDS残差台帳"), ("tensor名だけでは処理責任を確定できない",),
    )


def read_safetensors_header(path: Path, *, max_header_bytes: int = 256 * 1024 * 1024) -> tuple[TensorMetadata, ...]:
    with path.open("rb") as stream:
        prefix = stream.read(8)
        if len(prefix) != 8:
            raise WeightCompilerError(f"safetensors prefix不足: {path}")
        (header_size,) = struct.unpack("<Q", prefix)
        if not 1 < header_size <= max_header_bytes:
            raise WeightCompilerError(f"header size境界外: {header_size}")
        raw = stream.read(header_size)
    try:
        header = json.loads(raw.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise WeightCompilerError(f"header JSON不正: {path}") from exc
    rows: list[TensorMetadata] = []
    for name, value in sorted(header.items()):
        if name == "__metadata__":
            continue
        shape, offsets, dtype = value.get("shape"), value.get("data_offsets"), value.get("dtype")
        if not isinstance(shape, list) or not isinstance(offsets, list) or len(offsets) != 2 or not isinstance(dtype, str):
            raise WeightCompilerError(f"tensor header不正: {name}")
        rows.append(TensorMetadata(name, tuple(shape), dtype, path.name, (int(offsets[0]), int(offsets[1]))))
    return tuple(rows)


def load_weight_index(path: Path) -> tuple[TensorMetadata, ...]:
    value = json.loads(path.read_text(encoding="utf-8"))
    weight_map = value.get("weight_map") if isinstance(value, dict) else None
    if not isinstance(weight_map, dict):
        raise WeightCompilerError("weight_mapがありません")
    return tuple(TensorMetadata(name, (), "索引由来型不明", shard) for name, shard in sorted(weight_map.items()))


def compile_tensor_metadata(rows: Sequence[TensorMetadata], *, source_mode: str) -> tuple[tuple[TensorInstruction, ...], CompileSummary]:
    instructions = tuple(map_tensor_name(row) for row in rows)
    unresolved = tuple(row.tensor_name for row in instructions if row.opcode == "未解決テンソル役割")
    counts: dict[str, int] = {}
    for row in instructions:
        counts[row.opcode] = counts.get(row.opcode, 0) + 1
    return instructions, CompileSummary(
        len(instructions), len(instructions) - len(unresolved), len(unresolved),
        bool(instructions) and not unresolved, False, dict(sorted(counts.items())), unresolved, source_mode,
    )


def compile_checkpoint(*, index_path: Path | None = None, shard_paths: Iterable[Path] = ()) -> tuple[tuple[TensorInstruction, ...], CompileSummary]:
    shards = tuple(shard_paths)
    if shards:
        rows = [row for path in shards for row in read_safetensors_header(path)]
        return compile_tensor_metadata(rows, source_mode="safetensors頭部")
    if index_path is not None:
        return compile_tensor_metadata(load_weight_index(index_path), source_mode="HF重み索引")
    raise WeightCompilerError("index_path又はshard_pathsが必要です")


def expected_public_tensor_role_families(config: Mapping[str, Any]) -> dict[str, Any]:
    text = config["text"]
    full_layers = set(text["full_attention_layers"])
    kda_layers = set(text["kda_layers"])
    layer_rows = []
    for layer in range(1, int(text["num_hidden_layers"]) + 1):
        attention = "門制御MLA全体照合" if layer in full_layers else "KDA状態更新"
        layer_rows.append({
            "layer": layer,
            "attention_opcode": attention,
            "feedforward_opcode": "密SiTU_GLU" if layer <= int(text["first_k_dense_replace"]) else "安定潜在MoE",
            "attnres_block": (layer - 1) // int(text["attn_res_block_size"]),
            "expected_role_families": ["状態正規化", "注意残差深度評価", attention],
        })
    return {
        "state": "構造役割台帳完了・重み役割台帳待機",
        "model": "moonshotai/Kimi-K3",
        "layers": layer_rows,
        "global_families": ["語彙番地", "結果面得点表", "視覚片番地", "視覚内容選択", "視覚特徴変換", "視覚言語射影"],
        "expected_counts": {
            "layers": int(text["num_hidden_layers"]), "kda_layers": len(kda_layers),
            "gated_mla_layers": len(full_layers), "routed_experts": int(text["moe"]["num_experts"]),
            "selected_experts_per_token": int(text["moe"]["num_experts_per_token"]),
            "shared_experts": int(text["moe"]["num_shared_experts"]),
        },
        "scalar_semantic_conversion": "全重み処理及び挙動検証待機",
    }


def synthetic_safetensors(path: Path, entries: Mapping[str, Mapping[str, Any]]) -> None:
    header: dict[str, Any] = {"__metadata__": {"format": "synthetic-test"}}
    offset = 0
    for name, value in entries.items():
        size = int(value.get("bytes", 4))
        header[name] = {"dtype": value.get("dtype", "F32"), "shape": value.get("shape", [1]), "data_offsets": [offset, offset + size]}
        offset += size
    raw = json.dumps(header, ensure_ascii=False, separators=(",", ":")).encode("utf-8")
    path.write_bytes(struct.pack("<Q", len(raw)) + raw + bytes(offset))


def _data_base(path: Path) -> int:
    with path.open("rb") as stream:
        prefix = stream.read(8)
    if len(prefix) != 8:
        raise WeightCompilerError(f"safetensors prefix不足: {path}")
    return 8 + struct.unpack("<Q", prefix)[0]


def _hash_region(path: Path, start: int, end: int) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        stream.seek(start)
        remaining = end - start
        while remaining:
            chunk = stream.read(min(8 * 1024 * 1024, remaining))
            if not chunk:
                raise WeightCompilerError(f"payload途中終了: {path}")
            digest.update(chunk)
            remaining -= len(chunk)
    return digest.hexdigest()


def bind_checkpoint_payloads(shard_paths: Iterable[Path], *, hash_payloads: bool = False) -> tuple[TensorPayloadBinding, ...]:
    bindings: list[TensorPayloadBinding] = []
    for path in shard_paths:
        path = path.resolve()
        base = _data_base(path)
        for metadata in read_safetensors_header(path):
            if metadata.data_offsets is None:
                raise WeightCompilerError(f"data_offsetsなし: {metadata.name}")
            start, end = (base + metadata.data_offsets[0], base + metadata.data_offsets[1])
            instruction = map_tensor_name(metadata)
            bindings.append(TensorPayloadBinding(
                metadata.name, instruction.opcode, path.name, metadata.shape, metadata.dtype,
                start, end, end - start, _hash_region(path, start, end) if hash_payloads else None,
            ))
    return tuple(bindings)


def dump_compile_result(output_path: Path, instructions: Sequence[TensorInstruction], summary: CompileSummary) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps({
        "summary": asdict(summary), "instructions": [asdict(row) for row in instructions],
        "claim_boundary": {"tensor_role_conversion": "measured", "scalar_semantics": "not inferred from names/shapes alone", "K3_equivalence": False},
    }, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def dump_payload_binding_manifest(output_path: Path, bindings: Sequence[TensorPayloadBinding]) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps({
        "state": "正確重みバイト役割命令群結合", "bindings": [asdict(row) for row in bindings],
        "claim_boundary": {"weight_bytes_preserved_by_reference": True, "scalar_semantic_conversion": False, "K3_equivalence": False},
    }, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


重み変換誤り = WeightCompilerError
テンソル情報 = TensorMetadata
テンソル命令 = TensorInstruction
テンソル実体結合 = TensorPayloadBinding
変換概要 = CompileSummary
役割規則 = RoleRule
重み実体を結合 = bind_checkpoint_payloads
重み索引を命令化 = compile_checkpoint
テンソル情報を命令化 = compile_tensor_metadata
変換結果を書く = dump_compile_result
実体結合台帳を書く = dump_payload_binding_manifest
予想公開テンソル役割系統 = expected_public_tensor_role_families
重み索引を読む = load_weight_index
テンソル名を役割化 = map_tensor_name
safetensors頭部を読む = read_safetensors_header
模擬safetensors = synthetic_safetensors

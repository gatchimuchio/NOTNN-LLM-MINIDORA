#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""K3実装観測に基づく HDS 原理族補完 v6。

観測根拠:
- KimiDeltaAttention: q/k/v -> ShortConvolution -> KDA recurrent state
- decay gate: g=f_b(f_a(hidden)); KDA kernel computes decay from A_log, g, dt_bias
- beta=b_proj(hidden), kernel-side sigmoid for update strength
- attention output gate: g_proj(hidden) -> sigmoid/gated RMSNorm -> attention output
- attention residual: learned projection + norm scores block residual candidates and softmax-mixes them

値単独へ語彙的意味を付与せず、実装上の作用関係としてのみ原理を確定する。
"""
from __future__ import annotations

from typing import Any, Callable, Dict

EXTRA_PRINCIPLES: Dict[str, Dict[str, Any]] = {
    "P-KDA-CONV": {
        "認知世界": "KDAへ入るQ/K/Vを、現在tokenだけでなく直近系列の局所状態を含む参照・更新表現として暫定形成する。",
        "原理質問": "何が現在投影Q/K/Vへ短距離の系列履歴を持ち込んでいるのか。",
        "開放並列場": ["単なる平滑化", "局所特徴抽出", "KDA recurrent state以前の短期系列状態形成"],
        "原理分別": "Q/K/V投影後の短畳み込みが直近系列を局所混合し、KDAの参照・記憶更新へ渡す短期状態を成立させる。",
        "崩壊条件": "畳み込み係数または系列順序を変えると、同じ現在tokenでもKDAへ渡るQ/K/V局所状態が変わる。",
        "観測根拠": "modeling_kimi_linear.py KimiDeltaAttention: q/k/v_proj -> q/k/v_conv1d -> chunk_kda/fused_recurrent_kda",
    },
    "P-KDA-DECAY": {
        "認知世界": "KDA recurrent stateが系列進行に伴ってどの程度保持・忘却されるかを定める減衰関係として暫定形成する。",
        "原理質問": "何が旧状態の残存率を条件化しているのか。",
        "開放並列場": ["単なる数値安定化係数", "時間尺度", "状態忘却率", "head/状態次元ごとの減衰条件"],
        "原理分別": "A_logが減衰尺度を、dt_biasが入力依存ゲートへの基準ずれを与え、入力由来gと合成されてKDAの対数減衰を成立させる。",
        "崩壊条件": "A_logまたはdt_biasを変えると同一系列でも旧recurrent stateの保持・忘却軌跡が変わる。",
        "観測根拠": "FLA KDA: -exp(A_log) * softplus(g + dt_bias); K3はA_log/dt_biasをKDA kernelへ直接渡す",
    },
    "P-KDA-DECAY-SIGNAL": {
        "認知世界": "現在hidden stateからKDAの状態減衰を条件化する入力依存信号を形成する関係として暫定形成する。",
        "原理質問": "何が同じ減衰尺度を入力ごとに変化させるのか。",
        "開放並列場": ["一般特徴投影", "低rank圧縮", "忘却ゲート入力形成"],
        "原理分別": "f_a_proj→f_b_projがhidden stateをhead×state次元のraw decay signal gへ写し、A_log/dt_biasとの合成で入力依存の保持・忘却を成立させる。",
        "崩壊条件": "この写像を変えると同じA_log/dt_biasでも入力ごとの減衰パターンが変わる。",
        "観測根拠": "KimiDeltaAttention: g=f_b_proj(f_a_proj(hidden_states)); g is passed to KDA as gate input",
    },
    "P-KDA-UPDATE": {
        "認知世界": "現在入力がrecurrent stateへどの強度で書き込まれるかを条件化する関係として暫定形成する。",
        "原理質問": "何が現在のK/V情報による状態更新量を入力ごと・headごとに変えるのか。",
        "開放並列場": ["一般スカラーゲート", "routing", "delta update強度"],
        "原理分別": "b_projがhidden stateからhead別beta logitsを形成し、kernel内sigmoidを通じてKDAのdelta更新強度を成立させる。",
        "崩壊条件": "b_proj係数を変えると同一Q/K/Vでもrecurrent stateへの更新強度が変わる。",
        "観測根拠": "KimiDeltaAttention: beta=b_proj(hidden_states); chunk_kda(... beta=beta, use_beta_sigmoid_in_kernel=True)",
    },
    "P-ATTN-OUTPUT-GATE": {
        "認知世界": "attention/KDAで得た候補出力を現在hidden stateに応じて通過・抑制する帰還条件として暫定形成する。",
        "原理質問": "何が計算済みattention結果の各成分を次状態へどの程度反映するかを決めるのか。",
        "開放並列場": ["追加特徴投影", "後処理正規化", "attention結果の入力依存通過ゲート"],
        "原理分別": "g_projがhidden stateから出力ゲートを形成し、full attentionではsigmoid乗算、KDAではgated RMSNormを介してattention結果の次状態への反映量を条件化する。",
        "崩壊条件": "g_projを変えるとattention本体の結果が同じでも次状態へ帰還する成分量が変わる。",
        "観測根拠": "KimiMLAAttention: sigmoid(g_proj(hidden))*attn_output; KimiDeltaAttention: o_norm(o, g_proj(hidden))",
    },
    "P-ATTN-RESIDUAL-MIX": {
        "認知世界": "複数層にまたがるblock residual候補と現在prefix stateから、次処理へ渡す一つの状態を選択混合する関係として暫定形成する。",
        "原理質問": "何が蓄積された複数残差候補の寄与率を現在状態から決めるのか。",
        "開放並列場": ["単純残差加算", "固定平均", "内容依存の残差候補選択混合"],
        "原理分別": "正規化した各残差候補と学習済みprojectionの内積からscoreを作り、softmax重みで候補状態を混合することでblock間の内容依存帰還を成立させる。",
        "崩壊条件": "projection係数・候補集合・正規化関係を変えると同じ残差列でも選択混合された状態が変わる。",
        "観測根拠": "_apply_attn_res: normalize candidates -> score_weight=norm.weight*proj.weight -> softmax(scores) -> weighted matmul",
    },
}


def principle_for_tensor_v6(name: str, fallback: Callable[[str], str]) -> str:
    n = name.lower()
    if ".self_attn." in n:
        if n.endswith(".a_log") or n.endswith(".dt_bias"):
            return "P-KDA-DECAY"
        if any(n.endswith(f".{x}_conv1d.weight") for x in ("q", "k", "v")):
            return "P-KDA-CONV"
        if n.endswith(".f_a_proj.weight") or n.endswith(".f_b_proj.weight"):
            return "P-KDA-DECAY-SIGNAL"
        if n.endswith(".b_proj.weight"):
            return "P-KDA-UPDATE"
        if n.endswith(".g_proj.weight"):
            return "P-ATTN-OUTPUT-GATE"
    if n.endswith(".self_attention_res_proj.weight") or n.endswith(".output_attn_res_proj.weight"):
        return "P-ATTN-RESIDUAL-MIX"
    return fallback(name)


def install(base_module: Any) -> None:
    fallback = base_module.principle_for_tensor
    base_module.PRINCIPLE_FAMILIES.update(EXTRA_PRINCIPLES)
    base_module.principle_for_tensor = lambda name: principle_for_tensor_v6(name, fallback)

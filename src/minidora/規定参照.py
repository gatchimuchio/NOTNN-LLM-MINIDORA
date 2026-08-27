from __future__ import annotations

LLM成立規定リポジトリ = "https://github.com/gatchimuchio/LLM-Constitutive-Specification"
LLM成立規定参照コミット = "debb83e091a705a5eac09ef4fb97a5b36305db6d"
LLM成立規定版 = "2026-08-28-成立規定-7"

厳密LM中核 = (
    "完全言語状態空間",
    "整合した言語確率法則",
    "持続模型状態",
    "local-to-global接続",
)

隣接模型区分 = (
    "条件付きLM",
    "局所言語予測",
    "scorer",
    "representation model",
    "transducer",
)

再現区分 = (
    "機能再現",
    "能力再現",
    "構造再現",
    "因果機構再現",
)

# v0.4公開名との互換。内容はv7へ更新済み。
LLM成立意味区別 = 厳密LM中核
LLM構成再現区別 = 再現区分

__all__ = [
    "LLM成立規定リポジトリ",
    "LLM成立規定参照コミット",
    "LLM成立規定版",
    "厳密LM中核",
    "隣接模型区分",
    "再現区分",
    "LLM成立意味区別",
    "LLM構成再現区別",
]

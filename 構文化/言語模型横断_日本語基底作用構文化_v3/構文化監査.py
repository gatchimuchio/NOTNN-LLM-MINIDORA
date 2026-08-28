from __future__ import annotations

from pathlib import Path
import json
import re

根 = Path(__file__).resolve().parent

模型文書 = [
    "01_GPT-5_6_Sol.md",
    "02_Claude_Fable_5_Mythos_5.md",
    "03_Gemini_3_x.md",
    "04_DeepSeek_V4.md",
    "05_Qwen3_6-35B-A3B.md",
    "06_Grok_4_6.md",
    "07_Llama_3_70B.md",
    "08_OLMo_3.md",
    "09_Apertus_1_5_70B.md",
    "10_K2-V2_70B.md",
]

for 名前 in 模型文書:
    本文 = (根 / 名前).read_text(encoding="utf-8")
    for 必須 in ("## 状態担体", "## 作用", "## 未観測", "## 外部原語"):
        assert 必須 in 本文, (名前, 必須)
    assert "K3: 対象外" in 本文, 名前

規約 = json.loads((根 / "構文化規約_v3.json").read_text(encoding="utf-8"))
座標 = json.loads((根 / "作用座標_v3.json").read_text(encoding="utf-8"))
目録 = json.loads((根 / "MANIFEST.json").read_text(encoding="utf-8"))

assert 規約["規定言語"] == "日本語"
assert 座標["規定言語"] == "日本語"
assert len(座標["模型"]) == 10
assert all(模型["名称"] != "K3" for 模型 in 座標["模型"])
assert 目録["対象模型数"] == 10
assert 目録["観測記録数"] == 20

日本語 = re.compile(r"[ぁ-んァ-ヶ一-龥々]")

def 鍵監査(値):
    if isinstance(値, dict):
        for 鍵, 子 in 値.items():
            assert 日本語.search(str(鍵)), f"日本語を含まない内部鍵: {鍵}"
            鍵監査(子)
    elif isinstance(値, list):
        for 子 in 値:
            鍵監査(子)

鍵監査(規約)
鍵監査(座標)
鍵監査(目録)

台帳 = []
for 部 in sorted((根 / "観測台帳_v3").glob("part_*.jsonl")):
    for 行 in 部.read_text(encoding="utf-8").splitlines():
        if 行.strip():
            記録 = json.loads(行)
            鍵監査(記録)
            台帳.append(記録)

assert len(台帳) == 20
assert not any(記録["模型"] == "K3" for 記録 in 台帳)

print("日本語基底作用構文化v3監査: 合格")
print("対象模型=10 / K3除外 / 観測記録=20 / 内部鍵=日本語")

from pathlib import Path
import json, sys
ROOT=Path(__file__).resolve().parent
expected=[
"01_OpenAI_GPT-5_6_Sol.md","02_Claude_Fable_5_Mythos_5.md","03_Google_Gemini_3_x.md","04_DeepSeek_V4.md","05_Qwen3_6-35B-A3B.md","06_Grok_4_6.md","07_Llama_3_70B_2024-04.md","08_OLMo_3.md","09_Apertus_1_5_70B.md","10_K2-V2_70B.md"]
for name in expected:
    p=ROOT/name
    assert p.exists(), name
    t=p.read_text(encoding="utf-8")
    for token in ["## S — 状態担体","## A — 作用","## Δ — 状態差","## D — 後続依存","## P — 状態依存の経路変化","## R — 再参照・再利用の尺度","## C — 再結合","## v1からの訂正・保持","## 未観測"]:
        assert token in t, (name,token)
    assert "K3" in t and "対象外" in t
coord=json.loads((ROOT/"作用因果座標_v2.json").read_text(encoding="utf-8"))
assert coord["schema"]=="minidora.cross_llm.state_delta_action_structuring.v2"
assert len(coord["models"])==10
allowed=set(coord["dependency_kinds"])
for m in coord["models"]:
    assert set(m["dependency_kinds"]) <= allowed, (m["name"], m["dependency_kinds"])
assert all(m["name"]!="K3" for m in coord["models"])
assert coord["benchmark_trigger"]["checkpoint_count"]==815
assert coord["benchmark_trigger"]["checkpoint_reactivations"]==0
manifest=json.loads((ROOT/"MANIFEST.json").read_text(encoding="utf-8"))
assert manifest["model_count"]==10
assert (ROOT/"13_一次資料再照合.md").exists()
assert (ROOT/"構文化スキーマ_v2.json").exists()
ledger=[]
ledger_parts=sorted((ROOT/"観測台帳_v2").glob("part_*.jsonl"))
assert [p.name for p in ledger_parts] == [f"part_{i:02d}.jsonl" for i in range(1, 6)]
for part in ledger_parts:
    ledger.extend(json.loads(x) for x in part.read_text(encoding="utf-8").splitlines() if x.strip())
assert len(ledger) == 35
assert not any(x.get("モデル")=="K3" for x in ledger)
import hashlib
for item in manifest["files"]:
    fp=ROOT/item["path"]
    assert fp.exists(), item["path"]
    assert hashlib.sha256(fp.read_bytes()).hexdigest()==item["sha256"], item["path"]
print("構文化v2監査: PASS")
print("models=10 K3=excluded schema=v2")

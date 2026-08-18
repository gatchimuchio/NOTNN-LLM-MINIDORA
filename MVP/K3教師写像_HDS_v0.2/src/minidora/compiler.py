from __future__ import annotations
import json
from pathlib import Path

def 教師写像監査(teacher_path,mapping_path,p_path):
    teacher={}
    with open(teacher_path,"r",encoding="utf-8") as f:
        for line in f:
            if line.strip():
                x=json.loads(line); teacher[x["id"]]=x
    mapping=json.loads(Path(mapping_path).read_text(encoding="utf-8")); P=json.loads(Path(p_path).read_text(encoding="utf-8")); errors=[]; mapped_ids=set()
    for m in mapping["写像"]:
        for oid in m["教師根拠"]:
            mapped_ids.add(oid)
            if oid not in teacher: errors.append(f"未知教師ID: {oid}")
    p_mappings=set()
    for rule in P["規則"]: p_mappings.update(rule.get("由来写像",[]))
    known_mapping_ids={m["id"] for m in mapping["写像"]}
    for mid in p_mappings:
        if mid not in known_mapping_ids: errors.append(f"Pの由来写像不明: {mid}")
    prohibited={"KDA","MLA","AttnRes","MoE","896","Top-16","93 layers"}; p_text=json.dumps(P,ensure_ascii=False); leaked=sorted(x for x in prohibited if x in p_text)
    if leaked: errors.append(f"K3固有語がPへ漏出: {leaked}")
    return {"状態":"合格" if not errors else "失敗","教師件数":len(teacher),"写像に利用した教師件数":len(mapped_ids),"P規則数":len(P["規則"]),"誤り":errors}

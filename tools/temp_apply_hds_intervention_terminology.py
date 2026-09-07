from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def replace_exact(path: str, old: str, new: str, expected: int = 1) -> None:
    p = ROOT / path
    text = p.read_text(encoding="utf-8")
    count = text.count(old)
    if count != expected:
        raise SystemExit(f"{path}: expected {expected} occurrences, got {count}: {old!r}")
    p.write_text(text.replace(old, new), encoding="utf-8")


# Active runtime terminology and diagnostic marker.
replace_exact(
    "src/minidora/runtime.py",
    "既定経路は厳密言語模型・能力模型・汎用計算器・外部Data/R・HDS安全弁だけで成立する。",
    "既定経路は厳密言語模型・能力模型・汎用計算器・外部Data/R・HDS監督介入層だけで成立する。",
)
replace_exact(
    "src/minidora/hds_model_projection.py",
    "HDSの実体はこの能力評価内部には置かず、外側のフィードバック安全弁だけに置く。",
    "HDSの実体はこの能力評価内部には置かず、外側のHDS監督介入層だけに置く。",
)
replace_exact(
    "src/minidora/hds監督選択runtime.py",
    "APPROVE済みの通常推論は安全弁の対象外とし、診断文字列を理由に再解釈しない。",
    "APPROVE済みの通常推論はHDS介入の対象外とし、診断文字列を理由に再解釈しない。",
)
replace_exact(
    "src/minidora/hds監督選択runtime.py",
    "通常MINIDORAを単一主体として保持するHDS安全弁セッション。",
    "通常MINIDORAを単一主体として保持するHDS監督介入セッション。",
)
replace_exact(
    "src/minidora/hds監督選択runtime.py",
    "# 安全弁が動かなかった場合、通常MINIDORA結果を1bitも再解釈しない。",
    "# HDS介入がなかった場合、通常MINIDORA結果を1bitも再解釈しない。",
)
replace_exact(
    "src/minidora/hds監督選択runtime.py",
    '"HDS_FEEDBACK_SAFETY_VALVE",',
    '"HDS_SUPERVISORY_INTERVENTION",',
)
replace_exact(
    "src/minidora/hds監督選択runtime.py",
    "HDSをMINIDORAフィードバックループの安全弁として実行する。",
    "HDSをMINIDORAフィードバックループの監督介入層として実行する。",
)

# Active benchmark terminology and protocol wording.
replace_exact(
    "tools/benchmark_formal.py",
    '"""HDS安全弁を使うリポジトリ標準GPQAベンチ入口。',
    '"""HDS監督介入を使うリポジトリ標準GPQAベンチ入口。',
)
replace_exact(
    "tools/benchmark_formal.py",
    "baselineはHDS非介入の通常MINIDORA、currentはその結果が未閉包の時だけHDS安全弁を作動させる。",
    "baselineはHDS非介入の通常MINIDORA、currentはその結果が未閉包の時だけHDS介入を実行する。",
)
replace_exact(
    "tools/benchmark_formal.py",
    '"""HDS安全弁を含まない通常MINIDORA選択をそのまま実行する。"""',
    '"""HDS介入を含まない通常MINIDORA選択をそのまま実行する。"""',
)
replace_exact(
    "tools/benchmark_formal.py",
    'protocol["runtime"] = "minimal generic MINIDORA formal core + HDS safety valve on anomaly only; specialist modules excluded"',
    'protocol["runtime"] = "minimal generic MINIDORA formal core + HDS supervisory intervention layer; specialist modules excluded"',
)
replace_exact(
    "tools/benchmark_formal.py",
    'protocol["hds_role"] = "通常MINIDORAを俯瞰監視し、未閉包・競合・観測不足等の異常時だけ既存作用を起動。正常推論は完全透過"',
    'protocol["hds_role"] = "通常MINIDORAを俯瞰監督し、未閉包・競合・観測不足等がある場合だけHDS介入として既存作用を起動。非介入時は完全透過"\n    protocol["hds_intervention_definition"] = "HDS監督は観測層、HDS介入はRUN_EXISTING_ACTIONによる外部作用起動。停止要求・非介入は監督判断であり介入件数に含めない"',
)

replace_exact(
    "tools/benchmark_formal_scientific_ab.py",
    "現行 ``tools/benchmark_formal.py`` の正式MINIDORA + HDS安全弁。",
    "現行 ``tools/benchmark_formal.py`` の正式MINIDORA + HDS監督介入層。",
)
replace_exact(
    "tools/benchmark_formal_scientific_ab.py",
    'protocol["runtime"] = "current formal MINIDORA + HDS safety valve; repo-native scientific capability controlled A/B"',
    'protocol["runtime"] = "current formal MINIDORA + HDS supervisory intervention layer; repo-native scientific capability controlled A/B"',
)
replace_exact(
    "tools/benchmark_formal_scientific_ab.py",
    '"baseline=current formal MINIDORA with HDS safety valve. "',
    '"baseline=current formal MINIDORA with HDS supervisory intervention layer. "',
)

# Tests follow the current diagnostic contract and explicitly reject the legacy umbrella label.
replace_exact(
    "tests/test_hds監督選択runtime.py",
    'self.assertIn("HDS_FEEDBACK_SAFETY_VALVE", out.選択.理由)',
    'self.assertIn("HDS_SUPERVISORY_INTERVENTION", out.選択.理由)',
)
replace_exact(
    "tests/test_runtime_hds_choice.py",
    'self.assertNotIn("HDS_FEEDBACK_SAFETY_VALVE", result.採否.理由)',
    'self.assertNotIn("HDS_SUPERVISORY_INTERVENTION", result.採否.理由)',
    expected=2,
)
replace_exact(
    "tests/test_hds監督architecture.py",
    'self.assertIn("安全弁", text)',
    'self.assertIn("監督介入", text)\n        self.assertNotIn("安全弁", text)\n        self.assertNotIn("HDS_FEEDBACK_SAFETY_VALVE", inspect.getsource(supervised))',
)

# Canonical design: supervision is the outer layer; intervention is the actual action trigger.
p = ROOT / "設計/32_MINIDORA_HDS監督介入制御_v1.md"
text = p.read_text(encoding="utf-8")
old_intro = """## 1. 目的\n\nHDSをMINIDORAのフィードバックループに対する**安全弁**として配置する。\n\n通常MINIDORAの推論系は作り直さない。通常推論が自力で閉包した場合、HDSは介入せず、その結果を完全透過する。未閉包・競合・観測不足・状態停滞などの異常が観測された場合だけ、HDSが既存作用の起動を指示する。\n"""
new_intro = """## 1. 目的\n\nHDSをMINIDORAのフィードバックループに対する**監督介入層**として配置する。\n\n用語を次のように固定する。\n\n- **HDS監督** — 通常MINIDORAの状態を外側から観測し、介入要否を判定する層。監督そのものは出力を書き換えない。\n- **HDS介入** — 監督判断により `RUN_EXISTING_ACTION` を発行し、既存作用を実際に起動すること。`REFERENCE`、`EXISTING_COMPUTE_EXECUTOR` 等はこの下位種別である。\n- **HDS非介入** — `NO_INTERVENTION`。通常MINIDORAの結果を完全透過する。\n- **HDS停止判断** — `REQUEST_STOP`。監督判断であり、既存作用を起動しないためHDS介入件数には含めない。\n\n従来の「HDS安全弁」は、HDS監督介入層全体を指す総称としては廃止する。誤閉包防止や停止判断などの安全性はHDS監督介入層が持つ性質の一部であり、追加Reference取得・既存計算実行・再評価を含むHDS介入全体と同一視しない。\n\n通常MINIDORAの推論系は作り直さない。通常推論が自力で閉包した場合、HDSは介入せず、その結果を完全透過する。未閉包・競合・観測不足・状態停滞などの異常が観測された場合だけ、HDSが既存作用の起動を指示する。\n"""
if text.count(old_intro) != 1:
    raise SystemExit("canonical design intro did not match")
text = text.replace(old_intro, new_intro)
text = text.replace("どちらも安全弁ではなく、通常系の置換になる。", "どちらもHDS監督介入ではなく、通常系の置換になる。")
text = text.replace("HDS安全弁active pathからは外す。", "HDS監督介入active pathからは外す。")
text = text.replace("状態: 現行正本  ", "状態: 現行正本（2026-09-07 HDS監督介入用語統合改訂）  ")
p.write_text(text, encoding="utf-8")

print("HDS intervention terminology update applied")

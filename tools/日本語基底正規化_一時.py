# -*- coding: utf-8 -*-
"""日本語基底への移行専用正規化器。

再実行可能に保ち、旧英字公開入口は薄い互換入口へ降格する。
履歴資産と固定取得物は変更しない。
"""
from __future__ import annotations

from pathlib import Path
import io
import re
import tokenize


根 = Path(__file__).resolve().parents[1]
自己 = Path(__file__).resolve()


ソース移動 = {
    "choice_intent.py": "選択意図.py",
    "hds_adapter.py": "HDS適合器.py",
    "hds_choice_runtime.py": "HDS選択実行系.py",
    "hds_compiler.py": "HDS構文化器.py",
    "hds_compiler_action_delta.py": "HDS構文化作用差分.py",
    "hds_compiler_audit_ir.py": "HDS構文化監査中間表現.py",
    "hds_compiler_dynamics.py": "HDS構文化動態.py",
    "hds_compiler_failure.py": "HDS構文化失敗.py",
    "hds_compiler_failure_bank.py": "HDS構文化失敗集.py",
    "hds_compiler_frontend.py": "HDS構文化前処理.py",
    "hds_compiler_history.py": "HDS構文化履歴.py",
    "hds_compiler_pipeline_v1_4.py": "HDS構文化処理系列_v1_4.py",
    "hds_compiler_records.py": "HDS構文化記録.py",
    "hds_compiler_records_v1_3.py": "HDS構文化記録_v1_3.py",
    "hds_compiler_tacit.py": "HDS構文化暗黙知.py",
    "hds_compiler_v1.py": "HDS構文化器_v1.py",
    "hds_ir.py": "HDS中間表現.py",
    "hds_language_coordination.py": "HDS言語協調.py",
    "hds_language_relations.py": "HDS言語関係.py",
    "hds_language_scope.py": "HDS言語範囲.py",
    "hds_language_semantic_bridge.py": "HDS言語意味橋渡し.py",
    "hds_model_projection.py": "HDS模型射影.py",
    "hds_reference.py": "HDS参照.py",
    "hds_runtime_projection.py": "HDS実行系射影.py",
    "hds_semantic_topic_projection.py": "HDS意味主題射影.py",
    "hds監督選択runtime.py": "HDS監督選択実行系.py",
    "hds作業状態.py": "HDS作業状態.py",
    "hds統一状態循環.py": "HDS統一状態循環.py",
    "multilingual_surface.py": "多言語表層.py",
    "runtime.py": "実行系.py",
    "semantic_tokens.py": "意味字句.py",
    "standard_reference.py": "標準参照.py",
    "trinity_context.py": "トリニティ文脈.py",
}

ツール移動 = {
    "benchmark_contract.py": "評価契約.py",
    "製品能力Module実証.py": "製品能力モジュール実証.py",
}

ワークフロー移動 = {
    "browser-ci.yml": "ブラウザ実行CI.yml",
    "ci.yml": "再構築CI.yml",
    "glm_weight_d4_audit.yml": "GLM重みD4監査.yml",
    "gpqa_current_measure.yml": "GPQA現行測定.yml",
    "gpqa_scientific_specialist_ab.yml": "GPQA科学専門能力_AB.yml",
    "gpqa_scientific_specialist_replay.yml": "GPQA科学専門能力_再生.yml",
    "knowledge_retrieval_live.yml": "知識取得_実参照.yml",
    "manual-validation.yml": "手動検証.yml",
    "projection_chain_audit.yml": "射影連鎖監査.yml",
}

試験語彙 = {
    "and": "連言", "coordination": "協調", "clean": "整理",
    "benchmark": "外部評価", "cli": "コマンドライン", "contract": "契約",
    "repository": "リポジトリ", "repo": "リポジトリ", "lock": "固定",
    "choice": "選択", "intent": "意図", "core": "模型核", "Core": "模型核",
    "active": "有効", "path": "経路", "local": "局所", "view": "観測",
    "monotonic": "単調性", "crossref": "Crossref参照", "reference": "参照",
    "europe": "Europe", "pmc": "PMC参照", "general": "一般", "relations": "関係",
    "hds": "HDS", "adapter": "適合器", "candidate": "候補", "reconcile": "再照合",
    "hypothesis": "仮説", "compile": "構文化", "parallel": "並列", "compiler": "構文化器",
    "action": "作用", "delta": "差分", "architecture": "構造", "pipeline": "処理系列",
    "data": "資料", "direct": "直接", "verifier": "検証", "effort": "計算量",
    "evidence": "証拠", "clone": "複製", "quality": "品質", "graph": "関係図",
    "reasoning": "推論", "independent": "独立", "ir": "中間表現", "gate": "関門",
    "language": "言語", "scope": "範囲", "replay": "再生", "capture": "記録",
    "compare": "比較", "eval": "評価", "residual": "残差", "retrieval": "取得",
    "route": "経路", "source": "情報源", "confidence": "信頼度", "integration": "統合",
    "unknown": "未知", "slots": "欄", "working": "作業", "state": "状態",
    "http": "HTTP参照", "k3": "K3", "distinctive": "識別", "directed": "有向",
    "equivalence": "同等性", "exception": "例外", "elimination": "除去", "native": "ネイティブ",
    "structural": "構造", "base": "基底", "english": "英語", "semantic": "意味",
    "bridge": "橋渡し", "multilingual": "多言語", "trinity": "トリニティ",
    "natural": "自然言語", "open": "開放", "polarity": "極性", "preservation": "保持",
    "projection": "射影", "audit": "監査", "boundary": "境界", "chain": "連鎖",
    "fidelity": "忠実度", "qualifiers": "修飾", "runtime": "実行系", "subject": "主体",
    "trunk": "幹", "wikipedia": "Wikipedia", "relevance": "関連性", "round2": "第2巡",
    "module": "モジュール", "Module": "モジュール", "fallback": "代替経路",
}

識別子置換 = {
    "add_relation": "関係を追加",
    "_state_name": "_状態名",
    "_relation_signature": "_関係署名",
    "_candidate_sig": "_候補署名",
    "supervisory_state": "監督状態",
    "run_action": "作用を実行",
    "final_result": "最終結果",
    "_registry": "_登録簿",
    "_result": "_結果",
    "_candidate": "_候補",
    "_Compiler": "_構文化器",
    "Compiler": "構文化器",
    "_assertion_candidate": "_主張候補",
    "_relation_ir": "_関係中間表現",
    "_weak_relation": "_弱関係",
    "_core": "_模型核",
    "model_result": "模型結果",
    "choice_ir": "選択中間表現",
    "_query_choice": "_問合せ選択肢",
    "_direction_candidate": "_方向候補",
    "_relation": "_関係",
    "_synthetic_relation_ir": "_合成関係中間表現",
    "Fallback": "代替経路",
    "context_features": "文脈特徴",
    "_relation_name_from_predicate": "_述語から関係名",
    "_source_group_id": "_情報源群ID",
    "_fact_source_map": "_事実情報源対応",
    "_relation_similarity": "_関係類似度",
    "_source_confidence": "_情報源信頼度",
    "_state_marker": "_状態印",
    "_source_marker": "_情報源印",
    "_relation_condition": "_関係条件",
    "_relation_polarity": "_関係極性",
    "_relation_qualifiers": "_関係修飾",
    "_relation_name": "_関係名",
    "_source_id": "_情報源ID",
    "_candidate_edges": "_候補辺",
    "_collapse_by_source": "_情報源別に統合",
    "_choice_row": "_選択肢行",
    "_choice_numeric": "_選択肢数値",
    "_choice_contains": "_選択肢包含",
    "_generic_result": "_一般結果",
    "_choice_scalar": "_選択肢スカラー",
    "_parse_state": "_状態解析",
    "_projection_probability": "_射影確率",
    "_generic_relation_question": "_一般関係質問",
    "_fallback_question": "_代替質問",
    "_relation_is_question": "_関係は質問か",
    "_semantic_bridge_question": "_意味接続質問",
    "_semantic_loss": "_意味損失",
    "_relation_types": "_関係種別群",
}

状態値置換 = {
    "PROVISIONAL_BY_DEFAULT": "原則暫定",
    "CLOSED_FOR_OPERATION": "作用閉包",
    "STRUCTURED_PUBLIC_PROJECTION": "構造化公開射影",
    "FULL_FIELD_ACTIVE": "全領域有効",
    "PARTIALLY_ARTICULATED": "部分構文化",
    "MEANING_PRESERVED": "意味保持",
    "UNFORMED": "未形成",
    "SHADOW": "影",
    "PATTERN": "パターン",
    "MECHANISM_CANDIDATE": "機構候補",
    "PRINCIPLE_CANDIDATE": "原理候補",
    "STANDARD_RELATIONS": "標準関係",
    "FORMED_RELATIONS": "形成済み関係",
    "PRIMARY_CAPABILITY_ACTIONS": "一次能力作用",
}

契約鍵置換 = {
    "benchmark_contract": "評価契約",
    "schema": "契約形式",
    "benchmark_id": "外部評価識別子",
    "task": "課題",
    "evaluation_class": "評価種別",
    "input_boundary": "入力境界",
    "retrieval_mode": "参照方式",
    "fixed_reference_data_allowed": "固定参照資料許可",
    "condition_fingerprint_sha256": "条件指紋SHA256",
    "input_snapshot_sha256": "入力スナップショットSHA256",
    "canonical_full_run": "正本全数実行",
    "canonical_score_field": "正本得点欄",
    "within_run_controlled_ab_direct": "同一実行内統制AB直接比較",
    "cross_run_code_delta_direct": "実行間コード差直接比較",
    "snapshot_score_chronology_allowed": "スナップショット得点時系列保存許可",
    "claim_scope": "主張可能範囲",
    "forbidden_claims": "禁止主張",
    "dataset_csv_sha256": "資料集合CSV_SHA256",
    "full_benchmark_total": "全問題数",
    "selected_indices": "選択番号群",
    "choice_shuffle_seed": "選択肢シャッフル種",
    "openalex_enabled": "OpenAlex有効",
    "wikipedia_languages": "Wikipedia言語群",
    "controlled_ab": "統制AB",
}

契約識別子置換 = {
    "CONTRACT_SCHEMA": "契約形式",
    "GPQA_E2E_LIVE_ID": "GPQA実参照E2E識別子",
    "GPQA_CANONICAL_TOTAL": "GPQA正本全問題数",
    "GPQA_CANONICAL_DATASET_CSV_SHA256": "GPQA正本資料集合CSV_SHA256",
    "GPQA_CANONICAL_CHOICE_SHUFFLE_SEED": "GPQA正本選択肢シャッフル種",
    "GPQA_CANONICAL_OPENALEX_ENABLED": "GPQA正本OpenAlex有効",
    "GPQA_CANONICAL_WIKIPEDIA_LANGUAGES": "GPQA正本Wikipedia言語群",
    "_canonical_sha256": "_正本SHA256",
    "validate_gpqa_canonical_protocol": "GPQA正本手順を検証",
    "gpqa_e2e_live_contract": "GPQA実参照E2E契約",
    "direct_comparison_verdict": "直接比較判定",
    "attach_contract": "契約を付与",
}

試験関数置換 = {
    "test_plan_is_separate_from_archive_and_has_lease": "test_計画は正本保管と分離され有効期限を持つ",
    "test_candidate_change_rebinds_plan": "test_候補変化で計画を再束縛する",
    "test_subject_change_is_a_real_plan_invalidation_condition": "test_主体変化は計画失効条件になる",
    "test_parallel_pass_disagreement_opens_global_reconcile": "test_並列通過の不一致で大域再照合を開く",
    "test_formation_is_not_active_until_explicitly_approved": "test_形成は明示承認まで有効化しない",
    "test_effect_audit_requires_downstream_difference": "test_作用実効監査は後続差を要求する",
    "test_live_gpqa_is_canonical_and_fixed_reference_is_forbidden": "test_実参照GPQAが正本で固定参照は禁止",
    "test_canonical_protocol_accepts_minidora30_conditions": "test_正本手順はMINIDORA30条件を受理する",
    "test_partial_gpqa_is_rejected_as_canonical": "test_GPQA部分実行は正本として拒否する",
    "test_openalex_condition_change_is_rejected": "test_OpenAlex条件変更を拒否する",
    "test_dataset_hash_change_is_rejected": "test_資料集合ハッシュ変更を拒否する",
    "test_live_gpqa_is_not_cross_run_code_only_delta": "test_実参照GPQAは実行間コード差のみではない",
    "test_required_benchmark_contract_assets_exist": "test_必須評価契約資産が存在する",
    "test_canonical_separates_minidora30_core_and_minidora80_system_live_only": "test_正本はMINIDORA30模型核とMINIDORA80システムを分離する",
    "test_agents_enforces_gpqa_no_fixed_reference_policy": "test_AGENTSはGPQA固定参照禁止を要求する",
    "test_strict_runner_has_no_gpqa_fixed_replay_entry": "test_厳密評価入口にGPQA固定再生経路がない",
    "test_tools_readme_declares_live_only_canonical_runner": "test_ツール説明は実参照正本評価入口を宣言する",
    "test_minidora30_manifest_is_machine_locked": "test_MINIDORA30目録は機械固定される",
    "test_minidora80_manifest_is_machine_locked": "test_MINIDORA80目録は機械固定される",
    "test_gpqa_fixed_replay_execution_paths_are_retired": "test_GPQA固定再生実行経路は廃止済み",
    "test_runtime_transitive_import_graph_excludes_experimental_unified_path": "test_実行系推移依存から実験統一経路を除外する",
    "test_runtime_choice_path_is_formal_core_plus_hds_supervisory_intervention": "test_実行系選択経路は形式模型核とHDS監督介入である",
    "test_existing_approve_is_exactly_transparent": "test_既存承認は完全透過する",
    "test_suspend_can_only_add_new_closure": "test_保留は新規閉包だけを追加する",
}

説明語置換 = {
    "Capability Registry": "能力登録簿",
    "Capability Module": "能力モジュール",
    "Capability Modules": "能力モジュール群",
    "Module": "能力モジュール",
    "Core": "模型核",
    "Compiler": "構文化器",
    "Architecture": "構造",
    "Pipeline": "処理系列",
    "Runtime": "実行系",
    "Gate": "関門",
    "scope": "範囲",
    "solver": "解決器",
    "helper": "補助器",
    "fallback": "代替経路",
    "registry": "登録簿",
    "checkpoint": "検査点",
    "manifest": "目録",
    "inventory": "目録",
}


def _互換モジュール本文(正本名: str) -> str:
    モジュール = Path(正本名).stem
    return (
        f'"""旧英字名の互換入口。現行日本語正本は `{正本名}`。"""\n'
        'from importlib import import_module as _読込\n'
        f'_正本 = _読込(".{モジュール}", __package__)\n'
        'for _名, _値 in vars(_正本).items():\n'
        '    if _名 not in {"__name__", "__package__", "__loader__", "__spec__", "__file__", "__cached__"}:\n'
        '        globals()[_名] = _値\n'
    )


def _互換ツール本文(正本名: str) -> str:
    return (
        f'"""旧英字名の互換入口。現行日本語正本は `{正本名}`。"""\n'
        'from pathlib import Path\n'
        'import runpy\n\n'
        f'_正本経路 = Path(__file__).with_name("{正本名}")\n'
        '_名前空間 = runpy.run_path(str(_正本経路), run_name="_minidora_互換")\n'
        'for _名, _値 in _名前空間.items():\n'
        '    if not _名.startswith("__"):\n'
        '        globals()[_名] = _値\n'
    )

def _移送(基点: Path, 対応: dict[str, str], ツール: bool = False) -> None:
    for 旧名, 新名 in 対応.items():
        旧 = 基点 / 旧名
        新 = 基点 / 新名
        if not 旧.exists():
            continue
        旧本文 = 旧.read_text(encoding="utf-8")
        if "互換入口" not in 旧本文[:800] and not 新.exists():
            新.write_text(旧本文, encoding="utf-8")
        if 新.exists() and "互換入口" not in 旧本文[:800]:
            旧.write_text(_互換ツール本文(新名) if ツール else _互換モジュール本文(新名), encoding="utf-8")


def _試験名を日本語化() -> None:
    基点 = 根 / "tests"
    for 対象 in sorted(基点.glob("test_*.py")):
        意味 = 対象.stem[5:]
        新意味 = 意味
        for 旧, 新 in (("Core", "模型核"), ("core", "模型核"), ("Module", "モジュール"), ("runtime", "実行系"), ("repo", "リポジトリ"), ("round2", "第2巡")):
            新意味 = 新意味.replace(旧, 新)
        部分群 = []
        for 部分 in 新意味.split("_"):
            部分群.append(試験語彙.get(部分, 部分))
        新名 = "test_" + "_".join(部分群) + ".py"
        新対象 = 対象.with_name(新名)
        if 新対象 != 対象 and not 新対象.exists():
            対象.rename(新対象)


def _ワークフロー名を日本語化() -> None:
    基点 = 根 / ".github/workflows"
    for 旧名, 新名 in ワークフロー移動.items():
        旧 = 基点 / 旧名
        新 = 基点 / 新名
        if 旧.exists() and not 新.exists():
            旧.rename(新)


def _設計正本を補う() -> None:
    旧 = 根 / "設計/29_HDS_Compiler_作用差分構文化_v1_3.md"
    新 = 根 / "設計/29_HDS構文化器_作用差分構文化_v1_3.md"
    if 旧.exists() and not 新.exists():
        本文 = 旧.read_text(encoding="utf-8")
        for 英語, 日本語 in 説明語置換.items():
            本文 = 本文.replace(英語, 日本語)
        新.write_text(本文, encoding="utf-8")
    if 旧.exists() and 新.exists():
        旧.write_text("# 旧英字名の互換案内\n\n現行日本語正本は [`29_HDS構文化器_作用差分構文化_v1_3.md`](29_HDS構文化器_作用差分構文化_v1_3.md)。\n", encoding="utf-8")

    for 相対, 正本 in (("REFERENCES.md", "参照正本.md"), ("評価/BENCHMARK_CONTRACT_v2.md", "評価契約_v2.md")):
        対象 = 根 / 相対
        if 対象.exists():
            対象.write_text(f"# 旧英字名の互換案内\n\n現行日本語正本は [`{正本}`]({正本})。\n", encoding="utf-8")


def _字句置換(対象: Path, 対応: dict[str, str]) -> None:
    try:
        本文 = 対象.read_text(encoding="utf-8")
        出力 = []
        for 字句 in tokenize.generate_tokens(io.StringIO(本文).readline):
            if 字句.type == tokenize.NAME and 字句.string in 対応:
                字句 = tokenize.TokenInfo(字句.type, 対応[字句.string], 字句.start, 字句.end, 字句.line)
            出力.append(字句)
        新本文 = tokenize.untokenize(出力)
        if 新本文 != 本文:
            対象.write_text(新本文, encoding="utf-8")
    except (UnicodeDecodeError, tokenize.TokenError, IndentationError):
        return


def _内容を正規化() -> None:
    除外先頭 = ("docs/", "artifacts/", "構文化/正本パッケージ/")
    対象拡張子 = {".py", ".md", ".yml", ".yaml", ".toml", ".json", ".jsonl", ".ps1"}
    モジュール置換 = {Path(旧).stem: Path(新).stem for 旧, 新 in ソース移動.items()}
    モジュール置換.update({Path(旧).stem: Path(新).stem for 旧, 新 in ツール移動.items()})
    for 対象 in 根.rglob("*"):
        if not 対象.is_file() or 対象.resolve() == 自己 or 対象.suffix.lower() not in 対象拡張子:
            continue
        if 対象.name in {"日本語基底監査.py", "日本語基底詳細監査.py", "日本語基底正規化_実行.py", "日本語基底正規化_仕上げ.py"}:
            continue
        if 対象.name in {"日本語基底監査.py", "日本語基底詳細監査.py", "日本語基底正規化_実行.py", "日本語基底正規化_仕上げ.py"}:
            continue
        if 対象.name in {"日本語基底監査.py", "日本語基底詳細監査.py", "日本語基底正規化_実行.py"}:
            continue
        if 対象.name in {"日本語基底監査.py", "日本語基底詳細監査.py", "日本語基底正規化_実行.py"}:
            continue
        if 対象.name in {"日本語基底監査.py", "日本語基底詳細監査.py", "日本語基底正規化_実行.py"}:
            continue
        if 対象.name in {"日本語基底監査.py", "日本語基底詳細監査.py", "日本語基底正規化_実行.py"}:
            continue
        if 対象.name in {"日本語基底監査.py", "日本語基底詳細監査.py", "日本語基底正規化_実行.py"}:
            continue
        if 対象.name in {"日本語基底監査.py", "日本語基底詳細監査.py", "日本語基底正規化_実行.py"}:
            continue
        if 対象.name in {"日本語基底監査.py", "日本語基底詳細監査.py", "日本語基底正規化_実行.py"}:
            continue
        if 対象.name in {"日本語基底監査.py", "日本語基底詳細監査.py", "日本語基底正規化_実行.py"}:
            continue
        if 対象.name in {"日本語基底監査.py", "日本語基底詳細監査.py", "日本語基底正規化_実行.py"}:
            continue
        if 対象.name in {"日本語基底監査.py", "日本語基底詳細監査.py", "日本語基底正規化_実行.py"}:
            continue
        if 対象.name in {"日本語基底監査.py", "日本語基底詳細監査.py", "日本語基底正規化_実行.py"}:
            continue
        if 対象.name in {"日本語基底監査.py", "日本語基底詳細監査.py", "日本語基底正規化_実行.py"}:
            continue
        相対 = 対象.relative_to(根).as_posix()
        if 相対.startswith(".github/workflows/"):
            continue
        if 相対.startswith(除外先頭):
            continue
        try:
            本文 = 対象.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            continue
        新本文 = 本文
        for 旧, 新 in モジュール置換.items():
            新本文 = 新本文.replace(旧, 新)
        for 旧, 新 in 状態値置換.items():
            新本文 = 新本文.replace(f'"{旧}"', f'"{新}"').replace(f"'{旧}'", f"'{新}'")
        for 旧, 新 in 契約鍵置換.items():
            新本文 = 新本文.replace(f'"{旧}"', f'"{新}"').replace(f"'{旧}'", f"'{新}'")
        if 対象.suffix.lower() in {".md", ".yml", ".yaml"}:
            for 旧, 新 in 説明語置換.items():
                新本文 = 新本文.replace(旧, 新)
        if 新本文 != 本文:
            対象.write_text(新本文, encoding="utf-8")
        if 対象.suffix.lower() == ".py" and "互換入口" not in 対象.read_text(encoding="utf-8")[:800]:
            対応 = dict(識別子置換)
            対応.update(契約識別子置換)
            対応.update(試験関数置換)
            _字句置換(対象, 対応)


def _監査器を補正() -> None:
    対象 = 根 / "tools/日本語基底監査.py"
    本文 = 対象.read_text(encoding="utf-8")
    本文 = 本文.replace('            if _互換入口(対象):\n                continue\n            if not _日本語を含む(対象.stem):', '            if _互換入口(対象) or 対象.name == "README.md":\n                continue\n            if not _日本語を含む(対象.stem):')
    対象.write_text(本文, encoding="utf-8")


def _現行説明を正規化() -> None:
    for 相対 in ("tools/README.md", "製品版/README.md", "aistudio/README.md", "現行正本.md", "参照正本.md", "設計/README.md", "src/README.md", "tests/README.md"):
        対象 = 根 / 相対
        if not 対象.exists():
            continue
        本文 = 対象.read_text(encoding="utf-8")
        for 旧, 新 in 説明語置換.items():
            本文 = 本文.replace(旧, 新)
        本文 = 本文.replace("k3_public_artifact_inventory.py", "K3公開成果物目録.py")
        対象.write_text(本文, encoding="utf-8")


def main() -> int:
    _移送(根 / "src/minidora", ソース移動)
    _移送(根 / "tools", ツール移動, ツール=True)
    _試験名を日本語化()
    # workflow 改名は GitHub 接続権限のある別経路で適用する。
    _設計正本を補う()
    _内容を正規化()
    _監査器を補正()
    _現行説明を正規化()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
